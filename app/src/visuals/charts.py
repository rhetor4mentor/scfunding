# charts.py

import altair as alt
import numpy as np
import pandas as pd
from datetime import datetime
from loguru import logger
from typing import List

import warnings
warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", FutureWarning)

from ..loading.loader import TransactionParser
from .. import utils

YEAR_COMPARISON_COLORS = ['#219ebc','#023047']

def generate_tooltip(dataframe: pd.DataFrame) -> List[alt.Tooltip]:
    '''
    Produces a tooltip in correct formatting based on pattern matching of column names
    '''

    columns = dataframe.columns
    formats = {}
    for c in columns:
        if 'pledge' in c:
            formats[c] = '$,.0f'
        elif 'citizens' in c:
            formats[c] = ',.0f'
        elif 'pct' in c:
            formats[c] = '+.1%'
        else:
            formats[c] = None

    tooltips = []
    for c in columns:
        if c.startswith('period'):
            tooltips.append(alt.Tooltip(f"{c}:N", title=utils.format_to_title(c)))

    tooltips.extend(
        alt.Tooltip(column, format=formats[column], title=utils.format_to_title(column)) if formats[column] is not None else alt.Tooltip(column, title=utils.format_to_title(column))
        for column in formats.keys() if not column.startswith('period')
    )

    return tooltips

def plot_line_chart(
        dataframe: pd.DataFrame, 
        index: str = 'datetime_utc', 
        title: str = None,
        first_line_settings: dict = {'x': 'total_pledge', 'type': 'Q', 'format': '$,.0f', 'title': 'Total Pledges ($)'},
        second_line_settings: dict = {'x': 'total_citizens', 'type': 'Q', 'format': ',.0f', 'title': 'Total Citizens'},
        ) -> alt.Chart:
    """
    Produces a line plot for total_citizens and total_pledge using Altair.

    Parameters:
    dataframe (pd.DataFrame): A DataFrame containing 'total_citizens' and 'total_pledge' columns.

    Returns:
    alt.Chart: An Altair chart object.
    """

    if title is None:
        title = 'Avg. spent/account and total funding'

    settings = [first_line_settings, second_line_settings]
    colors = ['#ffb703', '#003049']

    df = dataframe.reset_index()

    tooltips = generate_tooltip(df)
    
    base = alt.Chart(df).encode(x=alt.X(f'{index}:T', title=''), tooltip=tooltips)

    if len([s for s in settings if s is not None]) == 1:
        base = base.interactive()

    hover = alt.selection_point(on='mouseover', nearest=True, empty='none', fields=[index])

    lines_and_points: List[alt.Chart] = []
    legend_data = []

    for i, line_settings in enumerate(settings):
        if line_settings is not None:
            line = base.mark_line().encode(
                y=alt.Y(f"{line_settings['x']}:{line_settings['type']}", 
                        axis=alt.Axis(title=line_settings['title'], format=line_settings['format'])),
                color=alt.value(colors[i])
            )
            lines_and_points.append(line)
            legend_data.append({'label': line_settings['title'], 'color': colors[i]})

            point = base.mark_point().encode(
                y=alt.Y(f"{line_settings['x']}:{line_settings['type']}", title=None, axis=None),
                opacity=alt.condition(hover, alt.value(1), alt.value(0)),
                color=alt.value(colors[i])
            ).add_params(hover)
            lines_and_points.append(point)

    legend_df = pd.DataFrame(legend_data)
    legend_df.loc[:, 'x'] = range(len(legend_df))

    legend = alt.Chart(legend_df).mark_text(
        align='center',
        baseline='middle',
    ).encode(
        x=alt.X('x:O', axis=None, title=''),
        text='label:N',
        color=alt.Color('color:N', scale=None, legend=alt.Legend(title="Legend"))
    ).properties(
        width='container',
        height=25
    )

    chart = alt.layer(*lines_and_points).resolve_scale(
        y='independent',
        x='shared',
    ).properties(
        title=title,
        height=400
    )

    return alt.vconcat(chart, legend)


