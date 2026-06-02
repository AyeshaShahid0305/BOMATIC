from pydantic import BaseModel


class E1Output(BaseModel):
    vendor_list: list[str]
    requirements_baseline: list[dict]
    risk_flags: list[dict]
    sector: str
    frameworks_selected: list[str]
