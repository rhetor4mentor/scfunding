import numpy as np
import pandas as pd
import pingouin as pg
from loguru import logger
from tqdm import tqdm


def compute_correlations_with_sliding_window(
    df: pd.DataFrame,
    window_size: int = 60,
    x: str = "delta_pledge",
    y: str = "delta_citizens",
    method: str = "percbend",
) -> pd.DataFrame:
    """
    Assumes df.index is a timestamp (e.g. datetime64)
    """

    correlation_results = []
    periods = range(len(df) - window_size + 1)
    freq = pd.infer_freq(df.index)
    logger.info(
        f"correlations - computing correlations of {x} with {y} for {len(periods)} periods of size {window_size} (time resolution: {freq})"
    )

    for start in tqdm(periods):
        end = start + window_size
        window_df = df.iloc[start:end]

        corr = pg.corr(
            window_df[x],
            window_df[y],
            method="percbend",
        )

        correlation_results.append(
            {
                "start_date": window_df.index[0],
                "end_date": window_df.index[-1],
                "x": x,
                "y": y,
                "r": corr["r"].values[0],
                "p-val": corr["p-val"].values[0],
                "n": corr["n"].values[0],
                "power": corr["power"].values[0],
                "avg_x": np.mean(window_df[x]),
                "avg_y": np.mean(window_df[y]),
            }
        )

    correlation_df = pd.DataFrame(correlation_results)

    return correlation_df
