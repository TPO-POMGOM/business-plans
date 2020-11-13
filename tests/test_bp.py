""" Test module business_plans.bp

**Revision history**

- 13-Nov-2020 TPO -- Created this module. """

from datetime import date, timedelta
from typing import List

import pytest

from business_plans.bp import ExternalAssumption, HistoryBasedAssumption, \
    UpdateLink


class TestUpdateLinkClass:

    def test_factory(self) -> None:
        update_link = UpdateLink("reference site", "http://ref.com")
        assert update_link.title == "reference site"
        assert update_link.url == "http://ref.com"


class TestExternalAssumptionClass:

    @pytest.mark.parametrize('days, update_required', [
        (365 * 2 + 2, True),
        (365 * 2 - 2, False)])
    def test_factory(self, days: int, update_required: bool) -> None:
        update_link = UpdateLink("reference site", "http://ref.com")
        last_update = date.today() - timedelta(days=days)
        assumption = ExternalAssumption(
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
    def test_factory(self,
                     days: int,
                     history: List[float],
                     update_required: bool) -> None:
        last_update = date.today() - timedelta(days=days)
        assumption = HistoryBasedAssumption(
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
