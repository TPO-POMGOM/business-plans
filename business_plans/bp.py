""" Model a business plan.

Business plans are modeled using ``pandas.DataFrame`` objects:

- The index is used to represent the periods spanned by the business plan.
  It can be any **strictly increasing series** of values (``int``, ``date``,
  ``datetime``, etc.).

- Columns of the DataFrame represent the 'lines' of the business plan (such as
  revenue, costs, margin, etc.). They are created by using method
  :func:`~BPAccessor.line`.

- Values have dtype ``float64``.

The ``bp`` accessor, defined by Class :class:`BPAccessor`, provides methods and
properties applicable to such DataFrame's.


**Example**

.. code-block:: python

    >>> df = pd.DataFrame(dtype='float64',
                          index=pd.date_range(start=date(2020, 1, 1),
                                              periods=10,
                                              freq='YS')
    >>> df.bp.line(name="Revenue", history=[100, 110, 120])
    2020-01-01    100.0
    2021-01-01    110.0
    2022-01-01    120.0
    2023-01-01      0.0
    2024-01-01      0.0
    2025-01-01      0.0
    2026-01-01      0.0
    2027-01-01      0.0
    2028-01-01      0.0
    2029-01-01      0.0
    Freq: AS-JAN, dtype: float64
    >>> print(df.at[date(2020, 1, 1), "Revenue"])
    100.0


**Note on indexes**

While business plan indexes can be any strictly increasing series of values,
they will in pratice be time-related values, such as ``int`` objects
representing years, ``date`` objects representing years, quarters, or months,
etc. Classes :class:`~business_plans.report.BPChart`,
:class:`~business_plans.report.LineBPChart`,
:class:`~business_plans.report.StackedBarBPChart`,
:class:`~business_plans.report.CompareBPsLineChart`, and
:class:`~business_plans.report.BPStatus` need a way of presenting those values
in report elements. This is done by method :func:`~BPAccessor.index_to_str`,
which requires the following:

1. A way of converting an index value to a ``datetime`` object -- This is
   provided by method :func:`~BPAccessor.index_to_datetime`. The default
   implementation provided does no conversion, i.e. works only when index
   values are ``datetime`` instances. This method must be overriden when this
   is not the case. For instance, if index values are integers representing
   years::

      df = pd.DataFrame(dtype='float64', index=range(2020, 2031))
      df.bp.index_to_datetime = lambda index: datetime(year=index, month=1, day=1)

2. A default format, which is used when :func:`~BPAccessor.index_to_str` is
   called with arg `fmt` set to ``None`` -- This is provided by
   :data:`~BPAccessor.index_format`. Here is how to set it up when index values
   are integers representing years::

      df.bp.index_format = '%Y'


**Revision history**

- 9-Avr-2019 TPO -- Created this module.

- 27-Sep-2020 TPO -- Created v0.2: replace class ``BP`` with
  ``pandas.DataFrame`` and class ``BPTimeSeries`` with ``pandas.Series``.

- 18-Oct-2020 TPO -- Initial release of v0.2.

- 4-Nov-2020 TPO - Created v0.3: generalize business plan index to any strictly
  increasing sequence.

- 13-Nov-2020 TPO -- Initial release of v0.3.

- 15-Nov-2020 TPO -- Initial release of v0.3.1: Refactor :class:`Simulator` API. """

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import os
from pathlib import Path
from typing import Any, Callable, Dict, Hashable, List, Optional, Union

import numpy as np
import pandas as pd

if os.environ.get('READTHEDOCS', 'False') != 'True':
    import win32con
    from win32ui import MessageBox


__all__ = [
    'actualise',
    'actualise_and_cumulate',
    'HistoryBasedAssumption',
    'max',
    'min',
    'percent_of',
    'ExternalAssumption',
    'UpdateLink',
]


@dataclass
class UpdateLink:
    """ Represent a link displayed in the instructions for updating an assumption.


    Arguments
    ---------

    title: `str`
        Title for the web site link, which is displayed in the report as part
        of the update instructions for the assumption. See argument
        `update_instructions` to class :class:`ExternalAssumption`.

    url: `str`
        URL to which the link points."""

    title: str
    url: str


