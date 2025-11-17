"""
通知サービス

Slack、メール、その他の通知チャネルへの通知機能を提供
"""

import asyncio
import json
from datetime import date, datetime
from typing import List, Dict, Any, Optional
import aiohttp
import logging

from config.config import config

logger = logging.getLogger(__name__)


class NotificationService:
    """通知サービスクラス"""
    
    def __init__(self):
        self.slack_webhook_url = config.SLACK_WEBHOOK_URL if hasattr(config, 'SLACK_WEBHOOK_URL') else None
        self.admin_channel = "#attendance-admin"
        self.alert_channel = "#attendance-alerts"
        self.realtime_channel = "#attendance-realtime"
    
    async def send_slack_notification(
        self,
        channel: str,
        title: str,
        message: str,
        color: str = "good",
        fields: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Slack通知を送信
        
        Args:
            channel: 送信先チャンネル
            title: タイトル
            message: メッセージ本文
            color: 添付ファイルの色（good, warning, danger）
            fields: 追加フィールド
        
        Returns:
            bool: 送信成功/失敗
        """
        if not self.slack_webhook_url:
            logger.warning("Slack Webhook URLが設定されていません")
            return False
        
        try:
            payload = {
                "channel": channel,
                "username": "勤怠管理システム",
                "icon_emoji": ":clock9:",
                "attachments": [{
                    "color": color,
                    "title": title,
                    "text": message,
                    "fields": fields or [],
                    "footer": "Attendance System",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Slack通知送信成功: {title}")
                        return True
                    else:
                        logger.error(f"Slack通知送信失敗: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Slack通知送信エラー: {e}")
            return False
    
    async def send_daily_alerts(
        self,
        target_date: date,
        alerts: List[Dict[str, Any]]
    ):
        """
        日次アラートを送信
        
        Args:
            target_date: 対象日
            alerts: アラートリスト
        """
        if not alerts:
            return
        
        # アラートタイプ別に集計
        overtime_alerts = [a for a in alerts if a["type"] == "overtime"]
        missing_punch_alerts = [a for a in alerts if a["type"] == "missing_punch"]
        
        fields = []
        
        if overtime_alerts:
            overtime_list = "\n".join([
                f"• {a['employee']}: {a['message']}"
                for a in overtime_alerts[:5]  # 最大5件
            ])
            if len(overtime_alerts) > 5:
                overtime_list += f"\n... 他{len(overtime_alerts) - 5}件"
            
            fields.append({
                "title": f"⚠️ 長時間労働 ({len(overtime_alerts)}名)",
                "value": overtime_list,
                "short": False
            })
        
        if missing_punch_alerts:
            missing_list = "\n".join([
                f"• {a['employee']}"
                for a in missing_punch_alerts[:10]  # 最大10件
            ])
            if len(missing_punch_alerts) > 10:
                missing_list += f"\n... 他{len(missing_punch_alerts) - 10}名"
            
            fields.append({
                "title": f"❌ 打刻漏れ ({len(missing_punch_alerts)}名)",
                "value": missing_list,
                "short": False
            })
        
        await self.send_slack_notification(
            channel=self.alert_channel,
            title=f"日次勤怠アラート - {target_date}",
            message=f"{target_date} の勤怠に関するアラートです",
            color="warning",
            fields=fields
        )
    
    async def send_monthly_alerts(
        self,
        year: int,
        month: int,
        alerts: List[Dict[str, Any]]
    ):
        """
        月次アラートを送信
        
        Args:
            year: 年
            month: 月
            alerts: アラートリスト
        """
        if not alerts:
            return
        
        # 重要度別に分類
        error_alerts = [a for a in alerts if a.get("severity") == "error"]
        warning_alerts = [a for a in alerts if a.get("severity") == "warning"]
        info_alerts = [a for a in alerts if a.get("severity") == "info"]
        
        fields = []
        
        if error_alerts:
            error_list = "\n".join([
                f"• {a['employee']}: {a['message']}"
                for a in error_alerts
            ])
            fields.append({
                "title": f"🚨 重要アラート ({len(error_alerts)}件)",
                "value": error_list,
                "short": False
            })
        
        if warning_alerts:
            warning_list = "\n".join([
                f"• {a['employee']}: {a['message']}"
                for a in warning_alerts[:10]
            ])
            if len(warning_alerts) > 10:
                warning_list += f"\n... 他{len(warning_alerts) - 10}件"
            
            fields.append({
                "title": f"⚠️ 警告 ({len(warning_alerts)}件)",
                "value": warning_list,
                "short": False
            })
        
        color = "danger" if error_alerts else "warning" if warning_alerts else "good"
        
        await self.send_slack_notification(
            channel=self.alert_channel,
            title=f"月次勤怠アラート - {year}年{month}月",
            message=f"{year}年{month}月の勤怠に関するアラートです",
            color=color,
            fields=fields
        )
    
    async def send_admin_notification(
        self,
        title: str,
        message: str,
        severity: str = "info"
    ):
        """
        管理者向け通知を送信
        
        Args:
            title: タイトル
            message: メッセージ
            severity: 重要度（info, warning, error）
        """
        color_map = {
            "info": "good",
            "warning": "warning",
            "error": "danger"
        }
        
        await self.send_slack_notification(
            channel=self.admin_channel,
            title=title,
            message=message,
            color=color_map.get(severity, "good")
        )
    
    async def send_overtime_alert(
        self,
        employee_name: str,
        overtime_hours: float,
        period: str = "daily"
    ):
        """
        残業アラートを送信
        
        Args:
            employee_name: 従業員名
            overtime_hours: 残業時間
            period: 期間（daily, monthly）
        """
        if period == "daily":
            title = "⚠️ 日次残業アラート"
            message = f"{employee_name}の本日の残業時間が{overtime_hours:.1f}時間です"
            color = "warning"
        else:
            title = "🚨 月次残業アラート"
            message = f"{employee_name}の月間残業時間が{overtime_hours:.1f}時間に達しました"
            color = "danger" if overtime_hours >= 60 else "warning"
        
        fields = [
            {
                "title": "従業員",
                "value": employee_name,
                "short": True
            },
            {
                "title": "残業時間",
                "value": f"{overtime_hours:.1f}時間",
                "short": True
            }
        ]
        
        await self.send_slack_notification(
            channel=self.alert_channel,
            title=title,
            message=message,
            color=color,
            fields=fields
        )
    
    async def send_punch_notification(
        self,
        employee_name: str,
        punch_type: str,
        punch_time: datetime
    ):
        """
        打刻通知を送信（リアルタイム通知用）
        
        Args:
            employee_name: 従業員名
            punch_type: 打刻種別
            punch_time: 打刻時刻
        """
        punch_type_display = {
            "in": "出勤",
            "out": "退勤",
            "outside": "外出",
            "return": "戻り"
        }
        
        emoji_map = {
            "in": "🏢",
            "out": "🏠",
            "outside": "🚶",
            "return": "🔙"
        }
        
        type_name = punch_type_display.get(punch_type, punch_type)
        emoji = emoji_map.get(punch_type, "⏰")
        
        message = f"{emoji} {employee_name}が{type_name}しました"
        
        fields = [
            {
                "title": "時刻",
                "value": punch_time.strftime("%H:%M:%S"),
                "short": True
            },
            {
                "title": "種別",
                "value": type_name,
                "short": True
            }
        ]
        
        await self.send_slack_notification(
            channel=self.realtime_channel,
            title="打刻通知",
            message=message,
            color="good",
            fields=fields
        )
    
    async def send_batch_error_notification(
        self,
        batch_type: str,
        error_message: str,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        """
        バッチ処理エラー通知
        
        Args:
            batch_type: バッチ種別（daily, monthly）
            error_message: エラーメッセージ
            additional_info: 追加情報
        """
        fields = [
            {
                "title": "バッチ種別",
                "value": batch_type,
                "short": True
            },
            {
                "title": "発生時刻",
                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "short": True
            },
            {
                "title": "エラー内容",
                "value": error_message[:500],  # 長すぎる場合は切り詰め
                "short": False
            }
        ]
        
        if additional_info:
            for key, value in additional_info.items():
                fields.append({
                    "title": key,
                    "value": str(value),
                    "short": True
                })
        
        await self.send_slack_notification(
            channel=self.admin_channel,
            title="🚨 バッチ処理エラー",
            message="バッチ処理でエラーが発生しました",
            color="danger",
            fields=fields
        )
