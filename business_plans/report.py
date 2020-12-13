""" Represent reports on a business plan, made up of charts and tables.

**Revision history**

- 22-Jun-2019 TPO -- Created this module.

- 13-Jul-2019 TPO -- Initial release.

- 24-Jul-2019 TPO -- Added BPStatus.

- 27-Sep-2020 TPO -- Created v0.2, replacing class ``BP`` with ``pandas.DataFrame``
  and class ``BPTimeSeries`` with ``pandas.Series``.

- 21-Oct-2020 TPO -- Initial release of v0.2.

- 4-Nov-2020 TPO - Created v0.3: generalize bp index to any strictly increasing
  sequence.

- 13-Nov-2020 TPO -- Initial release of v0.3. """


from __future__ import annotations
from datetime import datetime
import html
from pathlib import Path
from typing import List, Union

import pandas as pd
from typing_extensions import Literal

from business_plans.bp import ExternalAssumption, Formatter, HistoryBasedAssumption


__all__ = [
    'BPChart',
    'BPStatus',
    'Chart',
    'CHART_COLORS',
    'CompareBPsLineChart',
    'Element',
    'LineBPChart',
    'Report',
    'StackedBarBPChart',
]


CHART_COLORS = [
    '#f67019',
    '#4dc9f6',
    '#537bc4',
    '#f53794',
    '#acc236',
    '#166a8f',
    '#00a950',
    '#58595b',
    '#8549ba']


class Element:
    """ Represent an element in a Report.

        Arguments
        ---------

        html: `str`
            HTML code for the element."""

    def __init__(self, html: str) -> None:
        self._html = html

    @property
    def html(self) -> str:
        """ HTML code for the element (`str`, get only) """
        return self._html


LegendPosition = Literal['top', 'left', 'bottom', 'right']


class Chart(Element):
    """ Report element displaying a chart.


    Arguments
    ---------

    datasets: `str`
        String representation of the ``datasets:`` part of the JavaScript code
        which  will be passed to the ChartJS ``Chart`` object factory. The
        string will be automatically prefixed with ``datasets: [`` and
        terminated with ``]`` before calling the ``Chart`` object factory.

    title: `str`, defaults to ``""``
        Title which will be displayed at the top of the chart, as an HTML
        ``<h2>`` element.

    chart_type: `str`, defaults to ``'line'``
        Chart type which will be passed to the ``Chart`` object factory. See
        ChartJS documentation.

    labels: `str`, defaults to ``""``
        String representation of the labels to be displayed on the x-axis. It
        should start with ``[``, end with ``]``, and individual labels should
        be separated by commas.

    width: `str`, defaults to ``''``
        String representation of the width attribute for the HTML ``<canvas>``
        element on which the chart is drawn. If set to ``""``:

        - If `height` is set, the same value is used for `width`.

        - Otherwise, `width` is managed automatically by ChartJS, to
          generate a responsive display.

    height: `str`, defaults to ``''``
        String representation of the height attribute for the HTML ``<canvas>``
        element on which the chart is drawn. If set to ``""``:

        - If `width` is set, the same value is used for `height`.

        - Otherwise, `height` is managed automatically by ChartJS, to generate
          a responsive display.

    legend_position: `str`, defaults to ``'right'``
        Position of the legend relative to the chart. Can be either ``'top'``,
        ``'left'``, ``'bottom'`` or ``'right'``.

    legend_reverse: `bool`, defaults to ``False``
        If true, the legend will show the datasets in reverse order.

    options: `str`, defaults to ``''``
        String representation of the ``options:`` part of the JavaScript code
        which will be passed to the ChartJS ``Chart`` object factory. The
        string will be automatically prefixed with ``options: {`` and
        terminated with ``}`` before calling the ``Chart`` object factory. """

    _current_index = 0

    def __init__(self,
                 datasets: str,
                 title: str = "",
                 chart_type: str = 'line',
                 labels: str = "",
                 width: str = '',
                 height: str = '',
                 legend_position: LegendPosition = 'right',
                 legend_reverse: bool = False,
                 options: str = '') -> None:
        if not width and not height:
            dimension_options = ""
        else:
            height = height or width
            width = width or height
            width = "width=" + width
            height = "height=" + height
            dimension_options = ("""\
                responsive: false,
                maintainAspectRatio: false,""")
        super().__init__(f"""\
    <h2>{html.escape(title)}</h2>
    <canvas id="chart-{Chart._current_index}" {width} {height}></canvas>
    <script type="text/javascript">
        canvas = document.getElementById('chart-{Chart._current_index}')
        new Chart(canvas.getContext('2d'), {{
            {f"type: '{chart_type}'," if chart_type else ""}
            data: {{
                {f"labels: {labels}," if labels else ""}
                datasets: [
{datasets}
                ]
            }},
            options: {{
                legend: {{
                    position: '{legend_position}',
                    reverse: {"true" if legend_reverse else "false"},
                }},
{dimension_options}
{options}
            }}
        }});
    </script>
""")
        Chart._current_index += 1


