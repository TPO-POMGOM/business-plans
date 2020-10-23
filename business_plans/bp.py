""" Model a business plan.

**Revision history**

- 9-Avr-2019 TPO -- Created this module.

- 27-Sep-2020 TPO -- Created v0.2, replacing class ``BP`` with
  ``pandas.DataFrame`` and class ``BPTimeSeries`` with ``pandas.Series``.

- 18-Oct-2020 TPO -- Initial release of v0.2. """

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

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
        to be up to date and will not be reported by :class:`~report.BPStatus`
        report elements. Otherwise, :class:`~report.BPStatus` elements will
        report this assumption as being out of date and will display
        instructions on how to update it.

    update_instructions: `str`
        Instructions displayed by the :class:`~report.BPStatus` report element
        when the assumption needs to be updated. The string may refer to the
        keys in argument `update_links` to display web sites hyperlinks in the
        instructions. For example::

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

    start: `int`
        The year corresponding to the first element in `history`.

    last_update: `datetime.date`
        Date of the most recent update the assumption has received.

    update_every_x_year: `float`
        Maximum duration between updates, in years. If the time elapsed since
        the last update is less than this value, the assumption is considered
        to be up to date and will not be reported by :class:`~report.BPStatus`
        report elements. Otherwise, :class:`~report.BPStatus` elements will
        report this assumption as being out of date and will display -- as an
        aid to decision -- a graph showing historical data, the mean for
        historical data values, and the current value of the assumption. """

    name: str
    value: float
    history: List[float]
    start: int
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
#: ``Callable[[pandas.Series, int, int], List[float]]``
Simulator = Callable[[pd.Series, int, int], List[float]]


@pd.api.extensions.register_dataframe_accessor("bp")
class BPAccessor:
    """ Pandas ``DataFrame`` accessor for business plan methods and properties (``bp``).

    ``DataFrame``'s representing a business plan can be created by using
    factory function :func:`BP`. Methods and properties specific to  business
    plans can then be used by specifying the ``bp`` accessor, which is
    implemented by this class.


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


    Attributes
    ----------

    name: `str`, initial value is ``""``
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
"""

    def __init__(self, df: pd.DataFrame):
        self._df = df
        self._start = self._df.index.min()
        self._end = self._df.index.max()
        self._years_of_history: Dict[str, int] = {}
        self._max_history_lag: Dict[str, int] = {}
        self.name = ""
        self.assumptions: List[Assumption] = []

    @property
    def start(self) -> int:
        """ First year of the business plan (`int`, get only) """
        return self._start

    @property
    def end(self) -> int:
        """ Last year of the business plan (`int`, get only) """
        return self._end

    @property
    def years(self) -> int:
        """ Number of years in the business plan (`int`, get only) """
        return self._end - self._start + 1

    def line(self,
             name: str = "",
             *,
             default_value: float = 0,
             history: Optional[Union[pd.Series, List[float]]] = None,
             simulation: Optional[Simulator] = None,
             simulate_from: Optional[int] = None,
             simulate_until: Optional[int] = None,
             max_history_lag: int = 1) -> pd.Series:
        """ Return a new business plan line.

        If ``df`` is a ``pandas.DataFrame``, ``df.bp.line()`` returns a new
        business plan line, represented as  ``pandas.Series`` object whose
        index is ``range(df.bp.start, df.bp.end + 1)``, and whose dtype is
        ``float64``.


        Arguments
        ---------

        name: `str`, defaults to ``""``
            Name of the business plan line. It can be either:

            - A non-empty string -- The new business plan line is added to the
              business plan ``DataFrame``, as column `name`. Note that new
              business plan lines with history data (as opposed to business plan
              lines which are computed from other lines) should only be added
              to the business plan in this way, to ensure data required by
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
            can be used to retrieve n.

        simulation: `Optional[` :class:`Simulator` `]`, defaults to ``None``
            When `simulation` is specified, it is used to calculate the values
            of elements `simulation_start` to `simulation_end` (inclusive) of
            the business plan line, where:

            .. _simulation_start:

            - `simulation_start` is equal to:

                - If argument `simulate_from` is specified: ``simulate_from``

                - Otherwise, if argument `history` is specified:
                  ``bp.start + len(history)``

                - Otherwise: ``bp.start``

            .. _simulation_end:

            - `simulation_end` is equal to:

                - If argument `simulate_until` is specified: ``simulate_until``

                - Otherwise: ``bp.end``

            - `simulation` is a function with the following signature:

                ``simulation(s: pandas.Series, start: int, end: int) -> List[float]``

              It returns a list of ``(simulation_end - simulation_start + 1)``
              elements, which are then assigned to elements `simulation_start`
              to `simulation_end` of the business plan line.

        simulate_from: `Optional[int]`, defaults to ``None``
            See argument `simulation` above.

        simulate_until: `Optional[int]`, defaults to ``None``
            See argument `simulation` above.

        max_history_lag: `int`, defaults to ``1``
            Specifies the maximum number of years history data for this
            business plan line may lag behind the current year before class
            :class:`~report.BPStatus` issues a warning that history is missing.
            Method :func:`max_history_lag` can be used to retrieve this value.


        Returns
        -------

        pandas.Series
            representing the new business plan line. """

        line = pd.Series(data=default_value,
                         dtype='float64',
                         index=range(self._start, self._end + 1))
        if history is None:
            years_of_history = 0
        else:
            if len(history) > self.years:
                raise ValueError(f"Argument 'history' provides {len(history)} "
                                 f"values, max {self.years} expected")
            if len(history) > 0:
                line.iloc[:len(history)] = history
                years_of_history = len(history)
        if simulation is not None:
            simulation_start = simulate_from or (self._start + years_of_history)
            if not (self._start <= simulation_start):
                raise ValueError(f"Should have {self._start} <= simulate_from")
            simulation_end = simulate_until or self._end
            if not (simulation_start <= simulation_end <= self._end):
                raise ValueError(f"Should have {simulation_start} <= simulate_until <= "
                                 f"{self._end}")
            simulation_length = simulation_end - simulation_start + 1
            result = simulation(line, simulation_start, simulation_end)
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

    def max_history_lag(self, name: str) -> int:
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
            may lag behind the current year before class :class:`~report.BPStatus`
            issues a warning that history is missing. This is the value supplied
            to argument `max_history_lag` of method :func:`line` at the time
            the business plan line was created. """
        return self._max_history_lag.get(name, 1)

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