@dataclass
class ExternalAssumption:
    """ Represent an external assumption on which the business plan is based.


    Attributes
    ----------

    update_required: `bool`
        If true, the assumption is to be reported as being out of date.

        This attribute is set at the time the assumption is created.


    Arguments
    ---------

    name: `str`
        of the assumption.

    last_update: `datetime.date`
        Date of the most recent update the assumption has received.

    update_every_x_year: `float`
        Maximum duration between updates, in years. If the time elapsed since
        the last update is less than this value, the assumption is considered
        to be up to date and will not be reported by
        :class:`~business_plans.report.BPStatus` report elements. Otherwise,
        :class:`~business_plans.report.BPStatus` elements will report this
        assumption as being out of date and will display instructions on how to
        update it.

    update_instructions: `str`
        Instructions displayed by the :class:`~business_plans.report.BPStatus`
        report element when the assumption needs to be updated. The string may
        refer to the keys in argument `update_links` to display web sites
        hyperlinks in the instructions. For example::

         ExternalAssumption(
             name="Some assumption",
             last_update=date(2020, 10, 12),
             update_every_x_year=2,
             update_instructions="See {source} for more information.",
             update_links={'source': UpdateLink("reference site", "http://ref.com")})

    update_links: `Dict[str,` :class:`UpdateLink` `]`
        Web site links to be displayed in the update instructions. See
        `update_instructions` above. """

    name: str
    last_update: date
    update_every_x_year: float
    update_instructions: str
    update_links: Dict[str, UpdateLink]
    update_required: bool = field(init=False)

    def __post_init__(self):
        self.update_required = ((date.today() - self.last_update).days
                                > self.update_every_x_year * 365)


@dataclass
class HistoryBasedAssumption:
    """ Represent a business plan assumption based on history data.


    Attributes
    ----------

    update_required: `bool`
        If true, the assumption is to be reported as being out of date.

        This attribute is set at the time the assumption is created.


    Arguments
    ---------

    name: `str`
        of the assumption.

    value: `float`
        Current value of the assumption.

    history: `List[float]`
        Historical data which is displayed when the assumption needs to be
        updated, as an aid to decision.

    start: `Any`
        The index corresponding to the first element in `history`.

    last_update: `datetime.date`
        Date of the most recent update the assumption has received.

    update_every_x_year: `float`
        Maximum duration between updates, in years. If the time elapsed since
        the last update is less than this value, the assumption is considered
        to be up to date and will not be reported by
        :class:`~business_plans.report.BPStatus` report elements. Otherwise,
        :class:`~business_plans.report.BPStatus` elements will report this
        assumption as being out of date and will display -- as an aid to
        decision -- a graph showing historical data, the mean for historical
        data values, and the current value of the assumption. """

    name: str
    value: float
    history: List[float]
    start: Any
    last_update: date
    update_every_x_year: float
    update_required: bool = field(init=False)

    def __post_init__(self):
        self.update_required = (
            len(self.history) > 3
            and ((date.today() - self.last_update).days
                 > self.update_every_x_year * 365))


#: Type for the `assumptions` attribute of :class:`BPAccessor` =
#: ``Union[ExternalAssumption, HistoryBasedAssumption]``
Assumption = Union[ExternalAssumption, HistoryBasedAssumption]


#: Type for the `simulation` argument of :func:`~BPAccessor.line` =
#: ``Callable[[pd.DataFrame, pd.Series, List[Any], Any, Any, int, int],
#: List[float]]``
Simulator = Callable[[pd.DataFrame, pd.Series, List[Any], Any, Any, int, int],
                     List[float]]


#: Type for the `fmt` argument of :func:`~BPAccessor.datetime_to_str` and
#: :func:`~BPAccessor.index_to_str`  =
#: ``Optional[Union[str, Callable[[datetime], str]]]``
Formatter = Optional[Union[str, Callable[[datetime], str]]]


