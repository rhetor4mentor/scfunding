# utils.py
import datetime
import os
import re
import pandas as pd
import yaml
from loguru import logger


def format_to_column(text: str) -> str:
    """
    Text formatter to conform to lowercase + underscore separation
    """
    return re.sub(r"[ -]+", "_", str(text)).lower()


def format_to_title(text: str) -> str:
    """
    Text formatter for tooltips
    """
    words = re.split("-|,|_| ", text)
    return " ".join([w.strip().capitalize() for w in words])


def frequency_to_numeric(freq: str) -> int:
    """
    Map frequencies to numerical values
    """

    freq_map = {
        "S": 1,  # Secondly
        "T": 2,  # Minutely
        "h": 3,  # Hourly
        "H": 3,  # Hourly
        "D": 4,  # Daily
        "W": 5,  # Weekly
        "W-SUN": 5,  # Start of Week
        "M": 6,  # Monthly
        "ME": 6,  # Monthly
        "Q": 7,  # Quarterly
        "A": 8,  # Annually
        "YE": 8,  # Annually
    }
    return freq_map.get(freq, 8)  # Default to a high number if unknown


def format_timestamp(timestamp: pd.Timestamp, freq: str = None) -> str:
    if (freq == "ME") or (freq.startswith("YE-")):
        formatted_timestamp = timestamp.strftime("%B %Y")  # e.g., "January 2023"
    elif freq == "W" or (freq.startswith("W-")):
        iso_year, iso_week_number, _ = timestamp.isocalendar()
        formatted_timestamp = f"{iso_year} W{iso_week_number}"  # e.g., "2023-W01"
    elif freq == "YE":
        formatted_timestamp = timestamp.strftime("%Y")  # e.g., "2023"
    elif freq == "D":
        formatted_timestamp = timestamp.strftime("%a %d %b %Y")  # e.g., "2023"
    else:
        formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")  # Default format
    return formatted_timestamp


def format_timedelta(td: datetime.timedelta) -> str:
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Build a human-readable string
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0 or days > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    # parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    # Join the parts with commas
    return ", ".join(parts) + " ago"


def format_currency(x):
    return "${:,.0f}".format(x)


def format_counts(x):
    return "{:,.0f}".format(x)


def format_percentage(x):
    return "{:.1%}".format(x)


def format_ordinal(x: float) -> str:
    """
    Formatter function to convert a number into its ordinal representation.
    """
    if pd.isnull(x):
        return x  # Keep NaN values as they are
    else:
        x = int(round(x))
        return f"{x}{('th' if 4 <= x % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(x % 10, 'th'))}"


def load_config(filename="config.yaml") -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, filename)
    try:
        with open(path, "r") as file:
            config = yaml.safe_load(file)
            return config
    except Exception as e:
        logger.error(f"Could not find {path} - at {os.getcwd()}")


def same_time_in_other_year(
    ts: pd.DataFrame, date: pd.Timestamp = None, year: int = None
) -> pd.DataFrame:
    """
    Arguments:
    ---------
    time_series (pd.DataFrame): A DataFrame with a DateTimeIndex.
    date (pd.Timestamp): The date for which to retrieve the latest row. Defaults to the last available date.
    year (int): The year for which to retrieve the latest row. Defaults to the year before the provided date's year.

    Returns:
    --------
    pd.Series: The latest row for the specified day of the year and year.
    """

    time_series = ts.copy().sort_index()

    if date is None:
        date = time_series.index[-1]
    else:
        date = pd.to_datetime(date).normalize()

    if year is None:
        year = date.year - 1

    mask = (time_series.index.dayofyear == date.dayofyear) & (
        time_series.index.year == year
    )

    latest_row = (
        time_series.loc[mask].iloc[-1] if not time_series.loc[mask].empty else None
    )

    return latest_row


def parse_version(version: str):
    """
    Parses a version string to extract major, minor, and patch numbers.

    Parameters:
    - version: str, the version string to parse.

    Returns:
    - tuple of (major, minor, patch) or (None, None, None) if not matched.
    """
    if not isinstance(version, str):
        return None, None, None

    # Regular expression to match version numbers
    match = re.search(r"_V?(\d+)(?:\.(\d+))?(?:\.(\d+[abcd]?))?$", version)

    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        patch = match.group(3) if match.group(3) else "0"
        return major, minor, patch
    else:
        return None, None, None


def yesterday():
    return datetime.datetime.now() - datetime.timedelta(days=1)
