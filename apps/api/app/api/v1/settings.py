from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.services.settings_store import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    KEY_API_KEY,
    KEY_BASE_URL,
    KEY_MODEL,
    get_deepseek_config,
    mask_api_key,
    set_setting,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
def read_settings(db: Session = Depends(get_db)) -> SettingsRead:
    config = get_deepseek_config(db)
    api_key = config["api_key"]
    return SettingsRead(
        deepseek_configured=bool(api_key),
        deepseek_api_key_masked=mask_api_key(api_key),
        deepseek_base_url=config["base_url"] or DEFAULT_DEEPSEEK_BASE_URL,
        deepseek_model=config["model"] or DEFAULT_DEEPSEEK_MODEL,
    )


@router.put("", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsRead:
    if payload.clear_api_key:
        set_setting(db, KEY_API_KEY, None)
    elif payload.deepseek_api_key is not None:
        set_setting(db, KEY_API_KEY, payload.deepseek_api_key.strip())

    if payload.deepseek_base_url is not None:
        set_setting(db, KEY_BASE_URL, payload.deepseek_base_url.strip().rstrip("/"))

    if payload.deepseek_model is not None:
        set_setting(db, KEY_MODEL, payload.deepseek_model.strip())

    db.commit()
    return read_settings(db)
