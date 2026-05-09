from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from .config import settings


def _token_timezone() -> ZoneInfo:
    return ZoneInfo(settings.token_timezone)


def local_now() -> datetime:
    return datetime.now(_token_timezone())


def date_string(now: datetime | None = None) -> str:
    current = now.astimezone(_token_timezone()) if now else local_now()
    return current.strftime('%Y-%m-%d')


def end_of_day(now: datetime | None = None) -> datetime:
    current = now.astimezone(_token_timezone()) if now else local_now()
    next_day = current + timedelta(days=1)
    return current.replace(
        year=next_day.year,
        month=next_day.month,
        day=next_day.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def build_group_token(group_id: str, now: datetime | None = None) -> str:
    if not settings.web_token_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='WEB_TOKEN_SECRET 未配置，无法校验群聊链接。',
        )
    payload = f'{group_id}:{date_string(now)}:{settings.web_token_secret}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def verify_group_token(group_id: str, token: str) -> bool:
    if not token:
        return False
    return token == build_group_token(group_id)


def create_admin_token() -> tuple[str, datetime]:
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='JWT_SECRET / WEB_TOKEN_SECRET 未配置，无法签发管理员令牌。',
        )
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    payload = {
        'sub': 'admin',
        'exp': expires_at,
        'iat': datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm='HS256')
    return token, expires_at.astimezone(_token_timezone())


def verify_admin_token(token: str) -> dict:
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='JWT_SECRET / WEB_TOKEN_SECRET 未配置，无法校验管理员令牌。',
        )
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=['HS256'])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='管理员登录状态已失效，请重新登录。',
        ) from exc
