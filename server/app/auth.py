from typing import Optional

from fastapi import HTTPException, Request, status

from .config import AppConfig


def _extract_bearer(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def _extract_ui_token(request: Request) -> Optional[str]:
    token = _extract_bearer(request.headers.get("Authorization"))
    if token:
        return token
    return request.query_params.get("token")


def _get_config(request: Request) -> AppConfig:
    return request.app.state.config


def require_device_auth(request: Request) -> None:
    config = _get_config(request)
    token = _extract_bearer(request.headers.get("Authorization"))
    if config.device_tokens:
        if token in config.device_tokens:
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")
    if config.allow_unauth:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Device auth required; set INVENTORY_DEVICE_TOKENS or INVENTORY_ALLOW_UNAUTH=true",
    )


def require_ui_auth(request: Request) -> None:
    config = _get_config(request)
    token = _extract_ui_token(request)
    if config.ui_token:
        if token == config.ui_token:
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid UI token")
    if config.allow_unauth:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="UI auth required; set INVENTORY_UI_TOKEN or INVENTORY_ALLOW_UNAUTH=true",
    )