@pd.api.extensions.register_dataframe_accessor("bp")
class BPAccessor:
    """ Pandas DataFrame accessor for business plan methods and properties.


    Attributes
    ----------

    name: `str`, initial value is ``""``
        Name of the business plan. It is displayed on report elements generated
        by class :class:`~business_plans.report.CompareBPsLineChart`.

    assumptions: `List[` :data:`Assumption` `]`, initial value is ``[]``
        Assumptions on which the business plan is based. Assumptions are
        declared by appending objects of class :class:`ExternalAssumption` or
        class :class:`HistoryBasedAssumption` to attribute `assumptions`. For
        instance, if ``df`` is a DataFrame representing a business plan::

          df.bp.assumptions.append(ExternalAssumption(
              name="Some assumption",
              last_update=date(2020, 10, 12),
              update_every_x_year=2,
              update_instructions="See {source} for more information."
              update_links={'source': UpdateLink("reference", "http://ref.com")})

    index_format: `str`, initial value is ``'%d/%m/%Y'``
        Default format string used by methods :func:`~BPAccessor.datetime_to_str`
        and :func:`~BPAccessor.index_to_str`, when they are called with argument
        `fmt` set to ``None``. """

    def __init__(self, df: pd.DataFrame):
        if not(df.index.is_monotonic_increasing and df.index.is_unique):
            raise ValueError("'bp' accessor can only be used on DataFrames's "
                             "with strictly increasing index values.")
        self._df = df
        self._history_size: Dict[str, int] = {}
        self._max_history_lag: Dict[str, timedelta] = {}
        self.name = ""
        self.index_format = '%d/%m/%Y'
        self.assumptions: List[Assumption] = []

    def index_to_datetime(self, index: Any) -> datetime:
        """ Return the ``datetime`` equivalent of a given index value.


        Arguments
        ---------

        index: `Any`
            The index value to be converted to a ``datetime``.


        Returns
        -------

        datetime
            Returns `index` if it is a ``datetime`` object, and raises a
            ``ValueError`` exception otherwise. This method is meant to be
            overriden when index values are not ``datetime`` objects, to
            provide a means of converting them to ``datetime``.

            For instance, if index values are integers representing years::

                df = pd.DataFrame(dtype='float64', index=range(2020, 2031))
                df.bp.index_to_datetime = lambda index: datetime(index, 1, 1)
                df.bp.index_format = '%Y'
        """
        if isinstance(index, datetime):
            return index
        else:
            raise ValueError("Index value is not a datetime instance, method "
                             "index_to_datetime() must be overriden.")

    def datetime_to_str(self, index: datetime, fmt: Formatter = None) -> str:
        """ Format a datetime index value into a string.

        Arguments
        ---------

        index: `datetime`
            The datetime index value to be formatted into a string.

        fmt: :data:`Formatter`, defaults to ``None``
            Can have the following types:

            - ``None``: the method returns ``index.strftime(self.index_format)``

            - ``str``: the method returns ``index.strftime(fmt)``

            - ``Callable[[datetime], str]``: the method returns ``fmt(index)``

        Returns
        -------

        str
            See argument `fmt` above. """
        if fmt is None:
            return index.strftime(self.index_format)
        elif isinstance(fmt, str):
            return index.strftime(fmt)
        elif callable(fmt):
            return fmt(index)
        else:
            raise TypeError("Expected type Formatter for argument fmt, got", fmt)

    def index_to_str(self, index: Any, fmt: Formatter = None) -> str:
        """ Format an index value into a string.

        Shorthand for::

            self.datetime_to_str(self.index_to_datetime(index), fmt)

        """
        return self.datetime_to_str(self.index_to_datetime(index), fmt)

    def line(self,
             name: str = "",
             *,
             default_value: float = 0,
             history: Optional[Union[pd.Series, List[float]]] = None,
             simulation: Optional[Simulator] = None,
             simulate_from: Optional[Any] = None,
             simulate_until: Optional[Any] = None,
             max_history_lag: timedelta = timedelta(days=365)) -> pd.Series:
        """ Return a new business plan line.

        If ``df`` is a ``pandas.DataFrame``, ``df.bp.line()`` returns a new
        business plan line, represented as a ``pandas.Series`` object, with the
        same index as ``df`` and with dtype ``float64``.


        Arguments
        ---------

        name: `str`, defaults to ``""``
            Name of the business plan line. It can be either:

            - A non-empty string -- The new business plan line is added to the
              business plan DataFrame, as column `name`. Note that new
              business plan lines with history data (as opposed to business plan
              lines which are computed from other lines) should only be added
              to the business plan in this way, to ensure that data required by
              methods :func:`history_size` and :func:`max_history_lag` is
              properly intialized.

            - An empty string -- The new business plan line is not added to the
              business plan DataFrame.

        default_value: `float`, defaults to ``0``
            Value used to initialize elements in the business plan line which
            are not otherwise initialized by `history` or `simulation`.

        history: `Optional[Union[pandas.Series, List[float]]]`, defaults to ``None``
            When a ``pandas.Series`` or ``List[float]`` of n elements is
            specified, the first n elements of the business plan line are
            initialised with those elements. Method :func:`history_size`
            can later be used to retrieve n.

        simulation: `Optional[` :class:`Simulator` `]`, defaults to ``None``
            When `simulation` is specified, it is used to calculate the values
            of elements `start_index` to `end_index` (inclusive) of
            the business plan line, where:

            .. _start_index:

            - `start_index` is equal to:

                - If argument `simulate_from` is specified: ``simulate_from``

                - Otherwise, if argument `history` is specified:
                  ``df.index[len(history)]``

                - Otherwise: ``df.index[0]``

            .. _end_index:

            - `end_index` is equal to:

                - If argument `simulate_until` is specified: ``simulate_until``

                - Otherwise: ``df.index[-1]``

            - `simulation` is a function with the following signature::

                simulation(df: pandas.DataFrame,
                           s: pandas.Series,
                           index_values: List[Any],
                           start_index: Any,
                           end_index: Any,
                           start_loc: int,
                           end_loc: int) -> List[float]

              The function is called with the following values:

              - `df`: the ``pandas.DataFrame`` on which method :func:`line` is
                operating.

              - `s`: the ``pandas.Series`` created by method :func:`line`, on
                which the simulation is to be performed.

              .. _index_values:

              - `index_values`: all index values from `start_index` to
                `end_index` (inclusive).

              - `start_index`, `end_index`: see above. The following
                expressions always evaluate to true::

                  index_values[0] == start_index
                  index_values[-1] == end_index

              .. _start_loc:
              .. _end_loc:

              - `start_loc`, `end_loc`: integer position of `start_index` and
                `end_index` in the series's index. The following expressions
                always evaluate to true::

                  s.index[start_loc] == start_index
                  s.index[end_loc] == end_index
                  len(index_values) == end_loc - start_loc + 1

              The function should return a list of ``end_loc - start_loc + 1``
              elements, which are then assigned to elements `start_index`
              to `end_index` of the business plan line.

        simulate_from: `Optional[Any]`, defaults to ``None``
            See argument `simulation` above.

        simulate_until: `Optional[Any]`, defaults to ``None``
            See argument `simulation` above.

        max_history_lag: `timedelta`, defaults to ``timedelta(days=365)``
            Specifies the maximum lag between history data for this business
            plan line and the current date before class
            :class:`~business_plans.report.BPStatus` issues a warning that
            history is missing. Method :func:`max_history_lag` can later be
            used to retrieve this value.


        Returns
        -------

        pandas.Series
            representing the new business plan line. """

        index = self._df.index
        line = pd.Series(data=default_value, dtype='float64', index=index)
        if history is None or len(history) == 0:
            history_size = 0
        else:
            if len(history) > index.size:
                raise ValueError(f"Argument 'history' provides {len(history)} "
                                 f"values, max {index.size} expected")
            line.iloc[:len(history)] = history
            history_size = len(history)
        if simulation is not None:
            start_index = simulate_from or index[history_size]
            if start_index not in index:
                raise KeyError(start_index)
            end_index = simulate_until or index[-1]
            if end_index not in index:
                raise KeyError(end_index)
            if not (start_index <= end_index):
                raise ValueError(f"Start of simulation ({start_index}) "
                                 f"should be <= end of simulation ({end_index})")
            start_loc = index.get_loc(start_index)
            end_loc = index.get_loc(end_index)
            index_values = index[start_loc: end_loc + 1]
            result = simulation(self._df, line,
                                index_values, start_index, end_index,
                                start_loc, end_loc)
            if len(result) != len(index_values):
                raise ValueError(f"Simulator returned a list with {len(result)} "
                                 f"elements, expected {len(index_values)}")
            line.loc[start_index: end_index] = result
        if name:
            self._df[name] = line
            self._history_size[name] = history_size
            self._max_history_lag[name] = max_history_lag
        return line

    def history_size(self, name: str) -> int:
        """ Number of years of history available for a given business plan line.


        Arguments
        ---------

        name: `str`
            Name of the business plan line, as defined by argument `name` to
            method :func:`line`.


        Returns
        -------

        int
            If the `history` argument was supplied to method :func:`line` at
            the time the business plan line was created, ``len(history)`` is
            returned. Otherwise, ``0`` is returned. """
        return self._history_size.get(name, 0)

    def max_history_lag(self, name: str) -> timedelta:
        """ Maximum missing years of history for a given business plan line.


        Arguments
        ---------

        name: `str`
            Name of the business plan line, as defined by argument `name` to
            method :func:`line`.


        Returns
        -------

        int
            Maximum number of years history data for this business plan line
            may lag behind the current year before class
            :class:`~business_plans.report.BPStatus` issues a warning that
            history is missing. This is the value supplied to argument
            `max_history_lag` of method :func:`line` at the time the business
            plan line was created. """
        return self._max_history_lag.get(name, timedelta(days=365))

    def compare_to_reference(self, ref_file_path: str) -> None:
        """ Compare the business plan to a reference file.

        Compare the business plan with the contents of a reference file. The
        results of the comparison are shown in a dialog box.

        When the business plan and the reference file are not identical, a
        detailed report is displayed in the dialog box, indicating:

        - Lines which have different values in the business plan and in the
          reference.

        - Lines from the business plan which are not in the reference.

        - Lines from the reference which are not in the business plan.

        The user is then given the option to overwrite the reference file with
        the contents of the business plan (this is the way a reference file is
        created in the first place). A renamed copy of the old reference
        file is kept as a backup.


        Arguments
        ---------

        ref_file_path: `str`
            Path to the reference file. """
        reference = pd.read_json(ref_file_path)
        if not reference.index.equals(self._df.index):
            raise ValueError("Index mismatch between business plan and "
                             "reference file")
        bp_not_equal_to_ref: List[str] = []
        missing_from_ref: List[str] = []
        missing_from_bp: List[str] = []
        for key, value in self._df.items():
            if key in reference:
                if not np.allclose(value, reference[key]):
                    bp_not_equal_to_ref.append(key)
            else:
                missing_from_ref.append(key)
        for key in reference:
            if key not in self._df:
                missing_from_bp.append(key)
        if bp_not_equal_to_ref or missing_from_ref or missing_from_bp:
            msg = ""
            if bp_not_equal_to_ref:
                lines = len(bp_not_equal_to_ref)
                plural = lines > 1
                msg += (f"{lines} line{'s' if plural else ''} of BP "
                        f"'{self.name}' {'are' if plural else 'is'} not equal "
                        f"to reference file '{ref_file_path}':\n"
                        + "".join(f"- {line}\n" for line in bp_not_equal_to_ref))
            if missing_from_ref:
                lines = len(missing_from_ref)
                plural = lines > 1
                msg += (f"\n{lines} line{'s' if plural else ''} of BP "
                        f"'{self.name}' {'are' if plural else 'is'} missing "
                        f"from reference file '{ref_file_path}':\n"
                        + "".join(f"- {line}\n" for line in missing_from_ref))
            if missing_from_bp:
                lines = len(missing_from_bp)
                plural = lines > 1
                msg += (f"\n{lines} line{'s' if plural else ''} of reference "
                        f"file '{ref_file_path}' {'are' if plural else 'is'} "
                        f"missing from BP '{self.name}':\n"
                        + "".join(f"- {line}\n" for line in missing_from_bp))
            msg += f"\n\nUpdate reference file '{ref_file_path}'?"
            if (MessageBox(msg,
                           "Business plan",
                           win32con.MB_YESNO | win32con.MB_DEFBUTTON2)
                    == win32con.IDYES):
                path = Path(ref_file_path)
                suffix = path.suffix
                date_time = (datetime.fromtimestamp(path.stat().st_mtime)
                             .strftime('%Y %m %d %H %M %S'))
                path.rename(Path(f'{path.with_suffix("")} {date_time}{suffix}'))
                self._df.to_json(ref_file_path)

        else:
            MessageBox(f"All {len(self._df.columns)} lines of BP "
                       f"'{self.name}' are equal to reference file "
                       f"'{ref_file_path}'",
                       "Business plan")


