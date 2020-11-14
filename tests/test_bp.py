""" Test module business_plans.bp

**Revision history**

- 13-Nov-2020 TPO -- Created this module. """

from datetime import date, datetime, timedelta
from typing import Any, List

import pandas as pd
import pytest

from business_plans.bp import ExternalAssumption, Formatter, \
    HistoryBasedAssumption, UpdateLink


@pytest.fixture(scope="module")
def bp() -> pd.DataFrame:
    """ Module fixture - Unmutable and hidden Window instance. """
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
        assert bp.bp.datetime_to_str(datetime(2020, 1, 2), fmt) == result  # <===

    def test_datetime_to_str_with_invalid_fmt_raises_error(
            self, bp: pd.DataFrame) -> None:
        with pytest.raises(TypeError):
            bp.bp.datetime_to_str(datetime(2020, 1, 2), fmt=999)  # <===
