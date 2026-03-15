import os

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/dynpro_brain"
    vector_dimension: int = 384
    sample_data_dir: str = os.getenv("DYNPRO_SAMPLE_DATA_DIR", "data/sample_json")
    pilot_people_data_path: str | None = os.getenv("DYNPRO_PILOT_PEOPLE_PATH") or None


settings = Settings()