class BPChart(Element):
    """ Report element displaying business plan data as a chart and a data table.

    A :class:`BPChart` is composed of the following visual elements:

    - A title.

    - The chart itself, which displays either a line representation or a
      stacked bar representation of the business plan data.

    - Labels for the X and Y axes.

    - The data table. History values are displayed on a grey background.

    - A legend for the table.


    Arguments
    ---------

    bp_arg: ``Union[pandas.DataFrame, List[pandas.DataFrame]]``
      - When `bp_arg` receives a ``pandas.DataFrame``, `line_arg` should
        receive a list of strings naming business plan lines in the
        ``pandas.DataFrame``. The chart will plot each of these business plan
        lines. Note that no  point is plotted for index values which are not
        defined on a given business plan line.

      - When `bp_arg` receives a ``List[pandas.DataFrame]``, `line_arg` should
        receive a string naming a business plan line which is common to all the
        ``pandas.DataFrame``'s. The chart will plot this line for each of the
        business plans / ``pandas.DataFrame``'s. Note that no point is plotted
        for index values which are not defined on a given business plan line.

    line_arg: `Union[str, List[str]]`
        See `bp_arg` above.

    chart_type: `str`, defaults to ``'line'``
        Type of the chart to be displayed. Can be either ``'line'`` or
        ``'stacked bar'``.

    title: `str`, defaults to ``""``
        Title which will be displayed at the top of the chart, as an HTML
        ``<h2>`` element.

    index_format: :data:`~business_plans.bp.Formatter`, defaults to ``None``
        Define how index values are formatted. Index value `index`, associated
        to business plan `bp`, will be formatted as follows, depending on the
        type of `index_format`:

        - ``None``: format value as ``index.strftime(bp.bp.index_format)``

        - ``str``: format value as  ``index.strftime(index_format)``

        - ``Callable[[datetime], str]``: format value as ``index_format(index)``

    scale: `float`, defaults to ``1.0``
        Factor by which individual values are multiplied before being plotted
        on the chart and displayed in the table.

    precision: `int`, defaults to ``0``
        Number of digits to which individual values are rounded (after applying
        the scale factor) before being plotted on the chart and displayed in
        the table.

    fmt: `str`, defaults to ``'{:,.0f}'`` i.e. round values to 0 decimal places
        Format string used for displaying values in the table, after `scale`
        and `precision` have been applied.

    width: `str`, defaults to ``""``
        String representation of the width attribute for the HTML
        ``<canvas>`` element on which the chart is drawn. If set to ``""``:

        - If `height` is set, the same value is used for `width`.

        - Otherwise, `width` is managed automatically by ChartJS, to
          generate a responsive display.

    height: `str`, defaults to ``""``
        String representation of the height attribute for the HTML
        ``<canvas>`` element on which the chart is drawn. If set to ``""``:

        - If `width` is set, the same value is used for `height`.

        - Otherwise, `height` is managed automatically by ChartJS, to
          generate a responsive display.

    legend_position: `str`, defaults to ``'right'``
        Position of the legend relative to the chart. Can be either
        ``'top'``, ``'left'``, ``'bottom'`` or ``'right'``.

    legend_reverse: `bool`, defaults to ``False``
        If true, the legend will show the datasets in reverse order.

    x_label: `str`, defaults to ``""``
        Legend for the X axis.

    y_label: `str`, defaults to ``""``
        Legend for the Y axis.

    display_chart: `bool`, defaults to ``True``
        Indicates if the chart part of the element should be displayed or not.

    display_table: `bool`, defaults to ``True``
        Indicates if the table part of the element and its legend should be
        displayed or not.

    table_legend: `str`, defaults to ``""``
        Legend for the table, which is displayed right below the table. """

    def __init__(self,
                 bp_arg: Union[pd.DataFrame, List[pd.DataFrame]],
                 line_arg: Union[str, List[str]],
                 chart_type: Literal['line', 'stacked bar'] = 'line',
                 title: str = "",
                 index_format: Formatter = None,
                 scale: float = 1.0,
                 precision: int = 0,
                 fmt: str = '{:,.0f}',
                 width: str = "",
                 height: str = "",
                 legend_position: LegendPosition = 'right',
                 legend_reverse: bool = False,
                 x_label: str = "",
                 y_label: str = "",
                 display_chart: bool = True,
                 display_table: bool = True,
                 table_legend: str = "") -> None:

        def dataset_js(i: int, line: str) -> str:
            # nonlocal chart_type, data
            return ("""\
                    {{ label: '{title}',
                      backgroundColor: '{color}',
                      borderColor: '{color}',
                      fill: {fill},
                      spanGaps: false,
                      data: [{data}]
                    }}"""
                    .format(title=line,
                            color=CHART_COLORS[i % len(CHART_COLORS)],
                            fill='true' if chart_type != 'line' else 'false',
                            data=", ".join(str(d) for d in data[line])))

        if not display_chart and not display_table:
            raise ValueError("At least one of 'display_chart' and "
                             "'display_table' must be true")
        if isinstance(bp_arg, pd.DataFrame) and isinstance(line_arg, list):
            _bp = bp_arg
            _lines = line_arg
            bp_index = _bp.index
            data = {line: (_bp[line] * scale).round(precision) for line in _lines}
            datasets = [dataset_js(i, line) for i, line in enumerate(_lines)]
            chart_lines = [(_bp, line, _bp[line]) for line in reversed(_lines)]
        elif isinstance(bp_arg, list) and isinstance(line_arg, str):
            if not all(bp.bp.name for bp in bp_arg):
                raise ValueError("All business plans must have a bp.name set")
            _bps = bp_arg
            _line = line_arg
            _bp = _bps[0]
            bp_index = _bp.index
            data = {bp.bp.name: (bp[_line] * scale).round(precision) for bp in _bps}
            datasets = [dataset_js(i, bp.bp.name) for i, bp in enumerate(_bps)]
            chart_lines = [(bp, bp.bp.name, bp[_line]) for bp in reversed(_bps)]
        else:
            raise TypeError("Invalid types for 'bp_arg' and 'line_arg'")
        labels = [_bp.bp.index_to_str(index, index_format) for index in bp_index]
        stacked = 'true' if chart_type == 'stacked bar' else 'false'
        chart = Chart(datasets=",\n".join(datasets),
                      title=title,
                      chart_type='line' if chart_type == 'line' else 'bar',
                      labels=str(labels),
                      width=width,
                      height=height,
                      legend_position=legend_position,
                      legend_reverse=legend_reverse,
                      options=f"""\
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
                }}""").html if display_chart else ''

        table = []
        if display_table:
            if not display_chart:
                table.append(f"    <h2>{html.escape(title)}</h2>")
            caption = (f'    <caption>{html.escape(table_legend)}</caption>'
                       if table_legend else '')
            table.append(f"""\
    <table class="chart">
{caption}
        <thead>
            <tr>
                <th>{html.escape(x_label)}</th>""")
            for label in labels:
                table.append(f"                <th>{label}</th>")
            table.append("""\
            </tr>
        </thead>
        <tbody>""")
            for bp, line, bp_line in chart_lines:
                table.append(f"""\
            <tr>
                <th>{line}</th>""")
                history_size = bp.bp.history_size(line)
                sp = '&#x2007;'  # Unicode 'FIGURE SPACE', same width as digits.
                for i, d in enumerate(bp_line):
                    cls = ' class="history"' if i < history_size else ''
                    value = fmt.format(d) if type(d) in (int, float) else ''
                    table.append(f"                <td{cls}>{sp}{value}{sp}</td>")
                table.append("            </tr>")
            table.append("""\
        </tbody>
    </table>

""")
        super().__init__(html=chart + '\n'.join(table))