def plot_all_years(ts_weekly: pd.DataFrame, ts_annual: pd.DataFrame, metric="pledges", show_title: bool = True) -> alt.Chart:
    '''
    Main funding tracker visualisation
    '''

    if metric == "pledges":
        x="pledge"
        x_format = '$,.0f'
    elif metric == "citizens":
        x="citizens"
        x_format = ',.0f'
    else:
        raise ValueError(f"Only values permitted are 'pledges' and 'citizens', not {metric}")

    x_axis = alt.X(f"delta_{x}:Q", title=None, axis=alt.Axis(format=x_format, labelOverlap=True), scale=alt.Scale(domainMin=0))

    tooltips = generate_tooltip(ts_weekly)
    tooltips_a = generate_tooltip(ts_annual)
    
    ts_weekly['quarter_label'] = ts_weekly['quarter'].apply(lambda x: f"Q{x}")
    total = ts_weekly.tail(1)[f'total_{x}'].iloc[0]
    subtitle = (f"{total:,.0f} " if metric != "pledges" else f"${total:,.0f} ") + "historically"


    chart_year = alt.Chart(ts_weekly).mark_bar(color='#526A71').encode(
        x=x_axis,
        y=alt.Y("year:O", title="Year"),
        tooltip=tooltips,
    ).properties(width=200, title="Yearly totals",)

    chart_year_total = alt.Chart(ts_annual).mark_bar().encode(
        x=x_axis,
        color=alt.Color('year:N', legend=None).scale(scheme="category20c"),
        tooltip=tooltips_a,
    ).properties(width=200)

    chart_quarters = alt.Chart(ts_weekly).mark_bar().encode(
        x=x_axis,
        y=alt.Y("year:O", title="Year"),
        color=alt.Color("month:N"),
        tooltip=tooltips,
        column=alt.Column("quarter_label:O", title=None, spacing=50),
    ).properties(width=120, title="Breakdown by quarter")

    chart_quarters_totals = alt.Chart(ts_weekly).mark_bar().encode(
        x=x_axis,
        color=alt.Color("month:N"),
        tooltip=tooltips,
        column=alt.Column("quarter_label:O", title=None, spacing=50),
    ).properties(width=120,)

    chart = ((chart_year & chart_year_total) | ( chart_quarters & chart_quarters_totals )).resolve_scale(color="independent")

    if show_title:
        chart = chart.properties(
            title={
                'text': f"{metric.capitalize()} growth",
                'subtitle': subtitle,
            }
        )

    return chart


def plot_transactions_years_to_date(
        ts: pd.DataFrame, 
        metric="pledges",
        date: pd.Timestamp = None,
        ) -> alt.Chart:
    '''
    Every year of funding, up to current day of year.
    '''

    freq = pd.infer_freq(ts.index)

    if date is None:
        date = pd.to_datetime(max(ts.index.values))

    if freq == 'D':
        time_metric = 'day_of_year'
    elif freq.startswith('W'):
        time_metric = 'week_of_year'
    else:
        logger.error("time series should be at daily or weekly level")
        return


    if metric == "pledges":
        x = "total_pledge_in_year"
        text_format = '$,.0f'
    elif metric == "citizens":
        x = "total_citizens_in_year"
        text_format = '+,.0f'
    else:
        raise ValueError(f"Only values permitted are 'pledges' and 'citizens', not {metric}")

    x_axis = alt.X(
        f"{x}:Q",
        title="",
        axis=alt.Axis(
            labelOverlap=True,
            labelExpr="'$' + format(datum.value / 1000, ',.0f') + 'K'" if metric == "pledges" else "format(datum.value / 1000, ',.0f') + 'K'"
        ),
        scale=alt.Scale(domainMin=0)
    )

    # x_axis = alt.X(f"{x}:Q", title="", axis=alt.Axis(labelOverlap=True, labelExpr=f"'{x_format}'" ,), scale=alt.Scale(domainMin=0))
    year_filter = ts.loc[date][time_metric]
    latest_value = ts.loc[date, x]
    df = ts.query(f"{time_metric}=={year_filter}").copy()

    df['quarter_label'] = df['quarter'].apply(lambda x: f"Q{x}")
    df['rank'] = df[x].rank(ascending=False, method='dense')
    df['is_current'] = df['year'] == date.year
    pct_metric = f"how {date.year} compares (pct)"
    df[pct_metric] = np.where(latest_value != 0, (latest_value - df[x]) / latest_value, np.nan)

    tooltips = generate_tooltip(df[['period', x, 'year', 'rank', pct_metric]])

    bars = alt.Chart(df).mark_bar().encode(
        x=x_axis,
        y=alt.Y("year:O", title="Year", sort='-y'),
        color=alt.Color("is_current:O", scale=alt.Scale(range=YEAR_COMPARISON_COLORS), title='', legend=None),
        tooltip=tooltips,
    )

    text = bars.mark_text(
        align='left',
        baseline='middle',
        dx=3,
        color='black'
    ).encode(
        text=alt.Text(x, format=text_format)
    )

    # Combine the bars and text
    chart = (bars + text).resolve_scale(
        x='shared', y='shared'
    ).configure_view(strokeWidth=0).properties(
        width='container',
        title={
            'text': f"Year-on-Year comparison of {metric.title()} performance", 
            'subtitle': f"As of {datetime.strftime(date, '%a %d %B %Y')}"
        }
    )

    return chart

