"""
カードリーダーモジュール

PaSoRi RC-S300を使用したFeliCaカード読み取り機能を提供します。
"""

import logging
import time
import hashlib
from typing import Optional, Callable, Dict, Any
from threading import Thread, Event

try:
    import nfc
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False

from config.config import config


logger = logging.getLogger(__name__)


class CardReader:
    """カードリーダークラス"""
    
    def __init__(self, on_card_detected: Optional[Callable] = None):
        """
        初期化
        
        Args:
            on_card_detected: カード検出時のコールバック関数
        """
        self.clf = None
        self.on_card_detected = on_card_detected
        self.is_running = False
        self.stop_event = Event()
        self.reader_thread = None
        self.mock_mode = config.PASORI_MOCK_MODE or not NFC_AVAILABLE
        
        if self.mock_mode:
            logger.info("カードリーダーはモックモードで動作します")
    
    def connect(self) -> bool:
        """リーダーに接続"""
        if self.mock_mode:
            logger.info("モックモード: 仮想的にPaSoRiに接続しました")
            return True
        
        try:
            self.clf = nfc.ContactlessFrontend('usb')
            logger.info("PaSoRi RC-S300に接続しました")
            return True
        except Exception as e:
            logger.error(f"PaSoRiの接続に失敗しました: {e}")
            return False
    
    def disconnect(self):
        """接続を切断"""
        if self.clf and not self.mock_mode:
            try:
                self.clf.close()
                logger.info("PaSoRiとの接続を切断しました")
            except Exception as e:
                logger.error(f"切断中にエラーが発生しました: {e}")
    
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
        
        if self.mock_mode:
            # モックモードでは固定のカード情報を返す
            logger.info("モックモード: 仮想カードを読み取りました")
            return {
                "idm": "0123456789ABCDEF",
                "idm_hash": self.hash_idm("0123456789ABCDEF"),
                "pmm": "0011223344556677",
                "type": "FeliCa",
                "timestamp": time.time()
            }
        
        def on_connect(tag):
            return tag
        
        start_time = time.time()
        
        try:
            tag = self.clf.connect(
                rdwr={'on-connect': on_connect},
                terminate=lambda: time.time() - start_time > timeout
            )
            
            if tag:
                return self._process_tag(tag)
            else:
                logger.debug("タイムアウト: カードが検出されませんでした")
                return None
                
        except Exception as e:
            logger.error(f"カード読み取り中にエラーが発生しました: {e}")
            return None
    
    def _process_tag(self, tag) -> Dict[str, Any]:
        """タグ情報を処理"""
        idm = tag.idm.hex().upper() if hasattr(tag, 'idm') else None
        
        if not idm:
            logger.error("IDmが取得できませんでした")
            return None
        
        card_info = {
            "idm": idm,
            "idm_hash": self.hash_idm(idm),
            "pmm": tag.pmm.hex().upper() if hasattr(tag, 'pmm') else None,
            "type": tag.type if hasattr(tag, 'type') else "Unknown",
            "timestamp": time.time()
        }
        
        logger.info(f"カード検出: IDm={idm[:8]}...")
        return card_info
    
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