class StackedBarBPChart(BPChart):
    """ Report element displaying lines from a BP as a stacked bar chart + data table.

    .. code-block:: python

        StackedBarBPChart(bp, lines, **kwargs)

    is shorthand for:

    .. code-block:: python

        BPChart(bp, lines, chart_type='stacked bar', **kwargs)

    See :class:`BPChart` for more information. """

    def __init__(self, bp: pd.DataFrame, lines: List[str], **kwargs):
        super().__init__(bp, lines, chart_type='stacked bar', **kwargs)


class LineBPChart(BPChart):
    """ Report element displaying lines from a BP as a line chart + data table.

    .. code-block:: python

        LineBPChart(bp, lines, **kwargs)

    is shorthand for:

    .. code-block:: python

        BPChart(bp, lines, chart_type='line', **kwargs)

    See :class:`BPChart` for more information. """

    def __init__(self, bp: pd.DataFrame, lines: List[str], **kwargs):
        super().__init__(bp, lines, chart_type='line', **kwargs)


class CompareBPsLineChart(BPChart):
    """ Report element displaying one line in several BPs as a line chart + data table.

    .. code-block:: python

        CompareBPsLineChart(bps, line, **kwargs)

    is shorthand for:

    .. code-block:: python

        BPChart(bps, line, chart_type='line', **kwargs)

    See :class:`BPChart` for more information. """

    def __init__(self, bps: List[pd.DataFrame], line: str, **kwargs):
        super().__init__(bps, line, chart_type='line', **kwargs)


