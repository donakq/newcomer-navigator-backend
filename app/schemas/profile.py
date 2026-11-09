from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Profile(BaseModel):
    """A student's situation. None means "not answered yet"."""

    model_config = ConfigDict(extra="forbid")

    in_us: bool | None = None
    arrival_date: date | None = None
    visa: Literal["F-1"] = "F-1"
    state: Literal["WA"] = "WA"
    school: str | None = None
    degree_level: Literal["undergrad", "master", "phd"] | None = None
    year: int | None = None
    has_ssn: bool | None = None
    has_job_offer: bool | None = None
    job_type: Literal["on_campus", "CPT", "OPT"] | None = None
    has_income: bool | None = None
    has_us_phone: bool | None = None
    has_bank_account: bool | None = None
    has_state_id: bool | None = None
    housing_status: Literal["none", "temporary", "leased"] | None = None