def min(*line: pd.Series) -> pd.Series:
    """ Return the element-wise minimum of several pandas.Series.

    **Credits** -- Based on `Andy Hayden's code
    <https://stackoverflow.com/a/16993415>`_ """
    return pd.DataFrame([*line]).min()


def max(*line: pd.Series) -> pd.Series:
    """ Return the element-wise maximum of several pandas.Series.

    **Credits** -- Based on `Andy Hayden's code
    <https://stackoverflow.com/a/16993415>`_ """
    return pd.DataFrame([*line]).max()


def percent_of(s2: pd.Series,
               percent: float,
               shift: int = 0) -> Simulator:
    """ Simulator: calculate x% of a BP line.


    Arguments
    ---------

    s2: `pandas.series`
        The business line to be used as the basis for the simulation.

    percent: `float`
        Factor by which `s2` is to be multiplied for the simulation.

    shift: `int`
        Number of periods `s2` is to be shifted before multiplying it by
        `percent`.


    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `s1` denotes the business
        plan line on which the simulation is being performed. The simulation
        will set, for `i` in :ref:`index_values <index_values>`::

          s1.loc[i] = s2.shift(-shift, fill_value=0).loc[i] * percent """

    def simulator(df: pd.DataFrame,
                  s1: pd.Series,
                  index_values: List[Any],
                  start_index: Any,
                  end_index: Any,
                  start_loc: int,
                  end_loc: int) -> List[float]:
        return list(s2.shift(-shift, fill_value=0).loc[start_index: end_index]
                    * percent)

    return simulator