Languages = Literal['English', 'Français']


class BPStatus(Element):
    """ Report element displaying status information on business plan assumptions.

    The element lists all assumptions which need to be updated. Three
    categories of assumptions are taken into account:

    - Assumptions based on external data. They are declared thus::

        bp.bp.assumptions.append(ExternalAssumption(
            name="Some assumption",
            last_update=datetime.date(2015, 2, 1),
            update_every_x_year=3,
            update_instructions="Bla bla bla"))

      Such assumptions become out of date when the `last_update` argument to
      :class:`~bp.ExternalAssumption` lags the current date by more years than
      indicated by the `update_every_x_year` argument.

    - Assumptions based on the historical data for a BP line. They are declared
      thus::

        bp.bp.assumptions.append(HistoryBasedAssumption(
            name="Some assumption",
            value=2.0,
            history=[1.0, 2.0, 3.0, 4.0, 5.0],
            start=2010,
            last_update=datetime.date(2015, 2, 1),
            update_every_x_year=3))

      Such assumptions become out of date when the `last_update` argument to
      :class:`~bp.HistoryBasedAssumption` lags the current date by more years
      than indicated by the `update_every_x_year` argument.

    - Business plan line historical data, which is declared thus::

        bp.bp.line(name="BP line",
                   history=[1.0, 2.0, 3.0, 4.0, 5.0],
                   max_history_lag=2)

      The assumption is reported as missing historical data when the last index
      for which history is available lags behind the current year for more
      years than indicated by the `max_history_lag` argument.


    Arguments
    ---------

    bp: `pd.DataFrame`
        Business plan for which a status report will be generated.

    title: `str`, defaults to ``""``
        Title which will be displayed at the top of the status report, as an
        HTML ``<h2>`` element.

    index_format: :data:`~business_plans.bp.Formatter`, defaults to ``None``
        Define how index values are formatted. Index value `index`, associated
        to business plan `bp`, will be formatted as follows, depending on the
        type of `index_format`:

        - ``None``: format value as ``index.strftime(bp.bp.index_format)``

        - ``str``: format value as  ``index.strftime(index_format)``

        - ``Callable[[datetime], str]``: format value as ``index_format(index)``

    language: `str`, defaults to ``'English'``
        Language for the report. Can be either ``'English'`` or ``'Français'``. """

    messages = {
        'Up to date': {
            'English': "All assumptions are up to date.",
            'Français': "Toutes les hypothèses sont à jour."
        },
        'Out of date': {
            'English': "The following assumptions are out of date:",
            'Français': "Les hypothèses suivantes ne sont plus à jour :"
        },
        'Assumption needs update': {
            'English': "<b>{name}</b>: last updated on {day}/{month}/{year}. ",
            'Français': "<b>{name}</b> : la dernière mise à jour date du "
                         "{day}/{month}/{year}. "
        },
        'H-assumption needs update': {
            'English': "<b>{name}</b>: last updated on {day}/{month}/{year}. "
                       "Use the chart below to compare the current assumption "
                       "value with history, and update assumption value.\n",
            'Français': "<b>{name}</b> : la dernière mise à jour date du "
                         "{day}/{month}/{year}. "
                         "Utilisez le graphique ci-dessous pour comparer la "
                         "valeur de l'hypothèse avec l'historique, puis mettez "
                         "à jour l'hypothèse.\n"
        },
        'Missing history': {
            'English': "<b>{name}</b>: history is available until {most_recent} "
                       "and is missing until {required}.",
            'Français': "<b>{name}</b> : l'historique va jusqu'à {most_recent} "
                         "et manque ensuite jusqu'à {required}."
        },
        'Assumption': {
            'English': "Assumption",
            'Français': "Hypothèse"
        },
        'History': {
            'English': "History",
            'Français': "Historique"
        },
        'Average': {
            'English': "History average",
            'Français': "Moyenne de l\\'historique"
        },
    }

    def __init__(self,
                 bp: pd.DataFrame,
                 title: str = "",
                 index_format: Formatter = None,
                 language: Languages = 'English') -> None:

        def to_html_ul(strings: List[str]) -> str:
            """ Convert a list of strings to an HTML <UL> list. """
            return ("""    <ul class="BPStatus">\n"""
                    + "".join(f"        <li>{s}</li>\n" for s in strings)
                    + "    </ul>\n")

        def dataset_js(title: str, color: int, data: List[float]) -> str:
            """ Convert a list of floats to JS code for a chartjs dataset. """
            return ("""\
                    {{ label: '{title}',
                      backgroundColor: '{color}',
                      borderColor: '{color}',
                      fill: false,
                      spanGaps: false,
                      data: [{data}]
                    }},\n"""
                    .format(title=title,
                            color=CHART_COLORS[color % len(CHART_COLORS)],
                            data=", ".join(str(d) for d in data)))

        bp_status: List[str] = []
        messages = BPStatus.messages
        for assumption in bp.bp.assumptions:
            if (isinstance(assumption, ExternalAssumption)
                    and assumption.update_required):
                update_instructions = assumption.update_instructions.format(**{
                    key: (f'<a href="{html.escape(link.url)}" target="_blank">'
                          f'{html.escape(link.title)}</a>')
                    for key, link in assumption.update_links.items()})
                bp_status.append(
                    messages['Assumption needs update'][language].format(
                        name=assumption.name,
                        day=assumption.last_update.day,
                        month=assumption.last_update.month,
                        year=assumption.last_update.year)
                    + update_instructions)
            if (isinstance(assumption, HistoryBasedAssumption)
                    and assumption.update_required):

                def _round(x: float) -> float:
                    return round(x, ndigits=assumption.ndigits)

                n = len(assumption.history)
                start_pos = bp.index.get_loc(assumption.start)
                chart = Chart(
                    datasets=(
                        dataset_js(
                            messages['Assumption'][language],
                            color=0,
                            data=[_round(assumption.value)] * n)
                        + dataset_js(
                            messages['History'][language],
                            color=1,
                            data=[_round(x) for x in assumption.history])
                        + dataset_js(
                            messages['Average'][language],
                            color=2,
                            data=[_round(sum(assumption.history) / n)] * n)),
                    labels=str([bp.bp.index_to_str(index, index_format)
                                for index in bp.index[start_pos: start_pos + n]]),
                    options=f"""\
                scales: {{
                    yAxes: [{{
                        scaleLabel: {{
                            display: true,
                            labelString: '{assumption.y_scale}'
                        }}
                    }}]
                }}""",
                    width="800px",
                    height="150px").html
                bp_status.append(
                    messages['H-assumption needs update'][language].format(
                        name=assumption.name,
                        day=assumption.last_update.day,
                        month=assumption.last_update.month,
                        year=assumption.last_update.year)
                    + chart)
        for name in bp:
            history_size = bp.bp.history_size(name)
            if history_size:
                most_recent = bp.bp.index_to_datetime(bp.index[history_size - 1])
                required = datetime.today() - bp.bp.max_history_lag(name)
                if most_recent < required:
                    bp_status.append(
                        messages['Missing history'][language]
                        .format(name=name,
                                most_recent=bp.bp.datetime_to_str(most_recent,
                                                                  index_format),
                                required=bp.bp.datetime_to_str(required,
                                                               index_format)))
        summary = 'Out of date' if bp_status else 'Up to date'
        super().__init__(f"""\
    <h2>{title}</h2>
    <p class="BPStatus">{messages[summary][language]}</p>\n"""
                         + (to_html_ul(bp_status) if bp_status else "")
                         + "\n")


