""" Test module business_plans.bp

**Revision history**

- 13-Nov-2020 TPO -- Created this module.

- 16-Nov-2020 TPO -- Initial release. """

from datetime import date, datetime, timedelta
from typing import Any, List, Optional

import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal
import pytest

from business_plans.bp import actualise, actualise_and_cumulate, \
    ExternalAssumption, Formatter, from_list, HistoryBasedAssumption, max as bp_max, \
    min as bp_min, percent_of, UpdateLink


@pytest.fixture(scope="function")
def bp() -> pd.DataFrame:
    """ Function fixture - bp instance. """
    bp = pd.DataFrame(
        dtype='float64',
        index=pd.date_range(start=datetime(2020, 1, 1), periods=10, freq='YS'))
    yield bp


class TestUpdateLinkClass:

    def test_constructor(self) -> None:
        update_link = UpdateLink("reference site", "http://ref.com")  # <===
        assert update_link.title == "reference site"
        assert update_link.url == "http://ref.com"


class TestExternalAssumptionClass:

    @pytest.mark.parametrize('days, update_required', [
        (365 * 2 + 2, True),
        (365 * 2 - 2, False)])
    def test_constructor(self, days: int, update_required: bool) -> None:
        update_link = UpdateLink("reference site", "http://ref.com")
        last_update = date.today() - timedelta(days=days)
        assumption = ExternalAssumption(  # <===
            name="Some assumption",
            last_update=last_update,
            update_every_x_year=2,
            update_instructions="See {source} for more information.",
            update_links={'source': update_link})
        assert assumption.name == "Some assumption"
        assert assumption.last_update == last_update
        assert assumption.update_every_x_year == 2
        assert assumption.update_instructions == "See {source} for more information."
        assert assumption.update_links == {'source': update_link}
        assert assumption.update_required == update_required


class TestHistoryBasedAssumptionClass:

    @pytest.mark.parametrize('days, history, update_required', [
        (365 * 2 + 2, [1, 2, 3, 4], True),
        (365 * 2 + 2, [1, 2, 3], False),
        (365 * 2 - 2, [1, 2, 3, 4], False)])
    def test_constructor(self,
                         days: int,
                         history: List[float],
                         update_required: bool) -> None:
        last_update = date.today() - timedelta(days=days)
        assumption = HistoryBasedAssumption(  # <===
            name="Some assumption",
            value=55.0,
            history=history,
            start=2020,
            last_update=last_update,
            update_every_x_year=2)
        assert assumption.name == "Some assumption"
        assert assumption.value == 55.0
        assert assumption.history == history
        assert assumption.start == 2020
        assert assumption.update_every_x_year == 2
        assert assumption.update_required == update_required