def actualise(percent: float,
              value: Optional[float] = None,
              reference: Optional[Any] = None) -> Simulator:
    """ Simulator -- Actualise a value x% per year, against a reference period.


    Arguments
    ---------

    percent: `float`
        Percentage by which `value` is to be actualised.

    value: `Optional[float]`, defaults to ``None``
        Value to be actualised.

    reference: `Optional[Any]`, defaults to ``None``
        Reference period against which `value` is to be actualised.


    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `s` denotes the business
        plan line on which the simulation is being performed, and
        `reference_loc` is the integer position corresponding to index value
        `reference`.

        - If both `value` and `reference` are specified, the simulation
          will set::

            s.loc[reference] = value

          For `reference_loc` < `i` <= :ref:`end_loc <end_loc>`::

            s.iloc[i] = s.iloc[i - 1] * (1 + percent)

          For :ref:`start_loc <start_loc>` <= `i` < `reference_loc`::

            s.iloc[i] = s.iloc[i + 1] / (1 + percent)

        - If `value` is specified and `reference` is defaulted, the
          simulation will set::

            s.loc[start_index] = value

          For `reference_loc` < `i` <= :ref:`end_loc <end_loc>`::

            s.iloc[i] = s.iloc[i - 1] * (1 + percent)

        - If both `value` and `reference` are defaulted, the simulation
          will set, for :ref:`start_loc <start_loc>` <= `i` <=
          :ref:`end_loc <end_loc>`::

              s.iloc[i] = s.iloc[i - 1] * (1 + percent) """

    def simulator(df: pd.DataFrame,
                  s: pd.Series,
                  index_values: List[Any],
                  start_index: Any,
                  end_index: Any,
                  start_loc: int,
                  end_loc: int) -> List[float]:
        if value is None:
            if reference is not None:
                raise ValueError("Cannot specify 'reference' and default 'value'")
            if start_loc == 0:
                raise ValueError("Invalid start index", start_index)
            _value = s.iloc[start_loc - 1]
        else:
            _value = value
        if reference:
            _reference = s.index.get_loc(reference)
        else:
            if value:
                _reference = start_loc
            else:
                if start_loc == 0:
                    raise ValueError("Invalid start index", start_index)
                _reference = start_loc - 1
        return [_value * (1 + percent) ** (i - _reference)
                for i in range(start_loc, end_loc + 1)]

    return simulator


