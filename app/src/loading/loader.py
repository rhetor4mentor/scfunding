# loader.py
# https://docs.google.com/spreadsheets/d/1n96sotjICGR8pw7SL74KTwrCHO6hoqRuAc2Y_fbIJaA/edit?gid=0#gid=0
import numpy as np
import os
import pandas as pd
from datetime import datetime, timezone
from loguru import logger
from pydantic import ValidationError
from tqdm import tqdm
from typing import List

from .models import HourlyTransactions, SalesAndComments, GameVersions
from .time_series import TimeSeriesConstructor
from .. import utils

config = utils.load_config()


class FileLoader:
    def __init__(self, file_path: str = None, url: str = None):
        if not file_path and not url:
            raise ValueError("You must specify either a 'file_path' or a 'url'.")

        self.file_path: str = file_path
        self.url: str = url
        self.raw_data: pd.DataFrame = None
        self.aggregation_functions: dict = None
        self.time_series_constructor: TimeSeriesConstructor = None
        self.load_data()

    def load_data(self):
        if self.file_path is not None:
            address = self.file_path
        elif self.url is not None:
            address = self.url

        try:
            logger.info(f"Loading data from {address}")
            self.raw_data = pd.read_csv(
                address,
                usecols=lambda column: not column.startswith("Unnamed"),
                low_memory=False,
            )
            logger.info(f"Data loaded successfully with shape {self.raw_data.shape}")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise

    def get_time_series(
        self,
        freq: str = "D",
        append_time_metrics: bool = True,
    ) -> pd.DataFrame:

        if not self.time_series_constructor:
            raise ValueError("time_series_constructor is not initialized.")
        try:
            time_series = self.time_series_constructor.get(
                freq, append_time_metrics=append_time_metrics
            )
            return time_series
        except Exception as e:
            logger.error(e)
            return pd.DataFrame()


