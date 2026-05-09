from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PANEL_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PANEL_ROOT / '.env', override=False)


def _optional_path(env_name: str) -> Path | None:
    raw = os.getenv(env_name, '').strip()
    return Path(raw).expanduser() if raw else None


@dataclass(frozen=True)
class Settings:
    yiyin_bot_path: Path | None = _optional_path('YIYIN_BOT_PATH')
    admin_password: str = os.getenv('ADMIN_PASSWORD', '')
    site_base_url: str = os.getenv('SITE_BASE_URL', '').strip().rstrip('/')
    web_token_secret: str = os.getenv('WEB_TOKEN_SECRET', '').strip()
    jwt_secret: str = os.getenv('JWT_SECRET', '').strip() or os.getenv('WEB_TOKEN_SECRET', '').strip()
    token_timezone: str = os.getenv('TOKEN_TIMEZONE', 'Asia/Shanghai').strip() or 'Asia/Shanghai'
    backend_host: str = os.getenv('BACKEND_HOST', '127.0.0.1').strip() or '127.0.0.1'
    backend_port: int = int(os.getenv('BACKEND_PORT', '8000'))
    public_base_path: str = '/yiyin'
    api_base_path: str = '/yiyin/api'


settings = Settings()