class TestBPAccessorClass:

    def test_constructor(self) -> None:
        bp = pd.DataFrame(index=[1, 2, 4, 5, 10])
        assert bp.bp.name == ""  # <===
        assert bp.bp.index_format == '%d/%m/%Y'
        assert bp.bp.assumptions == []

    @pytest.mark.parametrize('index', [
        [1, 2, 4, 4, 10],
        [1, 2, 4, 3, 10]])
    def test_constructor_with_non_increasing_index_raises_error(
            self, index: List[Any]) -> None:
        bp = pd.DataFrame(index=index)
        with pytest.raises(ValueError):
            bp.bp.name  # <===

    def test_index_to_datetime_on_datetime_value(self, bp: pd.DataFrame):
        index = datetime(2020, 1, 1)
        assert bp.bp.index_to_datetime(index) == index  # <===

    def test_index_to_datetime_on_non_datetime_value_raises_error(
            self, bp: pd.DataFrame):
        index = 2020
        with pytest.raises(ValueError):
            bp.bp.index_to_datetime(index)  # <===

    @pytest.mark.parametrize('fmt, result', [
        (None, '02/01/2020'),
        ('%Y/%m/%d', '2020/01/02'),
        (lambda index: 'result', 'result')])
    def test_datetime_to_str(
            self, fmt: Formatter, result: str, bp: pd.DataFrame) -> None:
        """ Test with a datetime index. int index tested by test_index_to_str() """
        assert bp.bp.datetime_to_str(datetime(2020, 1, 2), fmt) == result  # <===

    def test_datetime_to_str_with_invalid_fmt_raises_error(
            self, bp: pd.DataFrame) -> None:
        with pytest.raises(TypeError):
            bp.bp.datetime_to_str(datetime(2020, 1, 2), fmt=999)  # <===

    @pytest.mark.parametrize('fmt', [
        None,
        '%Y',
        lambda index: index.strftime('%Y')])
    def test_index_to_str(self, fmt: Formatter) -> None:
        """ Test with an int index. """
        bp = pd.DataFrame(dtype='float64', index=range(2020, 2030))
        bp.bp.index_to_datetime = lambda index: datetime(year=index, month=1, day=1)
        bp.bp.index_format = '%Y'
        assert bp.bp.index_to_str(2020, fmt) == '2020'  # <===

    def test_line_method_name_arg(self, bp: pd.DataFrame) -> None:
        """ Also test default value for arg `default_value`.
            Also test default value for arg `max_history_lag`.
            Also test dtype and index of result. """
        bp.bp.line('New line')  # <===
        assert bp['New line'].tolist() == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        assert bp['New line'].dtype == np.float64
        assert bp['New line'].index.equals(bp.index)
        assert bp.bp.max_history_lag('New line') == timedelta(days=365)

    def test_line_method_default_value_arg(self, bp: pd.DataFrame) -> None:
        """ Also test default value for arg `default_value`. """
        assert (bp.bp.line(default_value=5).tolist()
                == [5, 5, 5, 5, 5, 5, 5, 5, 5, 5])  # <===

    def test_line_method_history_arg(self, bp: pd.DataFrame) -> None:
        """ Also test method `history_size`.
            Also test error case if `history` arg is too long.  """
        bp.bp.line('New line', history=[1, 2, 3, 4])  # <===
        assert bp['New line'].tolist() == [1, 2, 3, 4, 0, 0, 0, 0, 0, 0]
        assert bp.bp.history_size('New line') == 4
        with pytest.raises(ValueError):
            bp.bp.line(history=[1] * 11)  # <===

    @pytest.mark.parametrize('history, from_, until, result', [
        (None, None, None, [20, 21, 22, 23, 24, 25, 26, 27, 28, 29]),
        (None, 2025, None, [0, 0, 0, 0, 0, 25, 26, 27, 28, 29]),
        (None, 2025, 2028, [0, 0, 0, 0, 0, 25, 26, 27, 28, 0]),
        ([1, 2], None, None, [1, 2, 22, 23, 24, 25, 26, 27, 28, 29]),
        ([1, 2], 2025, None, [1, 2, 0, 0, 0, 25, 26, 27, 28, 29])])
    def test_line_method_simulation_happy_cases(
            self,
            history: Optional[List[float]],
            from_: Optional[Any],
            until: Optional[Any],
            result: List[float]) -> None:

        def simulation(df: pd.DataFrame,
                       s: pd.Series,
                       index_values: List[Any],
                       start_index: Any,
                       end_index: Any,
                       start_loc: int,
                       end_loc: int) -> List[float]:
            return list(range(int(start_index - 2000), int(end_index + 1 - 2000)))

        bp = pd.DataFrame(dtype='float64', index=range(2020, 2030))
        assert bp.bp.line(history=history,
                          simulation=simulation,
                          simulate_from=from_,
                          simulate_until=until).tolist() == result  # <===

    @pytest.mark.parametrize('from_, until, error', [
        (2019, None, KeyError),
        (None, 2019, KeyError),
        (2021, 2020, ValueError),
        (None, None, ValueError)])
    def test_line_method_simulation_error_cases(
            self,
            from_: Optional[Any],
            until: Optional[Any],
            error: Exception) -> None:
        bp = pd.DataFrame(dtype='float64', index=range(2020, 2030))
        with pytest.raises(error):  # type: ignore  # Help mypy
            bp.bp.line(simulation=lambda *args: [],
                       simulate_from=from_,
                       simulate_until=until)  # <===

    def test_line_method_max_history_lag_arg(self, bp: pd.DataFrame) -> None:
        """ Also test method `max_history_lag`. """
        bp.bp.line('New line', max_history_lag=timedelta(days=100))  # <===
        assert bp.bp.max_history_lag('New line') == timedelta(days=100)


