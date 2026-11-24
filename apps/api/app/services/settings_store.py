from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"

KEY_API_KEY = "deepseek_api_key"
KEY_BASE_URL = "deepseek_base_url"
KEY_MODEL = "deepseek_model"


def get_setting(db: Session, key: str) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else None


def set_setting(db: Session, key: str, value: str | None) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value


def get_deepseek_config(db: Session) -> dict[str, str | None]:
    rows = {
        row.key: row.value
        for row in db.scalars(
            select(AppSetting).where(
                AppSetting.key.in_([KEY_API_KEY, KEY_BASE_URL, KEY_MODEL])
            )
        ).all()
    }
    return {
        "api_key": rows.get(KEY_API_KEY),
        "base_url": rows.get(KEY_BASE_URL) or DEFAULT_DEEPSEEK_BASE_URL,
        "model": rows.get(KEY_MODEL) or DEFAULT_DEEPSEEK_MODEL,
    }


def mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"
