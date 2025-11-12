"""
モックバックエンド実装

テストおよび開発環境用のモックPaSoRi
"""

import logging
import time
import random
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .pasori_backend import PasoriBackend

logger = logging.getLogger(__name__)


@dataclass
class MockCard:
    """モックカード情報"""
    idm: bytes
    pmm: Optional[bytes] = None
    system_code: Optional[int] = None


class PasoriMockBackend(PasoriBackend):
    """モックバックエンド実装"""
    
    # テスト用のカード情報
    TEST_CARDS = [
        {
            "idm": "0123456789ABCDEF",
            "pmm": "0011223344556677",
            "system_code": 0x0003,  # Suica
            "name": "Test Suica Card"
        },
        {
            "idm": "FEDCBA9876543210",
            "pmm": "7766554433221100",
            "system_code": 0xFE00,  # Common area
            "name": "Test Common Card"
        },
        {
            "idm": "JE80F5250217373F",  # 実際のiPhone Suica IDm
            "pmm": "100B4B428485D0FF",
            "system_code": 0x0003,
            "name": "iPhone Suica (坂井毅史)"
        }
    ]
    
    def __init__(self):
        super().__init__()
        self.mock_card_index = 0
        self.last_detection_time = 0
        self.detection_interval = 3.0  # 同じカードの再検出防止時間
    
    def connect(self) -> bool:
        """モック接続（常に成功）"""
        self.is_connected = True
        logger.info("Connected to mock PaSoRi backend")
        return True
    
    def disconnect(self):
        """モック切断"""
        self.is_connected = False
        logger.info("Disconnected from mock PaSoRi backend")
    
    def sense(self, timeout: float = 3.0) -> Optional[MockCard]:
        """モックカード検出"""
        if not self.is_connected:
            logger.error("Mock PaSoRi is not connected")
            return None
        
        # タイムアウトのシミュレーション
        start_time = time.time()
        
        # ランダムな待機時間（0.5〜2秒）
        wait_time = random.uniform(0.5, min(2.0, timeout))
        time.sleep(wait_time)
        
        # タイムアウトチェック
        if time.time() - start_time >= timeout:
            logger.debug("Mock card detection timeout")
            return None
        
        # 30%の確率でカードを検出しない
        if random.random() < 0.3:
            logger.debug("Mock: No card detected")
            return None
        
        # 同じカードの連続検出を防ぐ
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_interval:
            logger.debug("Mock: Same card detection prevented")
            return None
        
        # テストカードから選択
        card_info = self.TEST_CARDS[self.mock_card_index]
        self.mock_card_index = (self.mock_card_index + 1) % len(self.TEST_CARDS)
        
        # カード情報を作成
        card = MockCard(
            idm=bytes.fromhex(card_info["idm"]),
            pmm=bytes.fromhex(card_info["pmm"]),
            system_code=card_info["system_code"]
        )
        
        self.last_detection_time = current_time
        logger.info(f"Mock card detected: {card_info['name']} (IDm={card_info['idm']})")
        
        return card
    
    def get_device_info(self) -> Dict[str, str]:
        """モックデバイス情報"""
        return {
            "backend": "Mock",
            "vendor_id": "0x0000",
            "product_id": "0x0000",
            "connected": str(self.is_connected),
            "mode": "development/testing",
            "available_cards": str(len(self.TEST_CARDS))
        }