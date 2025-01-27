import pandas as pd
from loguru import logger
from typing import List
from .loader import TransactionParser, CalendarEventParser, GameVersionParser

class CompleteTimeSeries:
    def __init__(self, 
                 transaction_file_path=None, 
                 calendar_file_path=None, 
                 game_version_file_path=None,
            ):
        self.transaction_parser = TransactionParser(file_path=transaction_file_path)
        self.calendar_event_parser = CalendarEventParser(file_path=calendar_file_path)
        self.game_version_parser = GameVersionParser(file_path=game_version_file_path)
        self.complete_time_series = self.get_time_series(freq='D')

    def get_time_series(self, freq: str ='D') -> pd.DataFrame:
        transactions = self.transaction_parser.get_time_series(freq=freq, append_time_metrics=False)
        calendar_events = self.calendar_event_parser.get_time_series(freq=freq, append_time_metrics=False)
        game_versions = self.game_version_parser.get_time_series_enriched(freq=freq, append_time_metrics=False)

        # max_date = max(
        #     transactions.index.max(),
        #     calendar_events.index.max(),
        #     game_versions.index.max()
        # )

        max_date = transactions.index.max()

        combined_df = transactions.join(calendar_events, how='outer')
        combined_df = combined_df.join(game_versions, how='outer')
        combined_df = combined_df.loc[:max_date]
        combined_df.fillna(method='ffill', inplace=True)

        combined_df = self.transaction_parser.time_series_constructor.add_time_metrics(time_series=combined_df)
        
        output = combined_df.dropna(subset=['delta_pledge']).asfreq(freq)
        output_max_date = combined_df.index.max()
        if output_max_date > max_date:
            logger.warning(f"max date introduced through ts combination: {output_max_date} vs expected {max_date}")

        return output

    @property
    def patch_stats(self, ) -> pd.DataFrame:
        '''
        Returns as table that shows for each patch: new citizens/day and duration 
        '''
        first_alpha01_patch_date = self.game_version_parser.versions.query('major==1').iloc[0]['date_start']

        patch_stats = self.time_series[self.time_series.index >= first_alpha01_patch_date].reset_index().groupby(['version_id']).agg(
            {
                'datetime_utc': [('date', 'min')],
                'delta_citizens': [('new citizens/day', lambda x: sum(x)/len(x))],
                'days_since_current_patch_launch': [('duration', 'max')],
            }
        )
        patch_stats.columns = patch_stats.columns.get_level_values(1)
        patch_stats = patch_stats.reset_index().set_index('date').sort_index()

        return patch_stats

    @property
    def time_series(self) -> pd.DataFrame:
        return self.complete_time_series
    
    @property
    def funding_years(self) -> List[int]:
        return sorted(set(self.complete_time_series.index.year))