def test_min_function() -> None:
    assert_series_equal(  # <===  # <===
        bp_min(pd.Series([1, 2, 3]), pd.Series([2, 3, 1]), pd.Series([3, 1, 2])),
        pd.Series([1, 1, 1]))


def test_max_function() -> None:
    assert_series_equal(  # <===
        bp_max(pd.Series([1, 2, 3]), pd.Series([2, 3, 1]), pd.Series([3, 1, 2])),
        pd.Series([3, 3, 3]))


@pytest.mark.parametrize('shift, result', [
    (0, [1, 2, 3, 4]),
    (-1, [0, 1, 2, 3]),
    (1, [2, 3, 4, 0])])
def test_percent_of_function(shift: int, result: List[float]) -> None:
    index = [2020, 2021, 2022, 2023]
    df = pd.DataFrame(index=index)
    s1 = pd.Series([10, 20, 30, 40], index=index)
    s2 = pd.Series([100, 200, 300, 400], index=index)
    percent = .01
    simulator = percent_of(s2, percent, shift)
    assert simulator(df, s1, index, 2020, 2023, 0, 3) == result  # <===


@pytest.mark.parametrize('value, reference, result', [
    (None, None, [101.0, 102.01, 103.03010000000002, 104.060401, 105.10100501000001]),
    (10, None, [10.0, 10.1, 10.201, 10.30301, 10.4060401]),
    (10, 2023, [9.802960494069207, 9.900990099009901, 10.0, 10.1, 10.201])])
def test_actualise_function_happy_cases(value: Optional[float],
                                        reference: Optional[Any],
                                        result: List[float]) -> None:
    index = [2020, 2021, 2022, 2023, 2024, 2025]
    df = pd.DataFrame(index=index)
    s = pd.Series([100, 200, 300, 400, 500, 600], index=index)
    percent = .01
    simulator = actualise(percent, value, reference)
    assert simulator(df, s, index, 2021, 2025, 1, 5) == result  # <===


@pytest.mark.parametrize('value, reference', [
    (None, None),
    (None, 2023)])
def test_actualise_function_error_cases(value: Optional[float],
                                        reference: Optional[Any]) -> None:
    index = [2020, 2021, 2022, 2023, 2024, 2025]
    df = pd.DataFrame(index=index)
    s = pd.Series([100, 200, 300, 400, 500, 600], index=index)
    percent = .01
    simulator = actualise(percent, value, reference)
    with pytest.raises(ValueError):
        simulator(df, s, index, 2020, 2025, 0, 5)  # <===


def test_actualise_and_cumulate_function() -> None:
    index = [2020, 2021, 2022, 2023]
    df = pd.DataFrame(index=index)
    s1 = pd.Series([10, 20, 30, 40], index=index)
    s2 = pd.Series([100, 200, 300, 400], index=index)
    percent = .01
    simulator = actualise_and_cumulate(s2, percent)
    assert (simulator(df, s1, index, 2020, 2023, 0, 3)  # <===
            == [0.0, 101.0, 304.01, 610.0501])


@pytest.mark.parametrize('values_start, start, result', [
    (None, 2020, [0, 1, 2, 3, 4, 5]),
    (None, 2022, [2, 3, 4, 5]),
    (2022, 2023, [1, 2, 3])])
def test_from_list_function_happy_cases(values_start: Optional[Any],
                                        start: Any,
                                        result: List[float]) -> None:
    index = [2020, 2021, 2022, 2023, 2024, 2025]
    df = pd.DataFrame(index=index)
    s = pd.Series([100, 200, 300, 400, 500, 600], index=index)
    simulator = from_list([0, 1, 2, 3, 4, 5], start=values_start)
    assert simulator(df, s, index, start, 2025, start - 2020, 5) == result  # <===


def test_from_list_function_error_cases() -> None:
    index = [2020, 2021, 2022, 2023, 2024, 2025]
    df = pd.DataFrame(index=index)
    s = pd.Series([100, 200, 300, 400, 500, 600], index=index)
    simulator = from_list([0, 1, 2, 3, 4, 5], start=2021)
    with pytest.raises(ValueError):
        simulator(df, s, index, 2020, 2025, 0, 5)  # <===
    simulator = from_list([0, 1, 2, 3, 4], start=2020)
    with pytest.raises(ValueError):
        simulator(df, s, index, 2020, 2025, 0, 5)  # <===
