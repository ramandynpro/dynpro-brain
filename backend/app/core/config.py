from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/dynpro_brain"
    vector_dimension: int = 384


settings = Settings()
