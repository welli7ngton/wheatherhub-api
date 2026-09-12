from fastapi import FastAPI
from app.api.schemas.health import HealthResponse


def create_application() -> FastAPI:
    application = FastAPI(
        title="Wheatherhub API",
        version="0.1.0",
        contact={
            "name": "Wellington Almeida",
            "email": "welli7ngton.dev@gmail.com",
        },
    )

    @application.get(
        "/health",
        tags=["health"],
        summary="Check API health",
        description="Returns a lightweight liveness response for the API process.",
        response_description="The API process is healthy and accepting requests.",
        response_model=HealthResponse
    )
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    return application


app = create_application()
