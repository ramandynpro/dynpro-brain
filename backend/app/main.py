from fastapi import FastAPI

from app.api.routes import health, pilot, search

app = FastAPI(
    title="DynPro Brain API",
    description="Phase 1 MVP scaffold for explainable capability intelligence.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(search.router, prefix="/api/v1")
app.include_router(pilot.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "DynPro Brain API is running",
        "phase": "phase-1-mvp-scaffold",
    }
