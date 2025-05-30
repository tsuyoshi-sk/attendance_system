#!/usr/bin/env python3
"""
RC-S380 iPhone Suica対応勤怠管理システム
エンタープライズレベルのセキュリティと機能を完備
"""

import nfc
import sqlite3
import hashlib
import logging
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from enum import Enum
import time
import threading
from queue import Queue
import signal

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rc_s380_attendance.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 打刻タイプ
class PunchType(Enum):
    IN = "IN"           # 出勤
    OUT = "OUT"         # 退勤
    OUTSIDE = "OUTSIDE" # 外出
    RETURN = "RETURN"   # 戻り

# システム設定
class Config:
    # データベース
    DB_PATH = "attendance.db"
    
    # セキュリティ
    HASH_ALGORITHM = "sha256"
    
    # ビジネスルール
    DUPLICATE_PREVENTION_MINUTES = 3  # 重複防止時間（分）
    OFFLINE_QUEUE_MAX_SIZE = 100     # オフライン時の最大保持件数
    OFFLINE_RETENTION_DAYS = 7       # オフライン記録保持日数
    
    # RC-S380設定
    RC_S380_VENDOR_ID = "054c"
    RC_S380_PRODUCT_IDS = ["06c1", "06c3"]  # RC-S380/S, RC-S380/P
    READ_TIMEOUT = 3  # カード読み取りタイムアウト（秒）
    
    # フィードバック
    ENABLE_SOUND = True
    ENABLE_LED = True

class SecurityManager:
    """セキュリティ機能を管理するクラス"""
    
    @staticmethod
    def hash_idm(idm: str) -> str:
        """IDmをSHA-256でハッシュ化"""
        return hashlib.sha256(idm.encode()).hexdigest()
    
    @staticmethod
    def validate_idm(idm: str) -> bool:
        """IDmの形式を検証"""
        # 16文字の16進数文字列であることを確認
        if len(idm) != 16:
            return False
        try:
            int(idm, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def check_card_authenticity(tag) -> bool:
        """カードの真正性を確認（偽造検出）"""
        # 基本的な検証（実際はより高度な検証が必要）
        if not hasattr(tag, 'identifier'):
            return False
        
        # Felica/Suicaのシステムコードを確認
        if hasattr(tag, 'system_code'):
            # Suicaのシステムコード: 0x0003
            if tag.system_code not in [0x0003, 0xFE00]:
                logger.warning(f"不正なシステムコード: {hex(tag.system_code)}")
                return False
        
        return True

class OfflineQueueManager:
    """オフライン時の打刻データを管理するクラス"""
    
    def __init__(self):
        self.queue = Queue(maxsize=Config.OFFLINE_QUEUE_MAX_SIZE)
        self.offline_db_path = "offline_punch_queue.db"
        self._init_offline_db()
    
    def _init_offline_db(self):
        """オフライン用データベースの初期化"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_punches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                punch_type TEXT NOT NULL,
                punch_time DATETIME NOT NULL,
                device_id TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def add_punch(self, punch_data: Dict[str, Any]):
        """オフライン打刻をキューに追加"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offline_punches (employee_id, punch_type, punch_time, device_id)
            VALUES (?, ?, ?, ?)
        """, (
            punch_data['employee_id'],
            punch_data['punch_type'],
            punch_data['punch_time'],
            punch_data['device_id']
        ))
        conn.commit()
        conn.close()
        logger.info(f"オフライン打刻を保存: {punch_data}")
    
    def process_offline_queue(self):
        """オフラインキューを処理"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # 保持期限を過ぎたレコードを削除
        retention_date = datetime.now() - timedelta(days=Config.OFFLINE_RETENTION_DAYS)
        cursor.execute("""
            DELETE FROM offline_punches WHERE created_at < ?
        """, (retention_date,))
        
        # 未処理のレコードを取得
        cursor.execute("""
            SELECT id, employee_id, punch_type, punch_time, device_id
            FROM offline_punches
            ORDER BY punch_time ASC
        """)
        
        offline_records = cursor.fetchall()
        conn.close()
        
        return offline_records

class AnomalyDetector:
    """異常打刻パターン検出システム"""
    
    def __init__(self):
        self.patterns = {
            'consecutive_punch': self._check_consecutive_punch,
            'unusual_time': self._check_unusual_time,
            'missing_punch': self._check_missing_punch,
            'long_working_hours': self._check_long_working_hours
        }
    
    def detect_anomalies(self, employee_id: int, punch_type: str, 
                        punch_time: datetime, conn: sqlite3.Connection) -> Dict[str, Any]:
        """異常パターンを検出"""
        anomalies = []
        
        for pattern_name, check_func in self.patterns.items():
            result = check_func(employee_id, punch_type, punch_time, conn)
            if result:
                anomalies.append({
                    'pattern': pattern_name,
                    'details': result
                })
        
        return anomalies
    
    def _check_consecutive_punch(self, employee_id: int, punch_type: str,
                                punch_time: datetime, conn: sqlite3.Connection) -> Optional[str]:
        """連続同一打刻のチェック"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT punch_type, punch_time
            FROM punch_records
            WHERE employee_id = ?
            ORDER BY punch_time DESC
            LIMIT 1
        """, (employee_id,))
        
        last_record = cursor.fetchone()
        if last_record and last_record[0] == punch_type:
            return f"連続して同じタイプ({punch_type})の打刻が検出されました"
        
        return None
    
    def _check_unusual_time(self, employee_id: int, punch_type: str,
                          punch_time: datetime, conn: sqlite3.Connection) -> Optional[str]:
        """異常時刻のチェック"""
        hour = punch_time.hour
        
        # 深夜・早朝の打刻をチェック
        if punch_type == "IN" and (hour < 5 or hour > 22):
            return f"通常外の出勤時刻です: {punch_time.strftime('%H:%M')}"
        elif punch_type == "OUT" and (hour < 5 or hour > 23):
            return f"通常外の退勤時刻です: {punch_time.strftime('%H:%M')}"
        
        return None
    
    def _check_missing_punch(self, employee_id: int, punch_type: str,
                           punch_time: datetime, conn: sqlite3.Connection) -> Optional[str]:
        """打刻漏れのチェック"""
        cursor = conn.cursor()
        
        # 今日の打刻履歴を取得
        today = punch_time.date()
        cursor.execute("""
            SELECT punch_type, punch_time
            FROM punch_records
            WHERE employee_id = ? AND DATE(punch_time) = ?
            ORDER BY punch_time ASC
        """, (employee_id, today))
        
        punches = cursor.fetchall()
        
        # INがないのにOUTしようとしている場合
        if punch_type == "OUT" and not any(p[0] == "IN" for p in punches):
            return "出勤打刻がありません"
        
        return None
    
    def _check_long_working_hours(self, employee_id: int, punch_type: str,
                                 punch_time: datetime, conn: sqlite3.Connection) -> Optional[str]:
        """長時間労働のチェック"""
        if punch_type != "OUT":
            return None
        
        cursor = conn.cursor()
        
        # 今日の最初のIN打刻を取得
        today = punch_time.date()
        cursor.execute("""
            SELECT punch_time
            FROM punch_records
            WHERE employee_id = ? AND DATE(punch_time) = ? AND punch_type = 'IN'
            ORDER BY punch_time ASC
            LIMIT 1
        """, (employee_id, today))
        
        first_in = cursor.fetchone()
        if first_in:
            working_hours = (punch_time - datetime.fromisoformat(first_in[0])).total_seconds() / 3600
            if working_hours > 12:
                return f"長時間労働の可能性があります: {working_hours:.1f}時間"
        
        return None