def plot_current_vs_last_year(
        ts: pd.DataFrame,
        metric: str = 'pledges', 
        date: pd.Timestamp = None,
        cap_last_x_days: int = None,
        show_title: bool = True,
    ) -> alt.Chart:
    '''
    Line plot that compares current year to previous year
    If cap_last_x_days is populated looks at the past x days
    if not, starts from 1st of January.
    '''
    if date is None:
        date = pd.to_datetime(max(ts.index.values))

    year_filter = ts.loc[date]['year']
    day_filter = ts.loc[date]['day_of_year']
    df = ts.query(f"(year in [{year_filter-1}, {year_filter}]) & (day_of_year<={day_filter})").copy()

    if cap_last_x_days is not None:
        df = df[df['day_of_year'] >= max(1, day_filter - cap_last_x_days)]

    if metric == "pledges":
        y = "total_pledge_in_year"
        y_title = "Funding"
        y_format = '$,.0f'
    elif metric == "citizens":
        y = "total_citizens_in_year"
        y_title = "Account Registrations"
        y_format = '+,.0f'
    else:
        raise ValueError(f"Only values permitted are 'pledges' and 'citizens', not {metric}")


    df_tooltip = df[['day_of_year', 'period', y, 'year', 'version_id']].pivot(index='day_of_year', columns=['year'])
    df_tooltip.rename(columns={'version_id': 'version'}, inplace=True)
    df_tooltip.columns = [f"{col[0]}_{int(col[1])}" for col in df_tooltip.columns.values]
    df_tooltip.reset_index(inplace=True)
    tooltips = generate_tooltip(df_tooltip)

    a = int(df['day_of_year'].min())
    b = int(df['day_of_year'].max())

    x_axis = alt.X('day_of_year:Q', title='Day of year', axis=alt.Axis(labelOverlap=True), scale=alt.Scale(domain=[a,b]))
    y_axis = alt.Y(f"{y}:Q", title=y_title, axis=alt.Axis(format=y_format), scale=alt.Scale(domainMin=0))


    lines = alt.Chart(df).mark_line().encode(
        x=x_axis,
        y=y_axis,
        color=alt.Color("year:O", sort=[year_filter, year_filter-1], scale=alt.Scale(range=YEAR_COMPARISON_COLORS[::-1]), title="Year"),
    ).properties(width='container')


    hover = alt.selection_point(
        name=f'{metric}_hover',
        fields=['day_of_year'],
        nearest=True,
        on="mouseover",
        empty="none",
    )

    points = lines.mark_point().encode(
        x=x_axis,
        opacity=alt.condition(hover, alt.value(1), alt.value(0))
    )

    dynamic_tooltip = (
        alt.Chart(df_tooltip)
        .mark_rule()
        .encode(
            x=x_axis,
            y=alt.value(0),
            opacity=alt.condition(hover, alt.value(0.3), alt.value(0)),
            tooltip=tooltips,
        )
        .add_params(hover)
    )

    chart = (lines + points + dynamic_tooltip)
    

    if show_title:
        chart = chart.properties(title={
                'text': f'{metric.capitalize()} acquisition: {year_filter} vs {year_filter-1} at same day of the year',
                'subtitle': f'Reference: {datetime.strftime(date, '%a %d %B %Y')}'
            }
    )

    return chart
