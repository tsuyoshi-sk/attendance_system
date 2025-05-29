"""
認証バイパスミドルウェア

テスト環境で認証をバイパスするためのミドルウェア
"""

import os
from fastapi import Request
from typing import Dict, Any, Optional

# 環境変数でバイパスモードを制御
BYPASS_AUTH = os.getenv("BYPASS_AUTH", "false").lower() == "true"


async def auth_bypass_middleware(request: Request) -> Optional[Dict[str, Any]]:
    """
    認証バイパスミドルウェア

    BYPASS_AUTH環境変数がtrueの場合、テスト用の認証情報を返す

    Args:
        request: HTTPリクエスト

    Returns:
        Optional[Dict[str, Any]]: テスト用認証情報またはNone
    """
    if BYPASS_AUTH:
        # テスト用の偽認証情報を返す
        return {
            "user_id": "test_admin",
            "username": "admin",
            "role": "admin",
            "is_authenticated": True,
            "employee_id": None,
            "permissions": [
                "employee:read",
                "employee:write",
                "employee:delete",
                "report:read",
                "report:write",
                "system:admin",
            ],
        }
    # 通常の認証処理
    return None