class RC_S380AttendanceSystem:
    """RC-S380を使用した勤怠管理システムのメインクラス"""
    
    def __init__(self):
        self.clf = None
        self.security_manager = SecurityManager()
        self.offline_queue = OfflineQueueManager()
        self.anomaly_detector = AnomalyDetector()
        self.is_running = False
        
        # シグナルハンドラーの設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """終了シグナルのハンドラー"""
        logger.info("終了シグナルを受信しました")
        self.stop()
    
    def connect_reader(self) -> bool:
        """RC-S380への接続"""
        try:
            # RC-S380の接続を試行
            for product_id in Config.RC_S380_PRODUCT_IDS:
                connection_string = f'usb:{Config.RC_S380_VENDOR_ID}:{product_id}'
                try:
                    self.clf = nfc.ContactlessFrontend(connection_string)
                    logger.info(f"✅ RC-S380接続成功: {connection_string}")
                    return True
                except:
                    continue
            
            logger.error("❌ RC-S380の接続に失敗しました")
            return False
            
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            return False
    
    def on_card_connect(self, tag) -> bool:
        """カード検出時の処理"""
        try:
            # カードの真正性チェック
            if not self.security_manager.check_card_authenticity(tag):
                logger.warning("⚠️ 不正なカードが検出されました")
                self._provide_feedback("error")
                return True
            
            # IDmの取得
            if hasattr(tag, 'identifier'):
                idm = tag.identifier.hex().upper()
                logger.info(f"📱 カード検出: IDm={idm}")
                
                # IDmの検証
                if not self.security_manager.validate_idm(idm):
                    logger.error("❌ 無効なIDm形式")
                    self._provide_feedback("error")
                    return True
                
                # 打刻処理
                self.process_attendance(idm)
                
            else:
                logger.error("❌ IDmを取得できません")
                self._provide_feedback("error")
                
        except Exception as e:
            logger.error(f"カード処理エラー: {e}")
            self._provide_feedback("error")
        
        return True
    
    def process_attendance(self, idm: str):
        """勤怠打刻処理"""
        try:
            # IDmのハッシュ化
            hashed_idm = self.security_manager.hash_idm(idm)
            
            # データベース接続
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            # 従業員情報の取得
            cursor.execute("""
                SELECT id, name, employee_code, department
                FROM employees
                WHERE card_idm_hash = ?
            """, (hashed_idm,))
            
            employee = cursor.fetchone()
            
            if not employee:
                logger.warning(f"⚠️ 未登録のカード: {idm}")
                self._provide_feedback("unregistered")
                conn.close()
                return
            
            employee_id, name, emp_code, department = employee
            
            # 重複防止チェック
            if self._check_duplicate_punch(employee_id, conn):
                logger.warning(f"⚠️ {name}さん: 重複打刻を防止しました")
                self._provide_feedback("duplicate")
                conn.close()
                return
            
            # 打刻タイプの決定
            punch_type = self._determine_punch_type(employee_id, conn)
            
            # 異常パターン検出
            anomalies = self.anomaly_detector.detect_anomalies(
                employee_id, punch_type, datetime.now(), conn
            )
            
            if anomalies:
                logger.warning(f"⚠️ 異常パターン検出: {anomalies}")
                # 異常があっても記録は続行（アラートのみ）
            
            # 打刻記録の保存
            try:
                cursor.execute("""
                    INSERT INTO punch_records (
                        employee_id, punch_type, punch_time,
                        device_type, device_id, is_offline, is_modified, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    employee_id, punch_type, datetime.now(),
                    'iPhone_Suica_RC-S380', idm, False, False, datetime.now()
                ))
                
                conn.commit()
                
                logger.info(f"✅ {name}さん ({emp_code}) - {department}部 の{punch_type}を記録しました")
                self._provide_feedback("success", punch_type)
                
                # 統計情報の更新
                self._update_statistics(employee_id, punch_type, conn)
                
            except sqlite3.Error as e:
                logger.error(f"データベースエラー: {e}")
                # オフラインキューに保存
                self.offline_queue.add_punch({
                    'employee_id': employee_id,
                    'punch_type': punch_type,
                    'punch_time': datetime.now(),
                    'device_id': idm
                })
                self._provide_feedback("offline")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"打刻処理エラー: {e}")
            self._provide_feedback("error")
    
    def _check_duplicate_punch(self, employee_id: int, conn: sqlite3.Connection) -> bool:
        """重複打刻のチェック"""
        cursor = conn.cursor()
        
        # 指定時間内の打刻をチェック
        time_threshold = datetime.now() - timedelta(minutes=Config.DUPLICATE_PREVENTION_MINUTES)
        
        cursor.execute("""
            SELECT COUNT(*) FROM punch_records
            WHERE employee_id = ? AND punch_time > ?
        """, (employee_id, time_threshold))
        
        count = cursor.fetchone()[0]
        return count > 0
    
    def _determine_punch_type(self, employee_id: int, conn: sqlite3.Connection) -> str:
        """打刻タイプの決定"""
        cursor = conn.cursor()
        
        # 今日の最新の打刻を取得
        today = datetime.now().date()
        cursor.execute("""
            SELECT punch_type
            FROM punch_records
            WHERE employee_id = ? AND DATE(punch_time) = ?
            ORDER BY punch_time DESC
            LIMIT 1
        """, (employee_id, today))
        
        last_punch = cursor.fetchone()
        
        if not last_punch:
            return PunchType.IN.value
        
        # 状態遷移ロジック
        transitions = {
            PunchType.IN.value: PunchType.OUT.value,
            PunchType.OUT.value: PunchType.IN.value,
            PunchType.OUTSIDE.value: PunchType.RETURN.value,
            PunchType.RETURN.value: PunchType.OUT.value
        }
        
        return transitions.get(last_punch[0], PunchType.IN.value)
    
    def _update_statistics(self, employee_id: int, punch_type: str, conn: sqlite3.Connection):
        """統計情報の更新"""
        cursor = conn.cursor()
        
        # 日次サマリーの更新
        today = datetime.now().date()
        
        if punch_type == PunchType.IN.value:
            # 出勤時刻の記録
            cursor.execute("""
                INSERT OR REPLACE INTO daily_summaries (
                    employee_id, date, first_punch_in, created_at
                ) VALUES (
                    ?, ?, ?,
                    COALESCE((SELECT created_at FROM daily_summaries 
                             WHERE employee_id = ? AND date = ?), ?)
                )
            """, (employee_id, today, datetime.now(), employee_id, today, datetime.now()))
            
        elif punch_type == PunchType.OUT.value:
            # 退勤時刻と労働時間の計算
            cursor.execute("""
                UPDATE daily_summaries
                SET last_punch_out = ?, 
                    total_work_hours = (
                        SELECT ROUND((julianday(?) - julianday(first_punch_in)) * 24, 2)
                    )
                WHERE employee_id = ? AND date = ?
            """, (datetime.now(), datetime.now(), employee_id, today))
        
        conn.commit()
    
    def _provide_feedback(self, status: str, punch_type: str = None):
        """ユーザーへのフィードバック"""
        feedback_messages = {
            'success': {
                PunchType.IN.value: "🎵 おはようございます！出勤を記録しました",
                PunchType.OUT.value: "🎵 お疲れ様でした！退勤を記録しました",
                PunchType.OUTSIDE.value: "🎵 外出を記録しました",
                PunchType.RETURN.value: "🎵 戻りを記録しました"
            },
            'error': "❌ エラーが発生しました",
            'unregistered': "⚠️ 未登録のカードです",
            'duplicate': "⚠️ 既に打刻済みです",
            'offline': "📴 オフラインモードで保存しました"
        }
        
        if status == 'success' and punch_type:
            message = feedback_messages['success'].get(punch_type, "✅ 打刻を記録しました")
        else:
            message = feedback_messages.get(status, "処理完了")
        
        print(f"\n{message}\n")
        
        # 音声フィードバック（macOSの場合）
        if Config.ENABLE_SOUND and sys.platform == 'darwin':
            if status == 'success':
                os.system('afplay /System/Library/Sounds/Glass.aiff')
            else:
                os.system('afplay /System/Library/Sounds/Basso.aiff')
    
    def process_offline_punches(self):
        """オフライン打刻の処理"""
        logger.info("オフライン打刻の処理を開始します...")
        
        offline_records = self.offline_queue.process_offline_queue()
        processed_count = 0
        
        for record_id, employee_id, punch_type, punch_time, device_id in offline_records:
            try:
                conn = sqlite3.connect(Config.DB_PATH)
                cursor = conn.cursor()
                
                # オンラインに同期
                cursor.execute("""
                    INSERT INTO punch_records (
                        employee_id, punch_type, punch_time,
                        device_type, device_id, is_offline, is_modified, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    employee_id, punch_type, punch_time,
                    'iPhone_Suica_RC-S380', device_id, True, False, datetime.now()
                ))
                
                conn.commit()
                conn.close()
                
                # オフラインキューから削除
                offline_conn = sqlite3.connect(self.offline_queue.offline_db_path)
                offline_cursor = offline_conn.cursor()
                offline_cursor.execute("DELETE FROM offline_punches WHERE id = ?", (record_id,))
                offline_conn.commit()
                offline_conn.close()
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"オフライン打刻の同期エラー: {e}")
        
        if processed_count > 0:
            logger.info(f"✅ {processed_count}件のオフライン打刻を同期しました")
    
    def start(self):
        """システムの起動"""
        logger.info("🚀 RC-S380 iPhone Suica勤怠管理システムを起動します...")
        
        # データベースの確認
        if not os.path.exists(Config.DB_PATH):
            logger.error("❌ データベースが見つかりません")
            return
        
        # リーダーの接続
        if not self.connect_reader():
            return
        
        # オフライン打刻の処理
        self.process_offline_punches()
        
        self.is_running = True
        
        print("\n" + "="*60)
        print("🏢 RC-S380 iPhone Suica勤怠管理システム")
        print("="*60)
        print("📱 iPhone Suicaをリーダーにかざしてください...")
        print("終了: Ctrl+C")
        print("="*60 + "\n")
        
        # メインループ
        try:
            while self.is_running:
                try:
                    # タイムアウト付きでカード読み取り
                    self.clf.connect(
                        rdwr={
                            'on-connect': self.on_card_connect,
                            'on-release': lambda tag: logger.debug("カードが離れました")
                        },
                        terminate=lambda: not self.is_running
                    )
                except nfc.clf.TimeoutError:
                    # タイムアウトは正常動作
                    pass
                except Exception as e:
                    logger.error(f"読み取りエラー: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("キーボード割り込みを検出")
        finally:
            self.stop()
    
    def stop(self):
        """システムの停止"""
        logger.info("システムを停止します...")
        self.is_running = False
        
        if self.clf:
            try:
                self.clf.close()
                logger.info("RC-S380との接続を切断しました")
            except:
                pass
        
        logger.info("👋 システムを終了しました")

def main():
    """メイン関数"""
    # ログディレクトリの作成
    os.makedirs('logs', exist_ok=True)
    
    # システムの起動
    system = RC_S380AttendanceSystem()
    system.start()

if __name__ == "__main__":
    main()