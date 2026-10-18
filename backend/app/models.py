from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HealthResponse(ApiModel):
    status: str
    service: str
    database: str


class ApiErrorResponse(ApiModel):
    error: str
    code: str
    request_id: str
