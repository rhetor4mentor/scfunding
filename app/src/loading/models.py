import math
from loguru import logger
from pydantic import BaseModel, validator, Field, root_validator
from datetime import datetime
from typing import Optional, Any


class ValidatedTransactionData(BaseModel):
    '''
    Desired format for parsed transactions
    '''
    datetime_utc: datetime
    total_pledge: float = Field(ge=0)
    delta_pledge: float
    total_citizens: int = Field(ge=0)
    delta_citizens: int

class HourlyTransactions(BaseModel):
    '''
    Data model and parsing logic for the Star Citizen Funding Tracker maintained by Sycend
    Crowdfunding Development Spreadsheet Version 3.0 - Hourly Data Import.csv
    '''
    datetime_utc: datetime = Field(description='Datetime UTC')
    total_pledge: Optional[float] = Field(description='Total Pledge in $')
    delta_pledge: Optional[float] = Field(description='Delta Pledge')
    total_citizens: Optional[int] = Field(description='Total Citizens')
    delta_citizens: Optional[int] = Field(description='Delta Citizens')
    data_correction_total_pledge: Optional[float] = Field(None)
    data_correction_total_citizen: Optional[int] = Field(None)

    @validator('datetime_utc', pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise ValueError(f"Invalid datetime format: {v}")
        return v


    @validator('total_pledge', 'delta_pledge', 'data_correction_total_pledge', pre=True)
    def parse_currency(cls, v) -> float:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        if isinstance(v, str):
            v = v.replace('$', '').replace('.', '').replace(',', '.')
        try:
            return float(v)
        except ValueError:
            raise ValueError(f"Invalid value for currency conversion: {v}")


    @validator('total_citizens', 'delta_citizens', 'data_correction_total_citizen', pre=True)
    def parse_integer(cls, v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        if isinstance(v, str):
            v = v.replace('.', '').replace(',', '.')
        try:
            return int(float(v))
        except ValueError:
            raise ValueError(f"Invalid value for integer conversion: {v}")


    @root_validator(pre=True)
    def check_pledge_and_citizens(cls, values):
        if not (values.get('total_pledge') or values.get('data_correction_total_pledge')):
            raise logger.error('Either total_pledge or data_correction_total_pledge must be provided.')
        if not (values.get('total_citizens') or values.get('data_correction_total_citizen')):
            raise logger.error('Either total_citizens or data_correction_total_citizen must be provided.')
        return values

    @property
    def data(self) -> ValidatedTransactionData:
        # Determine the correct values for total_pledge and total_citizens
        total_pledge = self.data_correction_total_pledge if self.data_correction_total_pledge is not None else self.total_pledge
        total_citizens = self.data_correction_total_citizen if self.data_correction_total_citizen is not None else self.total_citizens

        # Create and return an instance of the validated model
        return ValidatedTransactionData(
            datetime_utc=self.datetime_utc,
            total_pledge=total_pledge,
            delta_pledge=self.delta_pledge,
            total_citizens=total_citizens,
            delta_citizens=self.delta_citizens,
        )

class SalesAndComments(BaseModel):
    '''
    Crowdfunding Development Spreadsheet Version 3.0 - Sales & Comments
    Sale Type	Store Sales	Concept Sale	Game Milestones	Comments
    '''
    datetime_utc: datetime
    sale_type: Optional[Any]
    store_sales: Optional[Any]
    concept_sale: Optional[Any]
    game_milestones: Optional[Any]
    comments: Optional[Any]

class GameVersions(BaseModel):
    '''
    Crowdfunding Development Spreadsheet Version 3.0 - Gameversion
    Reformatted more cleanly
    '''

    date_start: datetime
    date_end: datetime
    version: str
    patch_count: int
    major: Optional[int]
    minor: Optional[int]
    patch: Optional[Any]