def actualise_and_cumulate(s2: pd.Series, percent: float) -> Simulator:
    """ Simulator: cumulate values in a BP line while actualising them x% per year.


    Arguments
    ---------

    s2: `pandas.series`
        The business line to be actualised and cumulated.

    percent: `float`
        Percentage by which `s2` is to be actualised.


    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `s1` denotes the business
        plan line on which the simulation is being performed. The simulation
        will set, for `i` in :ref:`index_values <index_values>`::

          s1.loc[i] = (s1.shift(1, fill_value=0).loc[i]
                       + s2.shift(1, fill_value=0).loc[i]) * (1 + percent)
    """

    def simulator(df: pd.DataFrame,
                  s1: pd.Series,
                  index_values: List[Any],
                  start_index: Any,
                  end_index: Any,
                  start_loc: int,
                  end_loc: int) -> List[float]:
        simulation = []
        cumulated = s1.shift(1, fill_value=0).loc[start_index]
        for value in s2.shift(1, fill_value=0).loc[start_index: end_index]:
            cumulated = (cumulated + value) * (1 + percent)
            simulation.append(cumulated)
        return simulation

    return simulator


def from_list(values: List[float], start: Optional[Any] = None) -> Simulator:
    """ Simulator: initialize a BP line from a list of values.


    Arguments
    ---------

    values: `List[float]`
        Values to be used to initialize the BP line.

    start: `Optional[Any]`, defaults to ``None``
        The index in the BP line for the first element in `values`. If omitted,
        it defaults to the first index in the BP line.


    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `bp_line` denotes the business
        plan line on which the simulation is being performed, and
        `values_start_loc` is the integer position corresponding to index value
        `start`. The simulation will set, for :ref:`start_loc <start_loc>` <=
        `i` <= :ref:`end_loc <end_loc>`::

          bp_line.iloc[i] = values[i - values_start_loc] """

    def simulator(df: pd.DataFrame,
                  s1: pd.Series,
                  index_values: List[Any],
                  start_index: Any,
                  end_index: Any,
                  start_loc: int,
                  end_loc: int) -> List[float]:
        values_start = start or s1.index[0]
        values_start_loc = s1.index.get_loc(values_start)
        if not (values_start_loc <= start_loc):
            raise ValueError(f"start ({values_start}) should be <= start_index "
                             f"({start_index})")
        length = end_loc - start_loc + 1
        if not(start_loc - values_start_loc + length <= len(values)):
            raise ValueError("Not enough elements in values")
        return values[start_loc - values_start_loc:
                      start_loc - values_start_loc + length]

    return simulator


