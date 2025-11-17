"""
レート制限設定

slowapi の Limiter インスタンスをアプリ全体で共有する。
X-Forwarded-For ヘッダーを優先してクライアントIPを判定。
"""

import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def get_real_ip(request: Request) -> str:
    """
    X-Forwarded-For ヘッダーを優先してクライアントIPを取得

    プロキシやロードバランサー経由の場合、X-Forwarded-For の最初のIPを使用。
    ヘッダーがない場合は get_remote_address にフォールバック。
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


# テスト環境ではレート制限を無効化
rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"
limiter = Limiter(key_func=get_real_ip, enabled=rate_limit_enabled)
