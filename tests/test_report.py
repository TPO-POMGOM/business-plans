""" Test module business_plans.bp

**Revision history**

- 16-Nov-2020 TPO -- Created this module.

- XX-Nov-2020 TPO -- Initial release. """

from datetime import date, datetime
from typing import List, Union

import pandas as pd
import pytest
from typing_extensions import Literal
from unittest.mock import patch

from business_plans.bp import ExternalAssumption, Formatter, \
    HistoryBasedAssumption, UpdateLink
from business_plans.report import BPChart, BPStatus, Chart, CHART_COLORS, \
    CompareBPsLineChart, Element, LegendPosition, LineBPChart, Report, \
    StackedBarBPChart


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


@pytest.fixture()
def bps() -> List[pd.DataFrame]:

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


class TestElementClass:

    def test_constructor(self) -> None:
        assert Element("Some HTML").html == "Some HTML"  # <===


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
        check_chart(Chart(datasets='some datasets',  # <===
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
<table class="chart">

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
<table class="chart">

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

    @pytest.mark.parametrize('line_arg, display_chart, display_table', [
        (['Line 1', 'Line 2', 'Line 3'], True, True),
        (['Line 1', 'Line 2', 'Line 3'], False, True),
        (['Line 1', 'Line 2', 'Line 3'], True, False),
        ('Line 1', True, True),
        ('Line 1', False, True),
        ('Line 1', True, False)
    ])
    def test_bp_arg_line_arg_display_arguments(
            self,
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
        html = strip_spaces(BPChart(bp_arg=bp_arg,  # <===
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

    @pytest.mark.parametrize('chart_type, x_label, y_label', [
        ('line', "", ""),
        ('stacked bar', "", ""),
        ('line', "X label", ""),
        ('line', "", "Y label")
    ])
    def test_chart_type_x_label_y_label_arguments(
            self,
            chart_type: Literal['line', 'stacked bar'],
            x_label: str,
            y_label: str,
            bps: List[pd.DataFrame]) -> None:
        html = strip_spaces(BPChart(bp_arg=bps[0],  # <===
                                    line_arg=['Line 1', 'Line 2', 'Line 3'],
                                    chart_type=chart_type,
                                    x_label=x_label,
                                    y_label=y_label).html)
        stacked = 'true' if chart_type == 'stacked bar' else 'false'
        assert (f"""\
scales: {{
xAxes: [{{
stacked: {stacked},
scaleLabel: {{
display: {'true' if x_label else 'false'},
labelString: '{x_label}' }}
}}],
yAxes: [{{
stacked: {stacked},
scaleLabel: {{
display: {'true' if y_label else 'false'},
labelString: '{y_label}' }}
}}]
}}""" in html)

    @pytest.mark.parametrize('index_format, labels', [
        (None, "['01/01/2020', '01/01/2021', '01/01/2022', '01/01/2023']"),
        ('%Y', "['2020', '2021', '2022', '2023']"),
        (lambda dt: dt.strftime('%Y/%m/%d'),
         "['2020/01/01', '2021/01/01', '2022/01/01', '2023/01/01']")
    ])
    def test_index_format_argument(
            self,
            index_format: Formatter,
            labels: str,
            bps: List[pd.DataFrame]) -> None:
        html = strip_spaces(BPChart(bp_arg=bps[0],  # <===
                                    line_arg=['Line 1', 'Line 2', 'Line 3'],
                                    index_format=index_format).html)
        assert f'data: {{\nlabels: {labels}' in html

    @pytest.mark.parametrize('scale, precision, data', [
        (1.0, 0, '[10.0, 11.0, 12.0, 13.0]'),
        (.1, 1, '[1.0, 1.1, 1.2, 1.3]'),
        (.1, 0, '[1.0, 1.0, 1.0, 1.0]'),
    ])
    def test_scale_precision_arguments(
            self,
            scale: float,
            precision: int,
            data: str,
            bps: List[pd.DataFrame]) -> None:
        html = strip_spaces(BPChart(bp_arg=bps[0],  # <===
                                    line_arg=['Line 1', 'Line 2', 'Line 3'],
                                    scale=scale,
                                    precision=precision).html)
        assert data in html

    def test_fmt_argument(self, bps: List[pd.DataFrame]) -> None:
        html = strip_spaces(BPChart(bp_arg=bps[0],  # <===
                                    line_arg=['Line 1'],
                                    fmt='{:.2f}').html)
        assert '''\
<tr>
<th>Line 1</th>
<td>&#x2007;10.00&#x2007;</td>
<td>&#x2007;11.00&#x2007;</td>
<td>&#x2007;12.00&#x2007;</td>
<td>&#x2007;13.00&#x2007;</td>
</tr>''' in html

    def test_table_legend_argument(self, bps: List[pd.DataFrame]) -> None:
        html = strip_spaces(BPChart(bp_arg=bps[0],  # <===
                                    line_arg=['Line 1'],
                                    table_legend="Some legend").html)
        assert '<caption>Some legend</caption>' in html

    def test_display_chart_false_and_display_table_false_raise_error(
            self, bps: List[pd.DataFrame]) -> None:
        with pytest.raises(ValueError):
            BPChart(bp_arg=bps[0],  # <===
                    line_arg=['Line 1'],
                    display_chart=False,
                    display_table=False)

    def test_unnamed_bps_raise_error(self, bps: List[pd.DataFrame]) -> None:
        bps[0].bp.name = ""
        with pytest.raises(ValueError):
            BPChart(bp_arg=bps, line_arg='Line 1')  # <===


class TestStackedBarBPChartClass:

    def test_constructor(self, bps: List[pd.DataFrame]) -> None:
        bp = bps[0]
        lines = ['Line 1']
        kwargs = {'title': 'Some title', 'legend_position': 'bottom'}
        with patch('business_plans.report.BPChart.__init__',
                   autospec=True) as bpchart_init:
            chart = StackedBarBPChart(bp, lines, **kwargs)  # <===
            bpchart_init.assert_called_with(chart, bp, lines,
                                            chart_type='stacked bar', **kwargs)


class TestLineBPChartClass:

    def test_constructor(self, bps: List[pd.DataFrame]) -> None:
        bp = bps[0]
        lines = ['Line 1']
        kwargs = {'title': 'Some title', 'legend_position': 'bottom'}
        with patch('business_plans.report.BPChart.__init__',
                   autospec=True) as bpchart_init:
            chart = LineBPChart(bp, lines, **kwargs)  # <===
            bpchart_init.assert_called_with(chart, bp, lines,
                                            chart_type='line', **kwargs)


class TestCompareBPsLineChartClass:

    def test_constructor(self, bps: List[pd.DataFrame]) -> None:
        line = 'Line 1'
        kwargs = {'title': 'Some title', 'legend_position': 'bottom'}
        with patch('business_plans.report.BPChart.__init__',
                   autospec=True) as bpchart_init:
            chart = CompareBPsLineChart(bps, line, **kwargs)  # <===
            bpchart_init.assert_called_with(chart, bps, line,
                                            chart_type='line', **kwargs)


class TestBPStatusClass:

    @pytest.mark.parametrize('language', [('English'), ('Français')])
    def test_external_assumptions(
            self, language: str, bps: List[pd.DataFrame]) -> None:
        bp = bps[0]
        assumption = ExternalAssumption(
            "Some assumption",
            last_update=date(2020, 1, 1),  # Ignored, see (*) below
            update_every_x_year=1,         # Ignored, see (*) below
            update_instructions="See {link}",
            update_links={'link': UpdateLink(title="Link title",
                                             url='http://some_url')})
        bp.bp.assumptions.append(assumption)

        assumption.update_required = True  # (*)
        html = strip_spaces(BPStatus(bp,  # <===
                                     language=language).html)  # type: ignore
        assert (
            BPStatus.messages['Assumption needs update'][language].format(
                name="Some assumption", day=1, month=1, year=2020)
            + 'See <a href="http://some_url" target="_blank">Link title</a>') in html

        assumption.update_required = False  # (*)
        html = strip_spaces(BPStatus(bp,  # <===
                                     language=language).html)  # type: ignore
        assert "Some assumption" not in html

    @pytest.mark.parametrize('language', [('English'), ('Français')])
    def test_history_based_assumptions(
            self, language: str, bps: List[pd.DataFrame]) -> None:
        bp = bps[0]
        assumption = HistoryBasedAssumption(
            "Some assumption",
            value=5.3,
            history=[1.1, 2.2, 3.3],
            start=2020,
            last_update=date(2020, 1, 1),  # Ignored, see (*) below
            update_every_x_year=1)         # Ignored, see (*) below
        bp.bp.assumptions.append(assumption)

        assumption.update_required = True  # (*)
        html = strip_spaces(BPStatus(bp,  # <===
                                     language=language).html)  # type: ignore
        assert (
            BPStatus.messages['H-assumption needs update'][language].format(
                name="Some assumption", day=1, month=1, year=2020)) in html
        assert f'''\
datasets: [
{{ label: '{BPStatus.messages['Assumption'][language]}',
backgroundColor: '{CHART_COLORS[0]}',
borderColor: '{CHART_COLORS[0]}',
fill: false,
spanGaps: false,
data: [5.3, 5.3, 5.3]
}},
{{ label: '{BPStatus.messages['History'][language]}',
backgroundColor: '{CHART_COLORS[1]}',
borderColor: '{CHART_COLORS[1]}',
fill: false,
spanGaps: false,
data: [1.1, 2.2, 3.3]
}},
{{ label: '{BPStatus.messages['Average'][language]}',
backgroundColor: '{CHART_COLORS[2]}',
borderColor: '{CHART_COLORS[2]}',
fill: false,
spanGaps: false,
data: [2.2, 2.2, 2.2]
}},

]''' in html

        assumption.update_required = False  # (*)
        html = strip_spaces(BPStatus(bp,  # <===
                                     language=language).html)  # type: ignore
        assert "Some assumption" not in html
