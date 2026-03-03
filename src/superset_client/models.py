from typing import Any, Literal

from pydantic import BaseModel


class ChartDataResult(BaseModel):
    data: list[dict]


class ChartDataResponseResult(BaseModel):
    annotation_data: list[dict[str, str]] | dict[str, Any] | None = None
    applied_filters: list[dict[str, Any]] = []
    cache_key: str | None = None
    cache_timeout: int | None = None
    cached_dttm: str | None = None
    colnames: list[str] = []
    coltypes: list[int] = []
    data: list[dict[str, Any]] = []
    error: str | None = None
    from_dttm: int | None = None
    is_cached: bool | None = None
    query: str = ""
    rejected_filters: list[dict[str, Any]] = []
    rowcount: int = 0
    stacktrace: str | None = None
    status: Literal[
        "stopped", "failed", "pending", "running", "scheduled", "success", "timed_out"
    ] = "success"
    to_dttm: int | None = None


class ChartDataResponse(BaseModel):
    result: list[ChartDataResponseResult]


class ChartDataAsyncResponse(BaseModel):
    channel_id: str
    job_id: str
    result_url: str
    status: str
    user_id: str | None = None


class Dashboard(BaseModel):
    id: int
    dashboard_title: str
    slug: str | None = None
    published: bool = False


class Chart(BaseModel):
    id: int
    slice_name: str
    viz_type: str
    dashboard_id: int | None = None