class Report:
    """ Represent a complete report on business plan data.


    Arguments
    ---------

    title: `str`, defaults to ``""``
        Title which will be displayed at the top of the report, as an HTML
        ``<h1>`` element, and which will be used as the ``<title>`` for the
        HTML page.

    max_width: `int`, defaults to ``960``
        Maximum width in pixels in which to display the report.

    prologue: `str`, defaults to ``""``
        HTML prologue to be used at the beginning of the report. When the empty
        string is specified, it is replaced by ``Report.PROLOGUE`` (see source
        code for more information).

    chartjs: `str`, defaults to ``""``
        URL for the ChartJS package. When the empty string is specified, it is
        replaced by ``Report.CHARTJS`` (see source code for more information).

    epilogue: `str`, defaults to ``""``
        HTML epilogue to be used at the end of the report. When the empty
        string is specified, it is replaced by ``Report.EPILOGUE`` (see source
        code for more information).

    css: `str`, defaults to ``""``
        CSS definitions to be inserted into the prologue, in an HTML
        ``<style>`` element. When the empty string is specified, it is replaced
        by ``Report.CSS`` (see source code for more information).

    separator: `str`, defaults to ``"    <hr>\\n\\n"``
        HTML code to be inserted between report elements. """

    CHARTJS = "https://cdn.jsdelivr.net/npm/chart.js@2.8.0/dist/Chart.min.js"

    PROLOGUE = """\
<!DOCTYPE html>
<html lang="en-US">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <script src="{chartjs}"></script>
    <style type="text/css">
{css}
    </style>
</head>

<body>
    <div class="content-wrapper">
    <h1>{title}</h1>
"""

    EPILOGUE = """\
    </div>
</body>
</html>
"""

    CSS = """\
        html {{
            font-family: sans-serif;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100% }}

        body {{ margin: 0 }}

        .content-wrapper {{
            max-width: {max_width}px;
            margin: auto; }}

        h1 {{ text-align: center; }}
        h2 {{ text-align: center; }}

        hr {{ margin-top: 40px; }}

        canvas {{ margin: auto; }}
        table.chart {{
            display: table;
            width: {max_width}px;
            overflow: auto;
            border-collapse: collapse;
            border-spacing: 0;
            page-break-inside: avoid;
            margin-top: 20px;
            margin-bottom: .85em; }}
        table.chart tr {{
            background-color: #fff;
            border-top: 1px solid #ccc; }}
        table.chart tr:nth-child(2n) {{ background-color: #f8f8f8; }}
        table.chart td, table.chart th {{
            font-size: 70%;
            padding:6px 0px;
            border:1px solid #ddd; }}
        table.chart th {{
            background-color: #777;
            color: white; }}
        table.chart td {{ text-align: right; }}
        table.chart td.history {{ background-color: #ccc; }}
        table.chart caption {{
            caption-side: bottom;
            padding: 10px;
            font-size: 70%;
            font-style: italic; }}

        ul.BPStatus {{ margin-top: 0; }}
        p.BPStatus {{ margin-bottom: 0; }} """

    def __init__(self,
                 title: str = "",
                 *,
                 max_width: int = 960,
                 prologue: str = "",
                 chartjs: str = "",
                 epilogue: str = "",
                 css: str = "",
                 separator: str = "    <hr>\n\n"):
        self.prologue = (prologue or Report.PROLOGUE).format(
            title=html.escape(title),
            chartjs=chartjs or Report.CHARTJS,
            max_width=max_width,
            css=(css or Report.CSS).format(max_width=max_width))
        self.epilogue = epilogue or Report.EPILOGUE
        self.separator = separator
        self.elements: List[Element] = []

    @property
    def html(self) -> str:
        """ HTML code for the report (`str`, get only)

        This is the code for a complete HTML page, ready to be displayed in a
        web browser."""
        return (self.prologue
                + self.separator
                + self.separator.join(element.html for element in self.elements)
                + self.epilogue)

    def append(self, element: Element) -> Report:
        """ Append an element to a report.


        Arguments
        ---------

        element: :class:`Element`
            The element to be added to the report. This may be an instance of
            any :class:`Element` sub-class, such as :class:`Chart`,
            :class:`BPChart`, :class:`StackedBarBPChart`,
            :class:`LineBPChart`, :class:`CompareBPsLineChart`, and
            :class:`BPStatus`.


        Returns
        -------

        :class:`Report`
            The Report instance itself, so that calls to :func:`append` may be
            chained::

                my_report.append(some_element).append(other_element) """
        self.elements.append(element)
        return self

    def write_to_file(self, filename: str) -> None:
        """ Write the HTML code for the report to a file.

        Arguments
        ---------

        filename: `str`
            Path to the file to be written. If the file already exists, it is
            silently overwritten. """
        Path(filename).write_text(self.html, encoding='utf8')
