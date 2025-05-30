"""
PaSoRi抽象化レイヤー

RC-S380/RC-S300の両方に対応するプラグイン式実装
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Protocol
import os
import logging

logger = logging.getLogger(__name__)


class Card(Protocol):
    """カード情報のプロトコル"""
    idm: bytes
    pmm: Optional[bytes]
    system_code: Optional[int]


class PasoriBackend(ABC):
    """PaSoRiバックエンドの抽象基底クラス"""
    
    def __init__(self):
        self.device = None
        self.is_connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """デバイスに接続"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """デバイスから切断"""
        pass
    
    @abstractmethod
    def sense(self, timeout: float = 3.0) -> Optional[Card]:
        """カードを検出"""
        pass
    
    @abstractmethod
    def get_device_info(self) -> Dict[str, str]:
        """デバイス情報を取得"""
        pass


def get_pasori_backend(device_type: Optional[str] = None) -> PasoriBackend:
    """
    環境変数またはパラメータに基づいて適切なバックエンドを返す
    
    Args:
        device_type: "rcs380", "rcs300", "mock" のいずれか
        
    Returns:
        PasoriBackend: 適切なバックエンドインスタンス
    """
    if device_type is None:
        device_type = os.getenv("PASORI_DEVICE", "auto").lower()
    
    # モックモード
    if device_type == "mock" or os.getenv("PASORI_MOCK_MODE", "false").lower() == "true":
        from .pasori_mock import PasoriMockBackend
        logger.info("Using mock PaSoRi backend")
        return PasoriMockBackend()
    
    # 自動検出モード
    if device_type == "auto":
        try:
            # RC-S380を優先的に試行
            from .pasori_rcs380 import PasoriRCS380Backend
            backend = PasoriRCS380Backend()
            if backend.connect():
                logger.info("Auto-detected RC-S380")
                backend.disconnect()
                return backend
        except Exception as e:
            logger.debug(f"RC-S380 not available: {e}")
        
        try:
            # RC-S300をフォールバック
            from .pasori_rcs300 import PasoriRCS300Backend
            backend = PasoriRCS300Backend()
            if backend.connect():
                logger.info("Auto-detected RC-S300")
                backend.disconnect()
                return backend
        except Exception as e:
            logger.debug(f"RC-S300 not available: {e}")
        
        # デバイスが見つからない場合はモックにフォールバック
        logger.warning("No PaSoRi device found, falling back to mock")
        from .pasori_mock import PasoriMockBackend
        return PasoriMockBackend()
    
    # 明示的な指定
    if device_type == "rcs380":
        from .pasori_rcs380 import PasoriRCS380Backend
        return PasoriRCS380Backend()
    elif device_type == "rcs300":
        from .pasori_rcs300 import PasoriRCS300Backend
        return PasoriRCS300Backend()
    else:
        raise ValueError(f"Unknown device type: {device_type}")