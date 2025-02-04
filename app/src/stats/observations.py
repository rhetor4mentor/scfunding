import pandas as pd
from scipy.stats import percentileofscore
from datetime import datetime
from .. import utils

def records(df: pd.DataFrame, metric: str = 'delta_pledge', n=5, ascending=False) -> pd.DataFrame:
    """ 
    Returns the top N rows of a DataFrame based on a specified metric and adds a 'time_since_event' column.

    Parameters:
    - df (pd.DataFrame): The DataFrame containing the time series data with a datetime index.
    - metric (str): The column name of the metric to rank by.
    - n (int): The number of top rows to return. Default is 5.
    - ascending (bool): Sort order. False for descending (default), True for ascending.

    Returns:
    - pd.DataFrame: A DataFrame containing the top N rows sorted by the specified metric with 'time_since_event' column.
    """
    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in DataFrame columns.")
    
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a DatetimeIndex.")
    
    data = df.copy()

    # Calculate 'time_since_event' as the difference between now and the index
    data['time_since_event'] = datetime.now() - df.index

    # Sort the DataFrame by the specified metric
    sorted_df = data.sort_values(by=metric, ascending=ascending)

    priority_cols = ['period', metric, 'time_since_event']
    columns_order = priority_cols + [col for col in sorted_df.columns if col not in priority_cols]
    
    formats: dict = {}
    for c in df.columns:
        if 'pledge' in c:
            formats[c] = utils.format_currency
        if 'citizens' in c:
            formats[c] = utils.format_counts

    styled_df = sorted_df[columns_order].head(n).style.format(formats)

    # Return the top N rows
    return styled_df

def precedence(df: pd.DataFrame, timestamp: pd.Timestamp = None,  metric: str = 'delta_pledge') -> pd.DataFrame:
    '''
    Calculates the frequency of a given date's metric in the historical data.

    Parameters:
    - df (pd.DataFrame): The DataFrame containing the time series data with a datetime index.
    - metric (str): The column name of the metric to analyze.
    - timestamp (str or pd.Timestamp): The timestamp to compare against, can be a full date-time or just year/month.

    Returns:
    - pd.DataFrame
    '''

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in DataFrame columns.")
    
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a DatetimeIndex.")
    
    if timestamp is None:
        timestamp = df.index[-1]

    # Convert the timestamp to a pd.Timestamp if it's a string
    if isinstance(timestamp, str):
        timestamp = pd.to_datetime(timestamp)
    
    # Ensure the timestamp is within the DataFrame's index range
    if timestamp not in df.index:
        raise ValueError("Timestamp not found in DataFrame index.")
    
    # Get the metric value at the specified timestamp
    metric_value_at_timestamp = df.loc[timestamp, metric]
    
    # Calculate the percentage of rows with a metric value as high or higher than the timestamp's metric
    total_rows = len(df)
    rows_with_higher_or_equal_metric = df[df[metric] >= metric_value_at_timestamp]
    percentage_all = (len(rows_with_higher_or_equal_metric) / total_rows)    
    percentile_rank = percentileofscore(df[metric].dropna(), metric_value_at_timestamp)

    # Calculate the percentage of rows prior to the timestamp with a metric value as high or higher
    prior_rows = df[df.index < timestamp]
    rows_prior_with_higher_or_equal_metric = prior_rows[prior_rows[metric] >= metric_value_at_timestamp]
    percentage_prior = (len(rows_prior_with_higher_or_equal_metric) / len(prior_rows)) if len(prior_rows) > 0 else 0
    metric_rank = df[metric].rank(ascending=False)
    rank_at_timestamp = metric_rank.loc[timestamp]

    output = pd.DataFrame({
        'period': [df.loc[timestamp, 'period']],
        'version': [df.loc[timestamp, 'version_id'] if 'version_id' in df.columns else None],
        'on_sale': [df.loc[timestamp, 'on_sale'] if 'on_sale' in df.columns else None],
        'period frequency': pd.infer_freq(df.index),
        'metric': [metric],
        'value': [metric_value_at_timestamp],
        'pct_better_periods' : [percentage_all],
        'pct_better_periods_prior': [percentage_prior],
        'percentile': percentile_rank,
        'rank': rank_at_timestamp,
        'n periods': [len(df)],
        'total_pledge': [df.loc[timestamp, 'total_pledge']],
        'total_citizens': [df.loc[timestamp, 'total_citizens']],
    }, index=[timestamp])

    formats: dict = {
        'pct_better_periods': utils.format_percentage,
        'pct_better_periods_prior': utils.format_percentage,
        'percentile': utils.format_ordinal,
    }

    if 'pledge' in metric:
        formats['value'] = utils.format_currency
    if 'citizens' in metric:
        formats['value'] = utils.format_counts

    styled_df = output.style.format(formats)

    return styled_df

    