class TransactionParser(FileLoader):
    """
    Class that downloads, parses and corrects hourly transaction data
    It also uses a time series constructor to convert the data into time-series at desired frequencies.

    arguments
    ---------
    file_path: str (None). If popupaled, the TransactionParser will use a local file path (or url) instead
    its predetermined URL (which is configured to download the CSV from Google Drive directly)
    """

    def __init__(self, file_path: str = None):
        url = config.get("GOOGLEDRIVE_URL_DOWNLOAD_TRANSACTIONS")
        super().__init__(file_path, url=url)

        self.aggregation_functions: dict = {
            "delta_pledge": "sum",
            "delta_citizens": "sum",
            "total_pledge_in_year": "max",
            "total_citizens_in_year": "max",
        }

        try:
            transactions = self.parse_dataframe(dataframe=self.raw_data)
        except Exception as e:
            logger.error(e)

        self.time_series_constructor = TimeSeriesConstructor(
            transactions, aggregation_functions=self.aggregation_functions
        )

    def correct_datetime_format(self, timestamp):
        """
        Flips YYYY/DD/MM to YYYY/MM/DD
        """
        date_str = str(timestamp)
        try:
            date_part, time_part = date_str.split(" ")
            year, day, month = date_part.split("-")
            # Swap day and month
            corrected_date_str = f"{year}-{month}-{day} {time_part}"
            return pd.to_datetime(corrected_date_str, format="%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Error correcting date {date_str}: {e}")
            return pd.NaT

    def parse_transactions(self, dataframe: pd.DataFrame) -> List[HourlyTransactions]:
        """
        Validates and parses hourly transaction data from an input dataframe that conforms
        to the Star Citizen funding tracker version 3.0.

        Arguments
        ---------
        dataframe: pd.DataFrame

        Returns
        -------
        List[src.loading.models.HourlyTransactions]
        """

        column_map: dict = dict(
            zip(
                dataframe.columns,
                [utils.format_to_column(c) for c in dataframe.columns],
            )
        )

        data = dataframe.copy()
        data.rename(columns=column_map, inplace=True)
        transactions = []
        for _, row in tqdm(data.iterrows()):
            try:
                t = HourlyTransactions(**row)
                transactions.append(t)
            except ValidationError as e:
                logger.error(f"Parsing failure at {row}:\n\n{e}")

        logger.success(f"Imported {len(transactions):,} hourly transactions")

        return transactions

    def parse_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Returns transaction data validated and parsed to add additional time-based variables

        This method also deals with a tricky corruption in the date formatting of hourly transactions
        that are present in 2012-2014 rows, and may someday pop back. They stand uncorrected in the data
        downloaded, and thus require some trickery.
        """
        transactions = self.parse_transactions(dataframe)
        succesful_records = []
        unsuccessful_records = []
        for t in transactions:
            try:
                succesful_records.append(t.data.model_dump())
            except ValidationError:
                unsuccessful_records.append(t)
                logger.error(t)

        logger.info(f"Validated {len(succesful_records):,} hourly transactions.")

        if len(unsuccessful_records) > 0:
            logger.warning(
                f"Excluded {len(unsuccessful_records)} records that did not conform to ValidatedTransactionData requirements"
            )

        dataframe = pd.DataFrame.from_records(succesful_records)
        # some time stamps are duplicated. but they correspond to different dates, with MM/DD being incorrectly used at times

        # transactions are recorded in chronological order, but at those indexes, we see dates going backward in time
        suspicious_dates = dataframe["datetime_utc"][
            dataframe["datetime_utc"].diff() < pd.Timedelta(days=0)
        ]

        if len(suspicious_dates) % 2 != 0:
            logger.warning("I probably did not solve corrupted dates")

        suspicious_indices = (
            suspicious_dates.shift(-1).dt.month == suspicious_dates.dt.day
        )
        for i in range(0, len(suspicious_indices), 2):
            if i + 1 < len(suspicious_indices):
                if suspicious_indices.iloc[i] and not suspicious_indices.iloc[i + 1]:
                    start_idx = suspicious_indices.index[i]
                    end_idx = suspicious_indices.index[i + 1] - 1
                    # logger.info(f"{start_idx}:{end_idx}")
                    dataframe.loc[(start_idx - 5) : (end_idx + 5)]
                    corrected_dates = dataframe.loc[start_idx:end_idx][
                        "datetime_utc"
                    ].apply(self.correct_datetime_format)
                    dataframe.loc[start_idx:end_idx, "datetime_utc"] = corrected_dates

        duplicated_timestamps = dataframe["datetime_utc"][
            dataframe["datetime_utc"].duplicated(keep="first")
        ]

        if len(duplicated_timestamps) > 0:
            # we need to look at all hours of a given problematic date, not just the duplicated rows
            problematic_dates = sorted(duplicated_timestamps.dt.date.unique())
            # duplication_event = pd.Timestamp('2013-12-05')
            for duplication_event in problematic_dates:
                incorrect_date_indexes = []
                matching_date_indexes = dataframe.index[
                    dataframe["datetime_utc"].dt.date == duplication_event
                ].to_series()
                point_of_rupture = matching_date_indexes[
                    matching_date_indexes.diff() >= 24
                ].values
                # index that non-ambiguously must refer to a different day, because rows are ordered by time of record
                # and each represent a single hour: if two consecutive matches have >24 rows of distance, they have more than 24h of distance
                # and thus we know their dates should have been different.
                # this thus forms two 'islands' of indexes, one that we know came first and another came second, since the chronological order
                # is respected in the row order.
                if len(point_of_rupture) > 1:
                    logger.error(
                        f"more than one point-of-rupture defined when trying to correct corrupted dates for {duplication_event.date()}"
                    )
                elif len(point_of_rupture) == 0:
                    logger.error(
                        f"no point-of-rupture defined when trying to correct corrupted dates for {duplication_event.date()}"
                    )
                else:
                    first_island = matching_date_indexes.loc[: point_of_rupture[0] - 1]
                    second_island = matching_date_indexes.loc[point_of_rupture[0] :]

                    if len(first_island) + len(second_island) != len(
                        matching_date_indexes
                    ):
                        logger.error(
                            f"incorrect island segmentation for {duplication_event.date()}"
                        )

                    # We know one must be in YYYY-MM-DD (expected), the other in YYYY-DD-MM (mistake):
                    # we just need to assess which.

                    if duplication_event.month > duplication_event.day:
                        incorrect_date_indexes = first_island
                    elif duplication_event.month < duplication_event.day:
                        incorrect_date_indexes = second_island

                    corrected_dates = dataframe.iloc[incorrect_date_indexes][
                        "datetime_utc"
                    ].apply(self.correct_datetime_format)
                    dataframe.loc[incorrect_date_indexes, "datetime_utc"] = (
                        corrected_dates
                    )

            if len(set(dataframe["datetime_utc"])) == len(dataframe):
                logger.success(
                    f"Corrected {len(problematic_dates)} dates recorded with reverted YYYY/DD/MM format."
                )
            else:
                logger.warning(
                    f"Still duplicates: {dataframe['datetime_utc'][dataframe['datetime_utc'].duplicated(keep=False)]}"
                )

        return dataframe.set_index("datetime_utc")

    @property
    def main_statistics(
        self,
    ) -> dict:
        """
        Return key indicators
        """
        hourly = self.time_series_constructor.get("h")
        latest = hourly.tail(1)
        last_year = utils.same_time_in_other_year(hourly)
        now = datetime.now(timezone.utc)

        output = {
            "time": {
                "now": now,
                "last_updated": latest.index[0],
                "time_since_measure": now - latest.index[0].tz_localize("UTC"),
                "year_completion_percentage": latest["day_of_year"].iloc[0] / 365.25,
            },
            "pledges": {
                "total_historically": latest["total_pledge"].iloc[0],
                "total_this_year": latest["total_pledge_in_year"].iloc[0],
                "total_year_on_year": last_year["total_pledge_in_year"],
            },
            "citizens": {
                "total_historically": latest["total_citizens"].iloc[0],
                "total_this_year": latest["total_citizens_in_year"].iloc[0],
                "total_year_on_year": last_year["total_citizens_in_year"],
            },
        }

        output["pledges"]["pct_change_year_on_year"] = (
            output["pledges"]["total_this_year"]
            / output["pledges"]["total_year_on_year"]
            - 1
        )
        output["citizens"]["pct_change_year_on_year"] = (
            output["citizens"]["total_this_year"]
            / output["citizens"]["total_year_on_year"]
            - 1
        )

        return output


class CalendarEventParser(FileLoader):
    """
    Class that downloads and parses sales event annotations (at daily level)
    It also uses a time series constructor to convert the data into time-series at desired frequencies.
    """

    def __init__(self, file_path: str = None):
        url = config.get("GOOGLEDRIVE_URL_DOWNLOAD_SALES_ANNOTATIONS")
        super().__init__(file_path, url=url)
        try:
            events = self.parse(dataframe=self.raw_data)
        except Exception as e:
            logger.error(e)

        self.aggregation_functions = {"on_sale": "sum"}

        self.time_series_constructor = TimeSeriesConstructor(
            dataframe=events,
            measurements=[
                "on_sale",
            ],
            summables=["on_sale"],
            deepest_granularity="D",
            aggregation_functions=self.aggregation_functions,
        )

    def parse(self, dataframe: pd.DataFrame = None) -> pd.DataFrame:

        if dataframe is None:
            dataframe = self.raw_data.copy()

        dataframe.columns.values[0] = "datetime_utc"
        dataframe.columns = [utils.format_to_column(c) for c in dataframe.columns]

        valid_records = []
        for _, row in dataframe.iterrows():
            try:
                record = SalesAndComments(**row)
                valid_records.append(record)
            except ValidationError as e:
                pass

        logger.info(f"{len(valid_records)} valid records.")

        valid_df = pd.DataFrame([record.dict() for record in valid_records]).set_index(
            "datetime_utc"
        )

        boolean_df = valid_df.notna()

        names = {
            "sale_type": "on_sale",
            "store_sales": "store_event",
            "concept_sale": "concept_launch",
            "game_milestones": "milestone",
            "comment": "comments",
        }

        boolean_df.rename(columns=names, inplace=True)
        return boolean_df


class GameVersionParser(FileLoader):
    """
    Class that downloads and parses game versions annotations (at day interval level)
    It also uses a time series constructor to convert the data into time-series at desired frequencies.
    """

    def __init__(self, file_path: str = None):
        url = config.get("GOOGLEDRIVE_URL_DOWNLOAD_GAMEVERSIONS_ANNOTATIONS")
        super().__init__(file_path, url=url)
        self.versions: pd.DataFrame = None
        self.versions_long: pd.DataFrame = None

        try:
            self.versions = self.parse(dataframe=self.raw_data)
            if self.versions is None or self.versions.empty:
                raise ValueError("Parsed DataFrame is None or empty.")
        except Exception as e:
            logger.error(e)

        try:
            self.versions_long = self.parse_to_long(dataframe=self.versions)
        except Exception as e:
            logger.error(e)

        self.aggregation_functions = {
            "days_since_current_patch_launch": [
                ("days_since_current_patch_launch", "max")
            ],
            "patch_count": [
                ("patches_during_period", lambda x: len(set(x))),
                ("version_id", "max"),
            ],
        }

        self.time_series_constructor = TimeSeriesConstructor(
            dataframe=self.versions_long,
            measurements=list(self.aggregation_functions.keys()),
            summables=[],
            deepest_granularity="D",
            interpolation_method="ffill",
            aggregation_functions=self.aggregation_functions,
        )

    @property
    def version_patch_count_map(
        self,
    ) -> dict:
        count_to_version_map = (
            self.versions[["patch_count", "version"]]
            .drop_duplicates()
            .set_index("patch_count")["version"]
            .to_dict()
        )
        return count_to_version_map

    def _clean_version_label(self, version_label: str) -> str:
        version = version_label.replace("Star_Citizen_", "")
        version = version.replace("_", " ")
        return version

    def _conform_older_version_numbers(
        self,
        data: pd.DataFrame,
        cutoff_date: pd.Timestamp = pd.Timestamp(2014, 6, 4),
    ) -> pd.DataFrame:
        early_date_mask = data["date_end"] <= cutoff_date
        data.loc[early_date_mask, "patch"] = data.loc[early_date_mask].apply(
            lambda row: f"{row['major']:.0f}.{row['minor']:.0f}", axis=1
        )
        data.loc[early_date_mask, ["major", "minor"]] = 0

        very_early_days = data["date_end"] <= pd.Timestamp(2013, 8, 30)

        data.loc[very_early_days, "patch"] = data[very_early_days]["version"]

        return data

    def parse(self, dataframe: pd.DataFrame = None) -> pd.DataFrame:

        today_str = datetime.now().strftime("%Y-%m-%d")

        if dataframe is None:
            dataframe = self.raw_data

        df = dataframe.copy()
        df.columns = [utils.format_to_column(c) for c in df.columns]
        df.dropna(subset=["date_end"], inplace=True)
        df["patch_count"] = df["patch_count"].astype(int)
        df.sort_values(["date_start"], inplace=True)
        df["date_end"] = df["date_end"].replace("3000-01-01", today_str)
        df["date_start"] = pd.to_datetime(df["date_start"]).dt.normalize()
        df["date_end"] = pd.to_datetime(df["date_end"]).dt.normalize()
        df[["major", "minor", "patch"]] = df["version"].apply(
            lambda v: pd.Series(utils.parse_version(v))
        )
        df["version"] = df["version"].apply(self._clean_version_label)

        df = self._conform_older_version_numbers(df)

        valid_records = []
        for _, row in df.iterrows():
            try:
                record = GameVersions(**row)
                valid_records.append(record)
            except ValidationError as e:
                pass

        logger.info(f"{len(valid_records)} valid game-version records.")
        valid_df = pd.DataFrame([record.dict() for record in valid_records])

        return valid_df

    def parse_to_long(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        expanded_df = pd.concat(
            dataframe.apply(self.expand_intervals, axis=1).tolist(), ignore_index=True
        )
        expanded_df.set_index("datetime_utc", inplace=True)
        return expanded_df

    def expand_intervals(self, row):
        date_range = pd.date_range(start=row["date_start"], end=row["date_end"])
        days_since_current_patch_launch = (date_range - row["date_start"]).days
        expanded_df = pd.DataFrame(
            {
                "datetime_utc": date_range,
                "version": row["version"],
                "major": row["major"],
                "minor": row["minor"],
                "patch": row["patch"],
                "patch_count": row["patch_count"],
                "days_since_current_patch_launch": days_since_current_patch_launch,
            }
        )
        return expanded_df

    def get_time_series_enriched(
        self, freq: str = "D", append_time_metrics: bool = True
    ) -> pd.DataFrame:
        ts = self.get_time_series(freq, append_time_metrics)
        ts["version_id"] = (
            ts["version_id"].replace(self.version_patch_count_map).astype(str)
        )
        return ts

    def year_view(self, year: int = None) -> pd.DataFrame:
        """
        Convenience method to look up what patches were live during a given year
        default to last year
        """

        if year is None:
            year = self.versions["date_end"].max().year
            logger.info(f"Default lookup of {year}")

        year_filter = self.versions_long.index.year == year
        data = (
            self.versions_long[year_filter][["version", "major", "minor", "patch"]]
            .drop_duplicates()
            .sort_index()
            .reset_index()
        )
        data["date"] = data["datetime_utc"]

        data["days_live"] = (
            pd.to_datetime(data["date"].shift(-1)) - pd.to_datetime((data["date"]))
        ).dt.days

        last_date = pd.to_datetime(data["date"]).iloc[-1]
        end_of_year = pd.Timestamp(year=last_date.year, month=12, day=31)
        today = pd.Timestamp(datetime.today())
        earliest_date = min(today, end_of_year)
        days_remaining = (earliest_date - last_date).days
        data.loc[data.index[-1], "days_live"] = days_remaining

        data["days_live"] = data["days_live"].astype(int)
        data["pct_live"] = data["days_live"] / end_of_year.dayofyear

        output = data[
            ["version", "date", "days_live", "pct_live", "major", "minor", "patch"]
        ]

        return output


if __name__ == "__main__":
    pd.set_option("display.max_rows", 1000)
    self = TransactionParser(
        "test/data/Crowdfunding Development Spreadsheet Version 3.0 - Hourly Data Import.csv"
    )
