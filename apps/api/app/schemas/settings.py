from pydantic import BaseModel, Field


class SettingsRead(BaseModel):
    deepseek_configured: bool
    deepseek_api_key_masked: str | None = None
    deepseek_base_url: str
    deepseek_model: str


class SettingsUpdate(BaseModel):
    deepseek_api_key: str | None = Field(default=None, min_length=1)
    deepseek_base_url: str | None = Field(default=None, min_length=1)
    deepseek_model: str | None = Field(default=None, min_length=1)
    clear_api_key: bool = False
