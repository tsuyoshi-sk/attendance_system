"""
RC-S300バックエンド実装

Sony RC-S300 (USB接続FeliCaリーダー) のサポート
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
class RC300Card:
    """RC-S300で読み取ったカード情報"""
    idm: bytes
    pmm: Optional[bytes] = None
    system_code: Optional[int] = None


class PasoriRCS300Backend(PasoriBackend):
    """RC-S300バックエンド実装"""
    
    # RC-S300のUSB識別子
    VENDOR_ID = 0x054c  # Sony
    PRODUCT_ID = 0x0dc9  # RC-S300
    
    def __init__(self):
        super().__init__()
        self.clf = None
        
        if not NFC_AVAILABLE:
            raise ImportError("nfcpy is not installed. Please install with: pip install nfcpy")
    
    def connect(self) -> bool:
        """RC-S300に接続"""
        try:
            connection_string = f'usb:{self.VENDOR_ID:04x}:{self.PRODUCT_ID:04x}'
            logger.debug(f"Trying to connect to RC-S300: {connection_string}")
            
            self.clf = nfc.ContactlessFrontend(connection_string)
            self.is_connected = True
            logger.info(f"Successfully connected to RC-S300")
            return True
            
        except Exception as e:
            logger.error(f"RC-S300 connection error: {e}")
            logger.info("Note: RC-S300 may have limited support on macOS. Consider using RC-S380.")
            return False
    
    def disconnect(self):
        """RC-S300から切断"""
        if self.clf:
            try:
                self.clf.close()
                self.is_connected = False
                logger.info("Disconnected from RC-S300")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    def sense(self, timeout: float = 3.0) -> Optional[RC300Card]:
        """カードを検出"""
        if not self.is_connected or not self.clf:
            logger.error("RC-S300 is not connected")
            return None
        
        try:
            # カード検出のターゲット設定
            target = nfc.clf.RemoteTarget("212F")  # FeliCa
            target.sensf_req = bytearray.fromhex("0000000000")
            
            # タイムアウト付きでカード検出
            tag = self.clf.sense(target, iterations=int(timeout * 10), interval=0.1)
            
            if tag:
                card = RC300Card(
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
            "backend": "RC-S300",
            "vendor_id": f"0x{self.VENDOR_ID:04x}",
            "product_id": f"0x{self.PRODUCT_ID:04x}",
            "connected": str(self.is_connected),
            "note": "Limited macOS support. RC-S380 recommended for macOS."
        }
        
        if self.clf and hasattr(self.clf, 'device'):
            device = self.clf.device
            if hasattr(device, 'vendor_name'):
                info["vendor_name"] = device.vendor_name
            if hasattr(device, 'product_name'):
                info["product_name"] = device.product_name
        
        return info