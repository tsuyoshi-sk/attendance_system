"""
オフライン打刻キュー管理

ネットワーク障害時の打刻データを保持し、復旧時に自動同期します。
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Lock, Thread, Event
from pathlib import Path
import sqlite3
from queue import Queue, Empty
import hashlib

from config.config import config
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


logger = logging.getLogger(__name__)


class OfflineQueueManager:
    """オフライン打刻キュー管理クラス"""
    
    MAX_QUEUE_SIZE = 100  # キューの最大サイズ
    RETENTION_DAYS = 7    # データ保持期間（日）
    SYNC_INTERVAL = 60    # 同期試行間隔（秒）
    BATCH_SIZE = 10       # 一度に同期する件数
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: SQLiteデータベースのパス
        """
        if db_path is None:
            db_path = os.path.join(config.DATA_DIR, "offline_queue.db")
        
        self.db_path = db_path
        self.db_lock = Lock()
        self.sync_thread = None
        self.stop_event = Event()
        self.is_running = False
        self.slack_client = None
        
        # Slack通知の設定
        if config.SLACK_ENABLED and config.SLACK_TOKEN:
            self.slack_client = WebClient(token=config.SLACK_TOKEN)
        
        # データベース初期化
        self._init_database()
        
        # 起動時に古いデータをクリーンアップ
        self._cleanup_old_records()
    
    def _init_database(self):
        """データベーステーブルを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offline_punches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT NOT NULL,
                    punch_type TEXT NOT NULL,
                    card_idm_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    device_type TEXT,
                    ip_address TEXT,
                    location_lat REAL,
                    location_lon REAL,
                    note TEXT,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at TEXT,
                    error_message TEXT,
                    data_hash TEXT NOT NULL UNIQUE
                )
            """)
            
            # インデックス作成
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON offline_punches(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_retry_count 
                ON offline_punches(retry_count)
            """)
            conn.commit()
    
    def add_punch(self, punch_data: Dict[str, Any]) -> bool:
        """
        打刻データをキューに追加
        
        Args:
            punch_data: 打刻データ
        
        Returns:
            bool: 成功/失敗
        """
        try:
            # データハッシュを生成（重複防止）
            data_hash = self._generate_data_hash(punch_data)
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    # キューサイズチェック
                    count = conn.execute(
                        "SELECT COUNT(*) FROM offline_punches"
                    ).fetchone()[0]
                    
                    if count >= self.MAX_QUEUE_SIZE:
                        # 最も古いレコードを削除
                        conn.execute("""
                            DELETE FROM offline_punches 
                            WHERE id IN (
                                SELECT id FROM offline_punches 
                                ORDER BY created_at ASC 
                                LIMIT 1
                            )
                        """)
                        logger.warning("オフラインキューが満杯のため、最古のレコードを削除しました")
                    
                    # データ挿入
                    conn.execute("""
                        INSERT OR IGNORE INTO offline_punches (
                            employee_id, punch_type, card_idm_hash,
                            timestamp, device_type, ip_address,
                            location_lat, location_lon, note,
                            created_at, data_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        punch_data.get('employee_id'),
                        punch_data.get('punch_type'),
                        punch_data.get('card_idm'),
                        punch_data.get('timestamp'),
                        punch_data.get('device_type'),
                        punch_data.get('ip_address'),
                        punch_data.get('location', {}).get('latitude'),
                        punch_data.get('location', {}).get('longitude'),
                        punch_data.get('note'),
                        datetime.now().isoformat(),
                        data_hash
                    ))
                    
                    conn.commit()
                    
                    logger.info(f"オフライン打刻をキューに追加: {data_hash[:8]}...")
                    return True
                    
        except sqlite3.IntegrityError:
            logger.warning("重複する打刻データのため、キューへの追加をスキップしました")
            return False
        except Exception as e:
            logger.error(f"オフラインキューへの追加エラー: {e}")
            return False
    
    def _generate_data_hash(self, punch_data: Dict[str, Any]) -> str:
        """データのハッシュ値を生成"""
        # 重要なフィールドのみを使用してハッシュを生成
        hash_source = f"{punch_data.get('card_idm')}:{punch_data.get('timestamp')}"
        return hashlib.sha256(hash_source.encode()).hexdigest()
    
    def get_pending_punches(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        保留中の打刻データを取得
        
        Args:
            limit: 取得件数制限
        
        Returns:
            List[Dict[str, Any]]: 打刻データリスト
        """
        if limit is None:
            limit = self.BATCH_SIZE
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT * FROM offline_punches 
                    WHERE retry_count < 5
                    ORDER BY created_at ASC 
                    LIMIT ?
                """, (limit,)).fetchall()
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"保留中の打刻データ取得エラー: {e}")
            return []
    
    def mark_as_synced(self, record_id: int) -> bool:
        """
        レコードを同期済みとしてマーク（削除）
        
        Args:
            record_id: レコードID
        
        Returns:
            bool: 成功/失敗
        """
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "DELETE FROM offline_punches WHERE id = ?",
                        (record_id,)
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"同期済みマークエラー: {e}")
            return False
    
    def update_retry_status(self, record_id: int, error_message: str) -> bool:
        """
        リトライ状態を更新
        
        Args:
            record_id: レコードID
            error_message: エラーメッセージ
        
        Returns:
            bool: 成功/失敗
        """
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE offline_punches 
                        SET retry_count = retry_count + 1,
                            last_retry_at = ?,
                            error_message = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(), error_message, record_id))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"リトライ状態更新エラー: {e}")
            return False
    
    def _cleanup_old_records(self):
        """古いレコードをクリーンアップ"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=self.RETENTION_DAYS)).isoformat()
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    deleted = conn.execute("""
                        DELETE FROM offline_punches 
                        WHERE created_at < ?
                    """, (cutoff_date,)).rowcount
                    
                    if deleted > 0:
                        conn.commit()
                        logger.info(f"{deleted}件の古いオフライン打刻をクリーンアップしました")
                        
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")
    
    def start_sync_thread(self, sync_callback):
        """
        同期スレッドを開始
        
        Args:
            sync_callback: 同期処理のコールバック関数
        """
        if self.is_running:
            logger.warning("同期スレッドは既に実行中です")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        def sync_loop():
            logger.info("オフライン同期スレッドを開始しました")
            last_notification_time = None
            
            while self.is_running and not self.stop_event.is_set():
                try:
                    # 保留中の打刻を取得
                    pending_punches = self.get_pending_punches()
                    
                    if pending_punches:
                        logger.info(f"{len(pending_punches)}件のオフライン打刻を同期します")
                        
                        success_count = 0
                        for punch in pending_punches:
                            try:
                                # コールバックで同期を試行
                                if sync_callback(punch):
                                    self.mark_as_synced(punch['id'])
                                    success_count += 1
                                else:
                                    self.update_retry_status(
                                        punch['id'], 
                                        "同期コールバックが失敗を返しました"
                                    )
                                    
                            except Exception as e:
                                error_msg = f"同期エラー: {str(e)}"
                                logger.error(error_msg)
                                self.update_retry_status(punch['id'], error_msg)
                        
                        if success_count > 0:
                            logger.info(f"{success_count}件の同期に成功しました")
                        
                        # 失敗が続く場合はSlack通知
                        failed_count = len(pending_punches) - success_count
                        if failed_count > 5:
                            current_time = datetime.now()
                            if (last_notification_time is None or 
                                current_time - last_notification_time > timedelta(hours=1)):
                                self._send_slack_notification(
                                    f"⚠️ オフライン打刻の同期エラー\n"
                                    f"{failed_count}件の打刻データが同期できません。"
                                )
                                last_notification_time = current_time
                    
                    # 定期的なクリーンアップ
                    if time.time() % 3600 < self.SYNC_INTERVAL:  # 1時間ごと
                        self._cleanup_old_records()
                    
                except Exception as e:
                    logger.error(f"同期ループエラー: {e}")
                
                # 次回同期まで待機
                self.stop_event.wait(self.SYNC_INTERVAL)
            
            logger.info("オフライン同期スレッドを停止しました")
        
        self.sync_thread = Thread(target=sync_loop, daemon=True)
        self.sync_thread.start()
    
    def stop_sync_thread(self):
        """同期スレッドを停止"""
        if not self.is_running:
            return
        
        logger.info("同期スレッドの停止を要求しました")
        self.is_running = False
        self.stop_event.set()
        
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
            if self.sync_thread.is_alive():
                logger.warning("同期スレッドの停止がタイムアウトしました")
    
    def _send_slack_notification(self, message: str):
        """Slack通知を送信"""
        if not self.slack_client:
            return
        
        try:
            self.slack_client.chat_postMessage(
                channel=config.SLACK_CHANNEL,
                text=message
            )
        except SlackApiError as e:
            logger.error(f"Slack通知エラー: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM offline_punches"
                ).fetchone()[0]
                
                failed = conn.execute(
                    "SELECT COUNT(*) FROM offline_punches WHERE retry_count >= 5"
                ).fetchone()[0]
                
                avg_retry = conn.execute(
                    "SELECT AVG(retry_count) FROM offline_punches"
                ).fetchone()[0] or 0
                
                oldest = conn.execute(
                    "SELECT MIN(created_at) FROM offline_punches"
                ).fetchone()[0]
                
                return {
                    "total_pending": total,
                    "failed_records": failed,
                    "average_retries": round(avg_retry, 2),
                    "oldest_record": oldest,
                    "queue_usage": f"{(total / self.MAX_QUEUE_SIZE) * 100:.1f}%"
                }
                
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """クリーンアップ"""
        self.stop_sync_thread()
        logger.info("オフラインキューマネージャーをクリーンアップしました")


# シングルトンインスタンス
offline_queue_manager = OfflineQueueManager()