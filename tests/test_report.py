""" Test module business_plans.bp

**Revision history**

- 16-Nov-2020 TPO -- Created this module.

- XX-Nov-2020 TPO -- Initial release. """

from datetime import date, datetime, timedelta
from typing import Any, List, Optional

import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal
import pytest

from business_plans.report import BPChart, BPStatus, Chart, CompareBPsLineChart, \
    Element, LineBPChart, Report, StackedBarBPChart


def strip_spaces(html: str) -> str:
    return '\n'.join(line.strip() for line in html.split('\n'))


class TestElementClass:

    def test_constructor(self) -> None:
        assert Element("Some HTML").html == "Some HTML"


class TestChartClass:

    def test_constructor(self) -> None:
        chart = Chart(datasets='some datasets',
                      title='some title',
                      chart_type='some chart type',
                      labels='[2020, 2021, 2022]',
                      legend_position='some position'
                      )
        assert 'datasets: [\nsome datasets\n]' in strip_spaces(chart.html)
        assert strip_spaces(chart.html).startswith('<h2>some title</h2>')
        assert "type: 'some chart type'," in strip_spaces(chart.html)
        assert 'data: {\nlabels: [2020, 2021, 2022]' in strip_spaces(chart.html)
        assert ("options: {\nlegend: {\nposition: 'some position',"
                in strip_spaces(chart.html))
