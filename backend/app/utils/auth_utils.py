"""
認証ユーティリティ

認証関連のユーティリティ関数
"""

import os
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User, UserRole
from backend.app.api.auth import get_current_user, get_current_active_user


def get_current_user_or_bypass(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    現在のユーザーを取得（バイパス対応）
    
    BYPASS_AUTH環境変数がtrueの場合、テスト用のユーザー情報を返す
    
    Args:
        db: データベースセッション
        
    Returns:
        Dict[str, Any]: ユーザー情報
    """
    if os.getenv("BYPASS_AUTH", "false").lower() == "true":
        return {
            "user_id": "bypass_user",
            "id": 1,
            "role": UserRole.ADMIN,
            "username": "test_admin",
            "employee_id": None,
            "is_active": True,
            "permissions": [
                "employee:read",
                "employee:write",
                "employee:delete",
                "report:read",
                "report:write",
                "system:admin"
            ]
        }
    
    # 通常の認証処理
    try:
        return get_current_user()
    except Exception:
        # 認証エラーの場合もバイパスモードならテストユーザーを返す
        if os.getenv("BYPASS_AUTH", "false").lower() == "true":
            return {
                "user_id": "bypass_user",
                "id": 1,
                "role": UserRole.ADMIN,
                "username": "test_admin",
                "employee_id": None,
                "is_active": True,
                "permissions": [
                    "employee:read",
                    "employee:write",
                    "employee:delete",
                    "report:read",
                    "report:write",
                    "system:admin"
                ]
            }
        raise


def require_permission_or_bypass(permission: str):
    """
    特定の権限を要求するデコレータ（バイパス対応）
    
    Args:
        permission: 必要な権限
    """
    async def permission_checker(
        current_user = Depends(get_current_user_or_bypass)
    ) -> Dict[str, Any]:
        if os.getenv("BYPASS_AUTH", "false").lower() == "true":
            # バイパスモードでは全権限を持つ
            return current_user
            
        # 通常の権限チェック
        if hasattr(await current_user, 'get_permissions'):
            if permission not in await current_user.get_permissions():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"権限 '{permission}' が必要です"
                )
        elif 'permissions' in (await current_user):
            if permission not in await current_user['permissions']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"権限 '{permission}' が必要です"
                )
        
        return current_user
    
    return permission_checker