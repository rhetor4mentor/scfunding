import os
import pandas as pd
import yaml
from loguru import logger
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import grangercausalitytests


def load_possible_features() -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, 'possible_features.yaml')
    try:
        with open(path, 'r') as file:
            config = yaml.safe_load(file)
            return config
    except Exception as e:
        logger.error(e)
