import numpy as np
import pandas as pd

from loguru import logger
from .. import utils
from typing import List, Dict

class TimeSeriesConstructor:
    '''
    General class to handle time series
    '''
    def __init__(self, 
            dataframe: pd.DataFrame,
            interpolation_method: str = 'linear', 
            measurements: List[str] = ['total_pledge', 'total_citizens'],
            summables: List[str] = ['delta_pledge', 'delta_citizens'],
            deepest_granularity: str = 'h',
            aggregation_functions: Dict[str, str] = None,
        ):
        """
        Formats TimeSeries with a DataFrame
        """
        self.dataframe: pd.DataFrame = dataframe
        self.freq = deepest_granularity
        self.interpolation_method = interpolation_method
        self.deepest_time_series: pd.DataFrame = None
        self.measurements: List[str] = measurements
        self.summables: List[str] = summables
        self.aggregation_functions: dict = aggregation_functions

        if self.aggregation_functions is None:
            logger.warning(f"TimeSeriesConstructor instance initiated without aggregation_functions, will use a harcoded default")
            self.aggregation_functions =  {
                'delta_pledge': 'sum',
                'delta_citizens': 'sum',
                'total_pledge_in_year': 'max',
                'total_citizens_in_year': 'max'
            }

        if not isinstance(self.dataframe.index, pd.DatetimeIndex):
            raise ValueError("DataFrame must have a DatetimeIndex")

        self.process()

    def add_time_metrics(self, time_series: pd.DataFrame) -> pd.DataFrame:
        '''
        Appends useful time-based metrics for reporting and modelling
        '''
        freq = pd.infer_freq(time_series.index)
        freq_numeric = utils.frequency_to_numeric(freq)

        if freq_numeric <= 8:  
            time_series['year'] = time_series.index.year
        if freq_numeric <= 7:
            time_series['quarter'] = time_series.index.quarter
        if freq_numeric <= 6:
            time_series['month'] = time_series.index.month
        if freq_numeric <=5:
            time_series['week_of_year'] = time_series.index.isocalendar().week
        if freq_numeric <=4:
            time_series['day_of_year'] = time_series.index.dayofyear
            time_series['day_of_week'] = time_series.index.dayofweek
            time_series['is_weekend'] = time_series['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
        if freq in ['h', 'H']:
            time_series['hour'] = time_series.index.hour
        
        time_series['period'] = pd.Series(time_series.index).apply(utils.format_timestamp, freq=freq).values

        return time_series

    def recompute_summables(self, time_series: pd.DataFrame) -> pd.DataFrame:
        '''
        Appends new delta_citizens and delta_pledge columns recomputed from totals
        '''
        if (not 'delta_citizens' in time_series.columns) and ('delta_citizens' in self.summables):
            time_series.loc[:, 'delta_citizens'] = time_series['total_citizens'].diff()
            time_series['delta_citizens'].iloc[0] = time_series['total_citizens'].iloc[0]
        if (not 'delta_pledge' in time_series.columns) and ('delta_pledge' in self.summables):
            time_series.loc[:, 'delta_pledge'] = time_series['total_pledge'].diff()
            time_series['delta_pledge'].iloc[0] = time_series['total_pledge'].iloc[0]
        return time_series

    def add_totals(self, time_series: pd.DataFrame) -> pd.DataFrame:
        '''
        Add summable variables into the input time_series
        '''
        if (not 'total_citizens' in time_series.columns) and ('delta_citizens' in self.summables):
            time_series.loc[:, 'total_citizens'] = time_series['delta_citizens'].cumsum()
        if (not 'total_pledge' in time_series.columns) and ('delta_citizens' in self.summables):
            time_series.loc[:, 'total_pledge'] = time_series['delta_pledge'].cumsum()

        return time_series
    
    def add_rolling_totals(self, time_series: pd.DataFrame, last_periods: int = 30) -> pd.DataFrame:
        """
        Add rolling sum columns for the summable metrics over the last specified periods (up until the current timestamp, exclusive).

        Arguments:
        ----------
        - time_series (pd.DataFrame): The DataFrame containing the time series data.
        - last_periods (int): The number of periods to look back for the rolling sum.

        Returns:
        --------
        - pd.DataFrame: The DataFrame with the new rolling sum columns added.
        """
        for summable in self.summables:
            s = summable.replace('delta_','')
            column_name = f"{s}_prior_{last_periods}_periods"
            time_series[column_name] = time_series[summable].rolling(window=last_periods, min_periods=1).sum().shift(1)

        return time_series

    def add_averages(self, time_series: pd.DataFrame) -> pd.DataFrame:

        if ('total_citizens' in time_series.columns) and ('total_pledge' in time_series.columns):

            time_series['cumulative_avg_pledge_total'] = np.where(
                    time_series['total_citizens'] != 0,
                    time_series['total_pledge'] / time_series['total_citizens'],
                    np.nan 
                )

            time_series['local_avg_pledge_total'] = np.where(
                time_series['delta_citizens'] != 0,
                time_series['delta_pledge'] / time_series['delta_citizens'],
                np.nan
            )

        return time_series

    def add_in_year_totals(self, time_series: pd.DataFrame) -> pd.DataFrame:
        if 'delta_citizens' in self.summables:
            time_series['total_citizens_in_year'] = time_series.groupby(time_series.index.year)['delta_citizens'].cumsum()

        if 'delta_pledge' in self.summables:
            time_series['total_pledge_in_year'] = time_series.groupby(time_series.index.year)['delta_pledge'].cumsum()

        return time_series

    def process(self, ) -> None:
        """
        Process the time series at its deepest granularity (by hour)

        returns
        -------
        pd.DataFrame
        """

        df = self.dataframe[self.measurements].groupby(self.dataframe.index).last()
        df = df.asfreq(self.freq).interpolate(method=self.interpolation_method).pipe(self.recompute_summables).pipe(self.add_in_year_totals)
        self.deepest_time_series = df

    def get(self, 
            freq: str = 'D', 
            last_periods: int = 30,
            append_time_metrics: bool = True,
        ) -> pd.DataFrame:
        if freq.startswith('W'):
            freq = freq + '-SUN'
        
        logger.info(f"Providing time series at desired frequency ({freq})")

        time_series = self.deepest_time_series[list(self.aggregation_functions.keys())].resample(freq,).agg(self.aggregation_functions).ffill()
        if isinstance(time_series.columns, pd.MultiIndex):
            time_series.columns = time_series.columns.get_level_values(1)

        output = (time_series.pipe(self.add_totals)
                .pipe(self.add_averages)
                .pipe(self.add_rolling_totals, last_periods=last_periods))

        if append_time_metrics:
            output = output.pipe(self.add_time_metrics)

        return output