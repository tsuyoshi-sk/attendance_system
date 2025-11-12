"""
カードリーダーモジュール

PaSoRi RC-S380/RC-S300を使用したFeliCaカード読み取り機能を提供します。
RC-S380がmacOSでの推奨モデルです。
"""

import logging
import time
import hashlib
import os
from typing import Optional, Callable, Dict, Any, List
from threading import Thread, Event

try:
    import nfc
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False

from config.config import config


logger = logging.getLogger(__name__)

# PaSoRiデバイスID設定（環境変数で上書き可能）
PASORI_DEVICE_ID = os.getenv("PASORI_DEVICE_ID", "usb:054c:0dc9")  # デフォルト: RC-S300

# フォールバックデバイスリスト（RC-S380優先）
PASORI_FALLBACKS = [
    "usb:054c:06c1",  # RC-S380/S
    "usb:054c:06c3",  # RC-S380/P
    "usb:054c:0dc9",  # RC-S300
    "usb"             # 任意のUSBデバイス
]


class CardReaderError(Exception):
    """カードリーダー関連のエラー"""
    pass


class CardReaderConnectionError(CardReaderError):
    """接続エラー"""
    pass


class CardReaderTimeoutError(CardReaderError):
    """タイムアウトエラー"""
    pass


class CardReader:
    """カードリーダークラス"""
    
    def __init__(self, on_card_detected: Optional[Callable] = None):
        """
        初期化
        
        Args:
            on_card_detected: カード検出時のコールバック関数
        """
        self.backend = None
        self.on_card_detected = on_card_detected
        self.is_running = False
        self.stop_event = Event()
        self.reader_thread = None
        
        # バックエンドの初期化
        from .pasori_backend import get_pasori_backend
        self.backend = get_pasori_backend()
    
    def connect(self) -> bool:
        """リーダーに接続"""
        if self.backend:
            success = self.backend.connect()
            if success:
                device_info = self.backend.get_device_info()
                logger.info(f"Connected to {device_info.get('backend', 'Unknown')} reader")
                logger.debug(f"Device info: {device_info}")
            return success
        return False
    
    def disconnect(self):
        """接続を切断"""
        if self.backend:
            self.backend.disconnect()
    
    def read_card_once(self, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        カードを1回読み取る
        
        Args:
            timeout: タイムアウト時間（秒）
        
        Returns:
            Optional[Dict[str, Any]]: カード情報
        """
        if timeout is None:
            timeout = config.PASORI_TIMEOUT
        
        if not self.backend:
            logger.error("Backend not initialized")
            return None
        
        try:
            card = self.backend.sense(timeout=float(timeout))
            
            if card:
                idm = card.idm.hex().upper()
                return {
                    "idm": idm,
                    "idm_hash": self.hash_idm(idm),
                    "pmm": card.pmm.hex().upper() if card.pmm else None,
                    "system_code": card.system_code,
                    "type": "FeliCa",
                    "timestamp": time.time()
                }
            else:
                logger.debug("タイムアウト: カードが検出されませんでした")
                return None
                
        except Exception as e:
            logger.error(f"カード読み取り中にエラーが発生しました: {e}")
            return None
    
    
    def hash_idm(self, idm: str) -> str:
        """IDmをハッシュ化"""
        return hashlib.sha256(
            f"{idm}{config.IDM_HASH_SECRET}".encode()
        ).hexdigest()
    
    def start_polling(self, interval: float = 1.0):
        """
        ポーリングを開始
        
        Args:
            interval: ポーリング間隔（秒）
        """
        if self.is_running:
            logger.warning("ポーリングは既に実行中です")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        def polling_loop():
            logger.info("カードポーリングを開始しました")
            last_idm = None
            last_detection_time = 0
            
            while self.is_running and not self.stop_event.is_set():
                try:
                    card_info = self.read_card_once(timeout=1)
                    
                    if card_info:
                        current_time = time.time()
                        # 同じカードの連続検出を防ぐ（3秒間）
                        if (card_info['idm'] != last_idm or 
                            current_time - last_detection_time > 3):
                            
                            last_idm = card_info['idm']
                            last_detection_time = current_time
                            
                            # コールバック実行
                            if self.on_card_detected:
                                try:
                                    self.on_card_detected(card_info)
                                except Exception as e:
                                    logger.error(f"コールバック実行中にエラー: {e}")
                    
                    # インターバル待機
                    self.stop_event.wait(interval)
                    
                except Exception as e:
                    logger.error(f"ポーリング中にエラーが発生しました: {e}")
                    self.stop_event.wait(interval)
            
            logger.info("カードポーリングを停止しました")
        
        self.reader_thread = Thread(target=polling_loop, daemon=True)
        self.reader_thread.start()
    
    def stop_polling(self):
        """ポーリングを停止"""
        if not self.is_running:
            return
        
        logger.info("ポーリング停止を要求しました")
        self.is_running = False
        self.stop_event.set()
        
        if self.reader_thread:
            self.reader_thread.join(timeout=5)
            if self.reader_thread.is_alive():
                logger.warning("ポーリングスレッドの停止がタイムアウトしました")


class CardReaderManager:
    """カードリーダー管理クラス"""
    
    def __init__(self):
        self.reader = None
        self.is_initialized = False
    
    def initialize(self, on_card_detected: Optional[Callable] = None) -> bool:
        """
        初期化
        
        Args:
            on_card_detected: カード検出時のコールバック
        
        Returns:
            bool: 成功/失敗
        """
        if self.is_initialized:
            logger.warning("既に初期化されています")
            return True
        
        self.reader = CardReader(on_card_detected)
        
        if self.reader.connect():
            self.is_initialized = True
            logger.info("カードリーダーマネージャーを初期化しました")
            return True
        else:
            logger.error("カードリーダーの初期化に失敗しました")
            return False
    
    def start(self):
        """ポーリング開始"""
        if not self.is_initialized:
            logger.error("初期化されていません")
            return
        
        self.reader.start_polling()
    
    def stop(self):
        """ポーリング停止"""
        if not self.is_initialized:
            return
        
        self.reader.stop_polling()
    
    def cleanup(self):
        """クリーンアップ"""
        if self.reader:
            self.reader.stop_polling()
            self.reader.disconnect()
            self.is_initialized = False
            logger.info("カードリーダーマネージャーをクリーンアップしました")


# シングルトンインスタンス
card_reader_manager = CardReaderManager()