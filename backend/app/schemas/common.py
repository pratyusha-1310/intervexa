from pydantic import BaseModel


class RootResponse(BaseModel):
    """Response schema for the root endpoint."""

    service: str
    status: str


class HealthResponse(BaseModel):
    """Response schema for the health-check endpoint."""

    status: str
