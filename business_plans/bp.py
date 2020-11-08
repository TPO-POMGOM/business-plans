""" Model a business plan.


**Revision history**

- 9-Avr-2019 TPO -- Created this module.

- 27-Sep-2020 TPO -- Created v0.2: replace class ``BP`` with
  ``pandas.DataFrame`` and class ``BPTimeSeries`` with ``pandas.Series``.

- 18-Oct-2020 TPO -- Initial release of v0.2.

- 4-Nov-2020 TPO - Created v0.3: generalize business plan index to any strictly
  increasing sequence. """

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd

if os.environ.get('READTHEDOCS', 'False') != 'True':
    import win32con
    from win32ui import MessageBox


__all__ = [
    'actualise',
    'actualise_and_cumulate',
    'BP',
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
             update_instructions="See {source} for more information."
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
#: ``Callable[[pandas.DataFrame, pandas.Series, Any, Any], List[float]]``
Simulator = Callable[[pd.DataFrame, pd.Series, Any, Any], List[float]]


@pd.api.extensions.register_dataframe_accessor("bp")
class BPAccessor:
    """ Pandas ``DataFrame`` accessor for business plan methods and properties (``bp``).

    ``DataFrame``'s representing a business plan can be created by using
    factory function :func:`BP`. Methods and properties specific to  business
    plans can then be used by specifying the ``bp`` accessor, which is
    implemented by this class.


    **Example**

    .. code-block:: python

        >>> df = BP("Test", range(2020, 2031)))
        >>> print(df.bp.name)
        Test
        >>> df.bp.line(name="Revenue", history=[100, 110, 120])
        2020    100.0
        2021    110.0
        2022    120.0
        2023      0.0
        2024      0.0
        2025      0.0
        2026      0.0
        2027      0.0
        2028      0.0
        2029      0.0
        2030      0.0
        dtype: float64
        >>> print(df.at[2020, "Revenue"])
        100.0


    Attributes
    ----------

    name: `str`, initial value is ``""`` TODO: wrong, correct it
        Name of the business plan line. It can be used to access the business
        plan line, see example above.

    assumptions: `List[` :data:`Assumption` `]`, initial value is ``[]``
        Assumptions on which the business plan is based. Assumptions are
        declared by appending objects of class :class:`ExternalAssumption` or
        class :class:`HistoryBasedAssumption` to attribute `assumptions`. For
        instance::

          my_bp.bp.assumptions.append(ExternalAssumption(
              name="Some assumption",
              last_update=date(2020, 10, 12),
              update_every_x_year=2,
              update_instructions="See {source} for more information."
              update_links={'source': UpdateLink("reference", "http://ref.com")})

    index_format: `str`, initial value is ``'%d/%m/%Y'``
        TODO """

    def __init__(self, df: pd.DataFrame):
        if not(df.index.is_monotonic_increasing and df.index.is_unique):
            raise ValueError("'bp' accessor can only be used on DataFrames's "
                             "with strictly increasing index values.")
        self._df = df
        self._years_of_history: Dict[str, int] = {}
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
                df.bp.index_to_datetime = lambda index: date(year=index, month=1, day=1)
                df.bp.index_format = '%Y'
        """
        if isinstance(index, datetime):
            return index
        else:
            raise ValueError("Index value is not a datetime instance, method "
                             "index_to_datetime() must be overriden.")

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
              business plan ``DataFrame``, as column `name`. Note that new
              business plan lines with history data (as opposed to business plan
              lines which are computed from other lines) should only be added
              to the business plan in this way, to ensure that data required by
              methods :func:`years_of_history` and :func:`max_history_lag` is
              properly intialized.

            - An empty string -- The new business plan line is not added to the
              business plan ``DataFrame``.

        default_value: `float`, defaults to ``0``
            Value used to initialize elements in the business plan line which
            are not otherwise initialized by `history` or `simulation`.

        history: `Optional[Union[pandas.Series, List[float]]]`, defaults to ``None``
            When a ``pandas.Series`` or ``List[float]`` of n elements is
            specified, the first n elements of the business plan line are
            initialised with those elements. Method :func:`years_of_history`
            can later be used to retrieve n.

        simulation: `Optional[` :class:`Simulator` `]`, defaults to ``None``
            When `simulation` is specified, it is used to calculate the values
            of elements `simulation_start` to `simulation_end` (inclusive) of
            the business plan line, where:

            .. _simulation_start:

            - `simulation_start` is equal to:

                - If argument `simulate_from` is specified: ``simulate_from``

                - Otherwise, if argument `history` is specified:
                  ``df.index[len(history)]``

                - Otherwise: ``df.index[0]``

            .. _simulation_end:

            - `simulation_end` is equal to:

                - If argument `simulate_until` is specified: ``simulate_until``

                - Otherwise: ``df.index[-1]``

            - `simulation` is a function with the following signature::

                simulation(df: pandas.DataFrame,
                           s: pandas.Series,
                           start: Any,
                           end: Any) -> List[float]

              It returns a list of::

                df.index.get_loc(simulation_end) - df.index.get_loc(simulation_start) + 1

              elements, which are then assigned to elements `simulation_start`
              to `simulation_end` of the business plan line.

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
            years_of_history = 0
        else:
            if len(history) > index.size:
                raise ValueError(f"Argument 'history' provides {len(history)} "
                                 f"values, max {index.size} expected")
            line.iloc[:len(history)] = history
            years_of_history = len(history)
        if simulation is not None:
            simulation_start = simulate_from or index[years_of_history]
            if simulation_start not in index:
                raise KeyError(simulation_start)
            simulation_end = simulate_until or index[-1]
            if simulation_end not in index:
                raise KeyError(simulation_end)
            if not (simulation_start <= simulation_end):
                raise ValueError(f"Start of simulation ({simulation_start}) "
                                 f"should be <= end of simulation ({simulation_end})")
            simulation_length = (index.get_loc(simulation_end)
                                 - index.get_loc(simulation_start) + 1)
            result = simulation(self._df, line, simulation_start, simulation_end)
            if len(result) != simulation_length:
                raise ValueError(f"list returned by simulator should have "
                                 f"{simulation_length} elements")
            line.loc[simulation_start: simulation_end] = result
        if name:
            self._df[name] = line
            self._years_of_history[name] = years_of_history
            self._max_history_lag[name] = max_history_lag
        return line

    def years_of_history(self, name: str) -> int:
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
        return self._years_of_history.get(name, 0)

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
            if MessageBox(msg,
                          "Business plan",
                          win32con.MB_YESNO | win32con.MB_DEFBUTTON2) == win32con.IDYES:
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


def BP(name: str,  # TODO: remove ???
       start: int,
       end: int) -> pd.DataFrame:
    """ Return a ``pandas.DataFrame`` representing a business plan.

    The DataFrame's columns represent the lines of the business plan (such as
    revenue, costs, margin, etc.). They are created by using method
    :func:`~BPAccessor.line`.

    The DataFrame's rows are the years which the business plan spans, from
    `start` to `end` (included).


    **Example**

    .. code-block:: python

        >>> df = BP("Test", 2020, 2030)
        >>> print(df.bp.name)
        Test
        >>> df.bp.line(name="Revenue", history=[100, 110, 120])
        2020    100.0
        2021    110.0
        2022    120.0
        2023      0.0
        2024      0.0
        2025      0.0
        2026      0.0
        2027      0.0
        2028      0.0
        2029      0.0
        2030      0.0
        dtype: float64
        >>> print(df.at[2020, "Revenue"])
        100.0

    Arguments
    ---------

    name: `str`
        Name of the business plan.

    start: `int`
        First year of the business plan.

    end: `int`
        Last year of the business plan. """
    if end <= start:
        raise ValueError("'end' should be > 'start'")
    df = pd.DataFrame(dtype='float64', index=range(start, end + 1))
    df.bp.name = name
    return df


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
        will set, for :ref:`simulation_start <simulation_start>` <= `i` <=
        :ref:`simulation_end <simulation_end>`::

          s1.loc[i] = s2.shift(-shift, fill_value=0).loc[i] * percent """

    def simulator(df: pd.DataFrame, s1: pd.Series, start: Any, end: Any) -> List[float]:
        return list(s2.shift(-shift, fill_value=0).loc[start: end] * percent)

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
        plan line on which the simulation is being performed.

        - If both `value` and `reference` are specified, the simulation
          will set::

            s.loc[reference] = value

          For `reference` < `i` <= :ref:`simulation_end <simulation_end>`::

            s.loc[i] = s.loc[i - 1] * (1 + percent)

          For :ref:`simulation_start <simulation_start>` <= `i` < `reference`::

            s.loc[i] = s.loc[i + 1] / (1 + percent)

        - If `value` is specified and `reference` is defaulted, the
          simulation will set::

            s.loc[simulation_start] = value

          For `reference` < `i` <= :ref:`simulation_end <simulation_end>`::

            s.loc[i] = s.loc[i - 1] * (1 + percent)

        - If both `value` and `reference` are defaulted, the simulation
          will set, for :ref:`simulation_start <simulation_start>` <= `i` <=
          :ref:`simulation_end <simulation_end>`::

              s.loc[i] = s.loc[i - 1] * (1 + percent) """

    def simulator(df: pd.DataFrame, s: pd.Series, start: Any, end: Any) -> List[float]:
        start_loc = s.index.get_loc(start)
        end_loc = s.index.get_loc(end)
        if value is None and reference is not None:
            raise ValueError("Cannot specify 'reference' and default 'value'")
        if value is None and start_loc == 0:
            raise ValueError("Cannot default 'history', 'simulate_from' and 'value'")
        if value:
            _value = value
        else:
            if start_loc == 0:
                raise ValueError("Invalid start index", start)
            _value = s.iloc[start_loc - 1]
        if reference:
            _reference = s.index.get_loc(reference)
        else:
            if value:
                _reference = start_loc
            else:
                if start_loc == 0:
                    raise ValueError("Invalid start index", start)
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
        will set, for :ref:`simulation_start <simulation_start>` <= `i` <=
        :ref:`simulation_end <simulation_end>`::

          s1.loc[i] = (s1.shift(1, fill_value=0).loc[i]
                       + s2.shift(1, fill_value=0).loc[i]) * (1 + percent)

    """

    def simulator(df: pd.DataFrame, s1: pd.Series, start: int, end: int) -> List[float]:
        simulation = []
        cumulated = s1.shift(1, fill_value=0).loc[start]
        for value in s2.shift(1, fill_value=0).loc[start: end]:
            cumulated = (cumulated + value) * (1 + percent)
            simulation.append(cumulated)
        return simulation

    return simulator
