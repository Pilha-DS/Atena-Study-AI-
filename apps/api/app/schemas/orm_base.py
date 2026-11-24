from pydantic import BaseModel, ConfigDict


class ORMCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
