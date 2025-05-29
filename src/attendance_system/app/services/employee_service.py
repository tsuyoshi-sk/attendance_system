"""
従業員管理サービス

従業員情報の管理とビジネスロジックを提供
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from backend.app.models import Employee, EmployeeCard, User, WageType
from backend.app.schemas.employee import EmployeeCreate, EmployeeUpdate
from backend.app.schemas.employee_card import CardCreate
import hashlib
import logging

logger = logging.getLogger(__name__)


class EmployeeService:
    """従業員管理サービスクラス"""

    def __init__(self, db: Session):
        self.db = db

    async def create_employee(self, employee_data: EmployeeCreate) -> Employee:
        """
        新規従業員を作成

        Args:
            employee_data: 従業員作成データ

        Returns:
            Employee: 作成された従業員

        Raises:
            ValueError: バリデーションエラー
        """
        # 重複チェック
        existing = (
            self.db.query(Employee)
            .filter(
                or_(
                    Employee.employee_code == employee_data.employee_code,
                    Employee.email == employee_data.email
                    if employee_data.email
                    else False,
                )
            )
            .first()
        )

        if existing:
            if existing.employee_code == employee_data.employee_code:
                raise ValueError(f"従業員コード '{employee_data.employee_code}' は既に使用されています")
            else:
                raise ValueError(f"メールアドレス '{employee_data.email}' は既に使用されています")

        # 賃金情報の妥当性チェック
        self._validate_wage_data(
            employee_data.wage_type,
            employee_data.hourly_rate,
            employee_data.monthly_salary,
        )

        # 従業員を作成
        try:
            employee = Employee(**employee_data.model_dump())
            self.db.add(employee)
            self.db.commit()
            self.db.refresh(employee)

            logger.info(f"従業員を作成しました: {employee.employee_code} - {employee.name}")
            return employee

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"従業員作成エラー: {str(e)}")
            raise ValueError("従業員の作成に失敗しました")

    async def get_employee(self, employee_id: int) -> Optional[Employee]:
        """
        従業員を取得

        Args:
            employee_id: 従業員ID

        Returns:
            Employee: 従業員情報
        """
        return self.db.query(Employee).filter(Employee.id == employee_id).first()

    async def get_employee_by_code(self, employee_code: str) -> Optional[Employee]:
        """
        従業員コードで従業員を取得

        Args:
            employee_code: 従業員コード

        Returns:
            Employee: 従業員情報
        """
        return (
            self.db.query(Employee)
            .filter(Employee.employee_code == employee_code)
            .first()
        )

    async def get_employees(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Employee]:
        """
        従業員一覧を取得

        Args:
            skip: スキップ数
            limit: 取得数
            is_active: 有効フラグフィルター
            department: 部署フィルター
            search: 検索文字列

        Returns:
            List[Employee]: 従業員リスト
        """
        query = self.db.query(Employee)

        if is_active is not None:
            query = query.filter(Employee.is_active == is_active)

        if department:
            query = query.filter(Employee.department == department)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Employee.name.like(search_term),
                    Employee.name_kana.like(search_term),
                    Employee.employee_code.like(search_term),
                    Employee.email.like(search_term),
                )
            )

        return query.offset(skip).limit(limit).all()

    async def update_employee(
        self, employee_id: int, employee_data: EmployeeUpdate
    ) -> Employee:
        """
        従業員情報を更新

        Args:
            employee_id: 従業員ID
            employee_data: 更新データ

        Returns:
            Employee: 更新された従業員

        Raises:
            ValueError: 従業員が見つからない場合
        """
        employee = await self.get_employee(employee_id)
        if not employee:
            raise ValueError(f"従業員ID {employee_id} が見つかりません")

        # 更新データの処理
        update_data = employee_data.model_dump(exclude_unset=True)

        # メールアドレスの重複チェック
        if "email" in update_data and update_data["email"]:
            existing = (
                self.db.query(Employee)
                .filter(
                    Employee.email == update_data["email"], Employee.id != employee_id
                )
                .first()
            )
            if existing:
                raise ValueError(f"メールアドレス '{update_data['email']}' は既に使用されています")

        # 賃金情報の妥当性チェック
        if (
            "wage_type" in update_data
            or "hourly_rate" in update_data
            or "monthly_salary" in update_data
        ):
            wage_type = update_data.get("wage_type", employee.wage_type)
            hourly_rate = update_data.get("hourly_rate", employee.hourly_rate)
            monthly_salary = update_data.get("monthly_salary", employee.monthly_salary)
            self._validate_wage_data(wage_type, hourly_rate, monthly_salary)

        # 更新を適用
        for key, value in update_data.items():
            setattr(employee, key, value)

        employee.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(employee)
            logger.info(f"従業員を更新しました: {employee.employee_code}")
            return employee
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"従業員更新エラー: {str(e)}")
            raise ValueError("従業員の更新に失敗しました")

    async def delete_employee(self, employee_id: int) -> bool:
        """
        従業員を削除（論理削除）

        Args:
            employee_id: 従業員ID

        Returns:
            bool: 削除成功フラグ
        """
        employee = await self.get_employee(employee_id)
        if not employee:
            raise ValueError(f"従業員ID {employee_id} が見つかりません")

        # 論理削除
        employee.is_active = False
        employee.updated_at = datetime.utcnow()

        # 関連するカードも無効化
        cards = (
            self.db.query(EmployeeCard)
            .filter(EmployeeCard.employee_id == employee_id)
            .all()
        )
        for card in cards:
            card.is_active = False

        # 関連するユーザーアカウントも無効化
        user = self.db.query(User).filter(User.employee_id == employee_id).first()
        if user:
            user.is_active = False

        self.db.commit()
        logger.info(f"従業員を論理削除しました: {employee.employee_code}")
        return True

    async def add_employee_card(
        self, employee_id: int, card_data: CardCreate
    ) -> EmployeeCard:
        """
        従業員にカードを追加

        Args:
            employee_id: 従業員ID
            card_data: カード作成データ

        Returns:
            EmployeeCard: 作成されたカード
        """
        employee = await self.get_employee(employee_id)
        if not employee:
            raise ValueError(f"従業員ID {employee_id} が見つかりません")

        # カードIDmハッシュの重複チェック
        existing = (
            self.db.query(EmployeeCard)
            .filter(EmployeeCard.card_idm_hash == card_data.card_idm_hash)
            .first()
        )
        if existing:
            raise ValueError("このカードは既に別の従業員に登録されています")

        # カードを作成
        card = EmployeeCard(employee_id=employee_id, **card_data.model_dump())

        # 従業員の最初のカードの場合、employee.card_idm_hashも更新
        if not employee.card_idm_hash:
            employee.card_idm_hash = card_data.card_idm_hash

        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)

        logger.info(
            f"カードを追加しました: 従業員 {employee.employee_code}, カード {card.card_nickname or 'No nickname'}"
        )
        return card

    async def get_employee_cards(self, employee_id: int) -> List[EmployeeCard]:
        """
        従業員のカード一覧を取得

        Args:
            employee_id: 従業員ID

        Returns:
            List[EmployeeCard]: カードリスト
        """
        return (
            self.db.query(EmployeeCard)
            .filter(
                EmployeeCard.employee_id == employee_id, EmployeeCard.is_active == True
            )
            .all()
        )

    async def delete_card(self, card_id: int) -> bool:
        """
        カードを削除（論理削除）

        Args:
            card_id: カードID

        Returns:
            bool: 削除成功フラグ
        """
        card = self.db.query(EmployeeCard).filter(EmployeeCard.id == card_id).first()
        if not card:
            raise ValueError(f"カードID {card_id} が見つかりません")

        card.is_active = False

        # 従業員のメインカードIDmハッシュを更新（必要な場合）
        employee = (
            self.db.query(Employee).filter(Employee.id == card.employee_id).first()
        )
        if employee and employee.card_idm_hash == card.card_idm_hash:
            # 他のアクティブなカードを探す
            other_card = (
                self.db.query(EmployeeCard)
                .filter(
                    EmployeeCard.employee_id == card.employee_id,
                    EmployeeCard.id != card_id,
                    EmployeeCard.is_active == True,
                )
                .first()
            )

            if other_card:
                employee.card_idm_hash = other_card.card_idm_hash
            else:
                employee.card_idm_hash = None

        self.db.commit()
        logger.info(f"カードを論理削除しました: ID {card_id}")
        return True

    def _validate_wage_data(
        self,
        wage_type: WageType,
        hourly_rate: Optional[float],
        monthly_salary: Optional[int],
    ):
        """
        賃金データの妥当性をチェック

        Args:
            wage_type: 賃金タイプ
            hourly_rate: 時給
            monthly_salary: 月給

        Raises:
            ValueError: 妥当性エラー
        """
        if wage_type == WageType.HOURLY:
            if not hourly_rate or hourly_rate <= 0:
                raise ValueError("時給制の場合、時給は必須で0より大きい必要があります")
        elif wage_type == WageType.MONTHLY:
            if not monthly_salary or monthly_salary <= 0:
                raise ValueError("月給制の場合、月給は必須で0より大きい必要があります")
