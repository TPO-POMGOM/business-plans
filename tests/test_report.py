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
from typing_extensions import Literal
from unittest.mock import call, Mock, patch, PropertyMock

from business_plans.report import BPChart, BPStatus, Chart, CompareBPsLineChart, \
    Element, LegendPosition, LineBPChart, Report, StackedBarBPChart


def strip_spaces(html: str) -> str:
    return '\n'.join(line.strip() for line in html.split('\n'))


def check_chart(chart: Chart,  # TODO reintegrate
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


class TestBPChartClass:

    single_bp_chart_html = '''\
new Chart(canvas.getContext('2d'), {
type: 'line',
data: {
labels: ['01/01/2020', '01/01/2021', '01/01/2022', '01/01/2023'],
datasets: [
{ label: 'Line 1',
backgroundColor: '#f67019',
borderColor: '#f67019',
fill: false,
spanGaps: false,
data: [10.0, 11.0, 12.0, 13.0]
},
{ label: 'Line 2',
backgroundColor: '#4dc9f6',
borderColor: '#4dc9f6',
fill: false,
spanGaps: false,
data: [20.0, 21.0, 22.0, 23.0]
},
{ label: 'Line 3',
backgroundColor: '#537bc4',
borderColor: '#537bc4',
fill: false,
spanGaps: false,
data: [30.0, 31.0, 32.0, 33.0]
}'''

    multi_bp_chart_html = '''\
new Chart(canvas.getContext('2d'), {
type: 'line',
data: {
labels: ['01/01/2020', '01/01/2021', '01/01/2022', '01/01/2023'],
datasets: [
{ label: 'BP1',
backgroundColor: '#f67019',
borderColor: '#f67019',
fill: false,
spanGaps: false,
data: [10.0, 11.0, 12.0, 13.0]
},
{ label: 'BP2',
backgroundColor: '#4dc9f6',
borderColor: '#4dc9f6',
fill: false,
spanGaps: false,
data: [15.0, 16.0, 17.0, 18.0]
},
{ label: 'BP3',
backgroundColor: '#537bc4',
borderColor: '#537bc4',
fill: false,
spanGaps: false,
data: [17.0, 18.0, 19.0, 20.0]
}'''

    single_bp_table_html = '''\
<table>

<thead>
<tr>
<th></th>
<th>01/01/2020</th>
<th>01/01/2021</th>
<th>01/01/2022</th>
<th>01/01/2023</th>
</tr>
</thead>
<tbody>
<tr>
<th>Line 3</th>
<td>&#x2007;30&#x2007;</td>
<td>&#x2007;31&#x2007;</td>
<td>&#x2007;32&#x2007;</td>
<td>&#x2007;33&#x2007;</td>
</tr>
<tr>
<th>Line 2</th>
<td>&#x2007;20&#x2007;</td>
<td>&#x2007;21&#x2007;</td>
<td>&#x2007;22&#x2007;</td>
<td>&#x2007;23&#x2007;</td>
</tr>
<tr>
<th>Line 1</th>
<td>&#x2007;10&#x2007;</td>
<td>&#x2007;11&#x2007;</td>
<td>&#x2007;12&#x2007;</td>
<td>&#x2007;13&#x2007;</td>
</tr>
</tbody>
</table>'''

    multi_bp_table_html = '''\
<table>

<thead>
<tr>
<th></th>
<th>01/01/2020</th>
<th>01/01/2021</th>
<th>01/01/2022</th>
<th>01/01/2023</th>
</tr>
</thead>
<tbody>
<tr>
<th>BP3</th>
<td>&#x2007;17&#x2007;</td>
<td>&#x2007;18&#x2007;</td>
<td>&#x2007;19&#x2007;</td>
<td>&#x2007;20&#x2007;</td>
</tr>
<tr>
<th>BP2</th>
<td>&#x2007;15&#x2007;</td>
<td>&#x2007;16&#x2007;</td>
<td>&#x2007;17&#x2007;</td>
<td>&#x2007;18&#x2007;</td>
</tr>
<tr>
<th>BP1</th>
<td>&#x2007;10&#x2007;</td>
<td>&#x2007;11&#x2007;</td>
<td>&#x2007;12&#x2007;</td>
<td>&#x2007;13&#x2007;</td>
</tr>
</tbody>
</table>'''

    @pytest.fixture()
    def bps(self) -> List[pd.DataFrame]:

        def year_to_datetime(year: int) -> datetime:
            return datetime(year, 1, 1)

        index = [2020, 2021, 2022, 2023]
        bp1 = pd.DataFrame(index=index)
        bp1.bp.name = "BP1"
        bp1.bp.index_to_datetime = year_to_datetime
        bp1['Line 1'] = [10., 11., 12., 13.]
        bp1['Line 2'] = [20., 21., 22., 23.]
        bp1['Line 3'] = [30., 31., 32., 33.]
        bp2 = pd.DataFrame(index=index)
        bp2.bp.name = "BP2"
        bp2.bp.index_to_datetime = year_to_datetime
        bp2['Line 1'] = [15, 16, 17, 18]
        bp2['Line 2'] = [25, 26, 27, 28]
        bp3 = pd.DataFrame(index=index)
        bp3.bp.name = "BP3"
        bp3.bp.index_to_datetime = year_to_datetime
        bp3['Line 1'] = [17, 18, 19, 20]
        bp3['Line 2'] = [27, 28, 29, 20]
        return [bp1, bp2, bp3]

    @pytest.mark.parametrize('line_arg, display_chart, display_table', [
        (['Line 1', 'Line 2', 'Line 3'], True, True),
        (['Line 1', 'Line 2', 'Line 3'], False, True),
        (['Line 1', 'Line 2', 'Line 3'], True, False),
        ('Line 1', True, True),
        ('Line 1', False, True),
        ('Line 1', True, False)
    ])
    def test_bp_arg_line_arg_display_args(self,
                                          line_arg: Union[str, List[str]],
                                          display_chart: bool,
                                          display_table: bool,
                                          bps: List[pd.DataFrame]) -> None:
        if isinstance(line_arg, str):
            bp_arg = bps
            chart_html = TestBPChartClass.multi_bp_chart_html
            table_html = TestBPChartClass.multi_bp_table_html
        else:
            bp_arg = bps[0]
            chart_html = TestBPChartClass.single_bp_chart_html
            table_html = TestBPChartClass.single_bp_table_html
        html = strip_spaces(BPChart(bp_arg=bp_arg,
                                    line_arg=line_arg,
                                    display_chart=display_chart,
                                    display_table=display_table).html)
        if display_chart:
            assert chart_html in html
        else:
            assert chart_html not in html
        if display_table:
            assert table_html in html
        else:
            assert table_html not in html
