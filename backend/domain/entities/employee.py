"""
従業員エンティティ

ビジネスロジックを含む従業員ドメインモデル
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, date


@dataclass
class Employee:
    """従業員エンティティ"""
    
    id: Optional[int]
    name: str
    employee_code: str
    email: str
    department_id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def can_punch(self) -> bool:
        """打刻可能かどうかを判定"""
        return self.is_active
    
    def is_valid_email(self) -> bool:
        """メールアドレスの妥当性チェック"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, self.email))
    
    def get_display_name(self) -> str:
        """表示用名前を取得"""
        return f"{self.name} ({self.employee_code})"
    
    def validate(self) -> List[str]:
        """エンティティの妥当性検証"""
        errors = []
        
        if not self.name or len(self.name.strip()) == 0:
            errors.append("名前は必須です")
        
        if not self.employee_code or len(self.employee_code.strip()) == 0:
            errors.append("従業員コードは必須です")
        
        if not self.is_valid_email():
            errors.append("有効なメールアドレスを入力してください")
        
        return errors


@dataclass
class Department:
    """部署エンティティ"""
    
    id: Optional[int]
    name: str
    code: str
    manager_id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def can_add_employee(self) -> bool:
        """従業員を追加可能かどうか"""
        return self.is_active
    
    def validate(self) -> List[str]:
        """部署の妥当性検証"""
        errors = []
        
        if not self.name or len(self.name.strip()) == 0:
            errors.append("部署名は必須です")
        
        if not self.code or len(self.code.strip()) == 0:
            errors.append("部署コードは必須です")
        
        return errors