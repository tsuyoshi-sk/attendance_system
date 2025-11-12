"""
RC-S380バックエンド実装

Sony RC-S380 (USB接続FeliCaリーダー) のサポート
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import nfc
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False

from .pasori_backend import PasoriBackend

logger = logging.getLogger(__name__)


@dataclass
class RC380Card:
    """RC-S380で読み取ったカード情報"""
    idm: bytes
    pmm: Optional[bytes] = None
    system_code: Optional[int] = None


class PasoriRCS380Backend(PasoriBackend):
    """RC-S380バックエンド実装"""
    
    # RC-S380のUSB識別子
    VENDOR_ID = 0x054c  # Sony
    PRODUCT_IDS = [0x06c1, 0x06c3]  # RC-S380/S, RC-S380/P
    
    def __init__(self):
        super().__init__()
        self.clf = None
        
        if not NFC_AVAILABLE:
            raise ImportError("nfcpy is not installed. Please install with: pip install nfcpy")
    
    def connect(self) -> bool:
        """RC-S380に接続"""
        try:
            # 各製品IDで接続を試行
            for product_id in self.PRODUCT_IDS:
                connection_string = f'usb:{self.VENDOR_ID:04x}:{product_id:04x}'
                try:
                    logger.debug(f"Trying to connect to RC-S380: {connection_string}")
                    self.clf = nfc.ContactlessFrontend(connection_string)
                    self.is_connected = True
                    logger.info(f"Successfully connected to RC-S380 ({connection_string})")
                    return True
                except Exception as e:
                    logger.debug(f"Failed to connect with {connection_string}: {e}")
                    continue
            
            # 汎用USB接続を試行
            try:
                self.clf = nfc.ContactlessFrontend('usb')
                self.is_connected = True
                logger.info("Connected to RC-S380 via generic USB")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to RC-S380: {e}")
                return False
                
        except Exception as e:
            logger.error(f"RC-S380 connection error: {e}")
            return False
    
    def disconnect(self):
        """RC-S380から切断"""
        if self.clf:
            try:
                self.clf.close()
                self.is_connected = False
                logger.info("Disconnected from RC-S380")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    def sense(self, timeout: float = 3.0) -> Optional[RC380Card]:
        """カードを検出"""
        if not self.is_connected or not self.clf:
            logger.error("RC-S380 is not connected")
            return None
        
        try:
            # カード検出のターゲット設定
            target = nfc.clf.RemoteTarget("212F")  # FeliCa
            target.sensf_req = bytearray.fromhex("0000000000")
            
            # タイムアウト付きでカード検出
            tag = self.clf.sense(target, iterations=int(timeout * 10), interval=0.1)
            
            if tag:
                card = RC380Card(
                    idm=tag.idm,
                    pmm=getattr(tag, 'pmm', None),
                    system_code=getattr(tag, 'sys', None)
                )
                logger.info(f"Card detected: IDm={tag.idm.hex()}")
                return card
            
            return None
            
        except Exception as e:
            logger.error(f"Error during card sensing: {e}")
            return None
    
    def get_device_info(self) -> Dict[str, str]:
        """デバイス情報を取得"""
        info = {
            "backend": "RC-S380",
            "vendor_id": f"0x{self.VENDOR_ID:04x}",
            "product_ids": [f"0x{pid:04x}" for pid in self.PRODUCT_IDS],
            "connected": str(self.is_connected)
        }
        
        if self.clf and hasattr(self.clf, 'device'):
            device = self.clf.device
            if hasattr(device, 'vendor_name'):
                info["vendor_name"] = device.vendor_name
            if hasattr(device, 'product_name'):
                info["product_name"] = device.product_name
            if hasattr(device, 'serial_number'):
                info["serial_number"] = device.serial_number
        
        return info