def one_offs(one_offs: Dict[Hashable, float], default_value: float = 0) -> Simulator:
    """ Simulator: initialize a BP line with one_off values.


    Arguments
    ---------

    one_offs: `Dict[Hashable, float]`
        Dictionnary whose keys are indexes into the BP line and whose values
        are used to initialize the BP line for the corresponding indexes. All
        other values in the BP line are set to `default_value`.

    default_value: `float`, defaults to ``0``
        Default value applied to all index values in the BP line, except those
        in ``one_offs.keys()``.


    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `bp_line` denotes the
        business plan line on which the simulation is being performed. The
        simulation will set, for `index` in :ref:`index_values <index_values>`::

          bp_line.loc[index] = one_offs.get(index, default_value) """

    def simulator(df: pd.DataFrame,
                  s1: pd.Series,
                  index_values: List[Any],
                  start_index: Any,
                  end_index: Any,
                  start_loc: int,
                  end_loc: int) -> List[float]:
        return [one_offs.get(index, default_value) for index in index_values]

    return simulator


def recurring(value: float,
              start: Optional[Any] = None,
              end: Optional[Any] = None,
              default_value: float = 0) -> Simulator:
    """ Simulator: initialize a BP line with a recurring value.


    Arguments
    ---------

    value: `float`
        The BP line is initialized with this value, from index `start` to index
        `end` (inclusive).

    start: `Optional[Any]`, defaults to ``None``
        Start index for the recurring value. If omitted, it defaults to the
        first index in the BP line.

    end: `Optional[Any]`, defaults to ``None``
        End index for the recurring value. If omitted, it defaults to the
        last index in the BP line.

    default_value: `float`, defaults to ``0``
        Default value given to BP line elements which are not between `start`
        and `end` (see below).


    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `bp_line` denotes the
        business plan line on which the simulation is being performed. The
        simulation will set, for `index` in :ref:`index_values <index_values>`::

          bp_line.loc[index] = value if (start <= index <= end) else default_value
    """

    def simulator(df: pd.DataFrame,
                  s1: pd.Series,
                  index_values: List[Any],
                  start_index: Any,
                  end_index: Any,
                  start_loc: int,
                  end_loc: int) -> List[float]:
        _start = start or s1.index[0]
        _end = end or s1.index[-1]
        return [value if (_start <= index <= _end) else default_value
                for index in index_values]

    return simulator