def BP(name: str,
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
        Number of years by which `s2` is to be shifted before multiplying it by
        `percent`.


    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `s1` denotes the business
        plan line on which the simulation is being performed. The simulation
        will set, for :ref:`simulation_start <simulation_start>` <= `year` <=
        :ref:`simulation_end <simulation_end>`::

          s1.loc[year] = s2.loc[year + shift] * percent """

    def simulator(s1: pd.Series, start: int, end: int) -> List[float]:
        if not(s2.index.min() <= start + shift <= end + shift <= s2.index.max()):
            raise ValueError("Should have s1.start <= start + shift <= "
                             "end + shift <= s2.end")
        simulation = [s2[i] * percent
                      for i in range(start + shift, end + shift + 1)]
        return simulation

    return simulator


def actualise(percent: float,
              value: Optional[float] = None,
              reference_year: Optional[int] = None) -> Simulator:
    """ Simulator -- Actualise a value x% per year, against a reference year.


    Arguments
    ---------

    percent: `float`
        Percentage by which `value` is to be actualised.

    value: `Optional[float]`, defaults to ``None``
        Value to be actualised.

    reference_year: `Optional[int]`, defaults to ``None``
        Reference year against which `value` is to be actualised.

    Returns
    -------

    :data:`Simulator`
        Simulator function to be passed to the `simulation` argument of method
        :func:`~BPAccessor.line`. In the following, `s` denotes the business
        plan line on which the simulation is being performed.

        - If both `value` and `reference_year` are specified, the simulation
          will set::

            s.loc[reference_year] = value

          For `reference_year` < `year` <= :ref:`simulation_end <simulation_end>`::

            s.loc[year] = s.loc[year - 1] * (1 + percent)

          For :ref:`simulation_start <simulation_start>` <= `year` < `reference_year`::

            s.loc[year] = s.loc[year + 1] / (1 + percent)

        - If `value` is specified and `reference_year` is defaulted, the
          simulation will set::

            s.loc[simulation_start] = value

          For `reference_year` < `year` <= :ref:`simulation_end <simulation_end>`::

            s.loc[year] = s.loc[year - 1] * (1 + percent)

        - If both `value` and `reference_year` are defaulted, the simulation
          will set, for :ref:`simulation_start <simulation_start>` <= `year` <=
          :ref:`simulation_end <simulation_end>`::

              s.loc[year] = s.loc[year - 1] * (1 + percent) """

    def simulator(s: pd.Series, start: int, end: int) -> List[float]:
        if value is None and reference_year is not None:
            raise ValueError("Cannot specify reference_year and default value")
        if value is None and start == s.index.min():
            raise ValueError("history, simulate_from and value cannot all be None")
        _value = value or s.loc[start - 1]
        _reference_year = reference_year or (start if value else (start - 1))
        return [_value * (1 + percent) ** (year - _reference_year)
                for year in range(start, end + 1)]

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
        will set, for :ref:`simulation_start <simulation_start>` <= `year` <=
        :ref:`simulation_end <simulation_end>`::

          s1.loc[year] = (s1.loc[year - 1] + s2.loc[year - 1]) * (1 + percent)

        Where by convention ``s1.loc[year - 1]`` is replaced by ``0`` for
        ``year <= s1.index.min()`` (instead of raising ``KeyError``), and
        similarly ``s2.loc[year - 1]`` is replaced by ``0`` for
        ``year <= s2.index.min()``. """

    def simulator(s1: pd.Series, start: int, end: int) -> List[float]:
        simulation = []
        value = s1.loc[start - 1] if start > s1.index.min() else 0
        s2_start = s2.index.min()
        for year in range(start, end + 1):
            value = ((value + (s2.loc[year - 1] if year > s2_start else 0))
                     * (1 + percent))
            simulation.append(value)
        return simulation

    return simulator
