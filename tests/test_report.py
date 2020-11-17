""" Test module business_plans.bp

**Revision history**

- 16-Nov-2020 TPO -- Created this module.

- XX-Nov-2020 TPO -- Initial release. """

from datetime import date, datetime, timedelta
from typing import Any, List, Optional, Union

import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal
import pytest
from unittest.mock import call, Mock, patch, PropertyMock

from business_plans.report import BPChart, BPStatus, Chart, CompareBPsLineChart, \
    Element, LegendPosition, LineBPChart, Report, StackedBarBPChart


def strip_spaces(html: str) -> str:
    return '\n'.join(line.strip() for line in html.split('\n'))


def check_chart(chart: Chart,
                width: str,
                height: str,
                legend_position: LegendPosition,
                legend_reverse: bool,
                options: str) -> None:
    html = strip_spaces(chart.html)
    assert 'datasets: [\nsome datasets\n]' in html
    assert html.startswith('<h2>some title</h2>')
    assert "type: 'some chart type'," in html
    assert 'data: {\nlabels: [2020, 2021, 2022]' in html
    if width or height:
        height = height or width
        width = width or height
        width = "width=" + width
        height = "height=" + height
        assert 'responsive: false,\nmaintainAspectRatio: false,' in html
    assert f'{width} {height}></canvas>' in html
    assert f"options: {{\nlegend: {{\nposition: '{legend_position}'," in html
    assert f'reverse: {"true" if legend_reverse else "false"},\n}},' in html
    assert f'{options}\n}}\n}});\n</script>' in html


class TestElementClass:

    def test_constructor(self) -> None:
        assert Element("Some HTML").html == "Some HTML"


class TestChartClass:

    @pytest.mark.parametrize('width, height, legend_position, legend_reverse, options', [
        ('', '', 'right', False, ''),
        ('640', '', 'right', False, ''),
        ('', '480', 'right', False, ''),
        ('640', '480', 'right', False, ''),
        ('', '', 'bottom', False, ''),
        ('', '', 'right', True, ''),
        ('', '', 'right', False, 'some options')])
    def test_constructor(self,
                         width: str,
                         height: str,
                         legend_position: LegendPosition,
                         legend_reverse: bool,
                         options: str) -> None:
        check_chart(Chart(datasets='some datasets',
                          title='some title',
                          chart_type='some chart type',
                          labels='[2020, 2021, 2022]',
                          width=width,
                          height=height,
                          legend_position=legend_position,
                          legend_reverse=legend_reverse,
                          options=options),
                    width, height, legend_position, legend_reverse, options)
