from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class ErrorCode(StrEnum):
    INVALID_COORDINATES = "INVALID_COORDINATES"
    INVALID_QUERY = "INVALID_QUERY"
    WEATHER_PROVIDER_TIMEOUT = "WEATHER_PROVIDER_TIMEOUT"
    WEATHER_PROVIDER_UNAVAILABLE = "WEATHER_PROVIDER_UNAVAILABLE"
    WEATHER_PROVIDER_INVALID_RESPONSE = "WEATHER_PROVIDER_INVALID_RESPONSE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    request_id: UUID


class ErrorResponse(BaseModel):
    error: ErrorDetail
