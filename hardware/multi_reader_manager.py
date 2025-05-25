"""
複数カードリーダー管理システム

複数のPaSoRiデバイスを管理し、フェイルオーバーと負荷分散を実現します。
"""

import asyncio
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import nfc
import usb.core
import usb.util

logger = logging.getLogger(__name__)


class ReaderDevice:
    """個別のカードリーダーデバイス"""
    
    def __init__(self, device_id: str, usb_path: str):
        self.device_id = device_id
        self.usb_path = usb_path
        self.is_active = False
        self.last_read_time = None
        self.read_count = 0
        self.error_count = 0
        self.clf = None
        self._lock = threading.Lock()
    
    def connect(self) -> bool:
        """デバイスに接続"""
        try:
            self.clf = nfc.ContactlessFrontend(self.usb_path)
            self.is_active = True
            logger.info(f"Connected to reader {self.device_id} at {self.usb_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to reader {self.device_id}: {str(e)}")
            self.is_active = False
            return False
    
    def disconnect(self):
        """デバイスから切断"""
        if self.clf:
            try:
                self.clf.close()
            except:
                pass
            self.clf = None
        self.is_active = False
    
    def read_card(self, timeout: float = 3.0) -> Optional[str]:
        """カードを読み取り"""
        if not self.is_active or not self.clf:
            return None
        
        with self._lock:
            try:
                target = self.clf.sense(
                    nfc.clf.RemoteTarget("212F"),
                    iterations=int(timeout * 10),
                    interval=0.1
                )
                
                if target:
                    tag = nfc.tag.activate(self.clf, target)
                    if tag:
                        self.last_read_time = datetime.now()
                        self.read_count += 1
                        return tag.identifier.hex().upper()
                
                return None
                
            except Exception as e:
                logger.error(f"Read error on device {self.device_id}: {str(e)}")
                self.error_count += 1
                if self.error_count > 5:
                    self.is_active = False
                return None
    
    def get_health_score(self) -> float:
        """デバイスの健全性スコアを計算（0.0-1.0）"""
        if not self.is_active:
            return 0.0
        
        # エラー率による減点
        error_rate = self.error_count / max(self.read_count + self.error_count, 1)
        error_score = max(0, 1 - error_rate * 2)
        
        # 最終使用からの経過時間による減点
        if self.last_read_time:
            idle_minutes = (datetime.now() - self.last_read_time).total_seconds() / 60
            idle_score = max(0, 1 - idle_minutes / 60)  # 1時間で0になる
        else:
            idle_score = 0.5
        
        return (error_score * 0.7 + idle_score * 0.3)


class MultiReaderManager:
    """複数PaSoRiデバイス管理"""
    
    def __init__(self):
        self.readers: Dict[str, ReaderDevice] = {}
        self.primary_reader: Optional[ReaderDevice] = None
        self.backup_readers: List[ReaderDevice] = []
        self._initialization_complete = False
        self._monitor_task = None
        self._read_tasks: Dict[str, asyncio.Task] = {}
    
    async def initialize_readers(self) -> Dict[str, any]:
        """
        利用可能な全リーダーを初期化
        
        Returns:
            初期化結果
        """
        logger.info("Initializing multiple card readers...")
        
        # USB接続されているPaSoRiデバイスを検出
        detected_devices = self._detect_pasori_devices()
        
        if not detected_devices:
            logger.warning("No PaSoRi devices detected")
            return {
                "success": False,
                "message": "No card readers found",
                "device_count": 0
            }
        
        # 各デバイスを初期化
        successful_readers = []
        for device_info in detected_devices:
            device_id = device_info["id"]
            usb_path = device_info["path"]
            
            reader = ReaderDevice(device_id, usb_path)
            if reader.connect():
                self.readers[device_id] = reader
                successful_readers.append(device_id)
                logger.info(f"Successfully initialized reader: {device_id}")
            else:
                logger.error(f"Failed to initialize reader: {device_id}")
        
        if not successful_readers:
            return {
                "success": False,
                "message": "Failed to initialize any readers",
                "device_count": 0
            }
        
        # プライマリとバックアップを設定
        self._assign_reader_roles()
        
        # 監視タスクを開始
        self._monitor_task = asyncio.create_task(self._monitor_devices())
        
        self._initialization_complete = True
        
        return {
            "success": True,
            "message": f"Initialized {len(successful_readers)} readers",
            "device_count": len(successful_readers),
            "primary": self.primary_reader.device_id if self.primary_reader else None,
            "backups": [r.device_id for r in self.backup_readers]
        }
    
    def _detect_pasori_devices(self) -> List[Dict[str, str]]:
        """PaSoRiデバイスを検出"""
        devices = []
        
        # Sony RC-S300/S330/S370/S380 のベンダーID
        SONY_VENDOR_ID = 0x054c
        PASORI_PRODUCT_IDS = [0x01bb, 0x02e1, 0x06c1, 0x06c3]
        
        try:
            # USB デバイスを検索
            for product_id in PASORI_PRODUCT_IDS:
                found_devices = usb.core.find(
                    find_all=True,
                    idVendor=SONY_VENDOR_ID,
                    idProduct=product_id
                )
                
                for idx, device in enumerate(found_devices):
                    device_id = f"pasori_{product_id:04x}_{idx}"
                    usb_path = f"usb:{device.bus:03d}:{device.address:03d}"
                    
                    devices.append({
                        "id": device_id,
                        "path": usb_path,
                        "product_id": product_id,
                        "bus": device.bus,
                        "address": device.address
                    })
                    
                    logger.info(f"Detected PaSoRi device: {device_id} at {usb_path}")
        
        except Exception as e:
            logger.error(f"Error detecting PaSoRi devices: {str(e)}")
        
        return devices
    
    def _assign_reader_roles(self):
        """リーダーの役割を割り当て"""
        active_readers = [
            r for r in self.readers.values() 
            if r.is_active
        ]
        
        if not active_readers:
            self.primary_reader = None
            self.backup_readers = []
            return
        
        # 健全性スコアでソート
        active_readers.sort(
            key=lambda r: r.get_health_score(), 
            reverse=True
        )
        
        # 最も健全なリーダーをプライマリに
        self.primary_reader = active_readers[0]
        self.backup_readers = active_readers[1:]
        
        logger.info(
            f"Assigned primary reader: {self.primary_reader.device_id}, "
            f"backups: {[r.device_id for r in self.backup_readers]}"
        )
    
    async def read_card_multi(self, timeout: float = 3.0) -> Tuple[Optional[str], Optional[str]]:
        """
        複数リーダーからの同時読み取り
        
        Returns:
            (カードIDm, 読み取ったデバイスID)
        """
        if not self._initialization_complete:
            logger.error("Reader manager not initialized")
            return None, None
        
        active_readers = [
            r for r in self.readers.values() 
            if r.is_active
        ]
        
        if not active_readers:
            logger.error("No active readers available")
            return None, None
        
        # 各リーダーで並行読み取り
        read_tasks = []
        for reader in active_readers:
            task = asyncio.create_task(
                self._read_from_device(reader, timeout)
            )
            read_tasks.append((task, reader.device_id))
        
        try:
            # 最初に成功した読み取りを使用
            done, pending = await asyncio.wait(
                [task for task, _ in read_tasks],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout
            )
            
            # 成功した読み取りを取得
            for task in done:
                result = await task
                if result:
                    # 他のタスクをキャンセル
                    for p in pending:
                        p.cancel()
                    
                    # どのリーダーが読み取ったか特定
                    for t, device_id in read_tasks:
                        if t == task:
                            logger.info(f"Card read by device: {device_id}")
                            return result, device_id
            
            return None, None
            
        except asyncio.TimeoutError:
            logger.warning("Read timeout on all devices")
            return None, None
        except Exception as e:
            logger.error(f"Error in multi-reader read: {str(e)}")
            return None, None
    
    async def _read_from_device(
        self, 
        reader: ReaderDevice, 
        timeout: float
    ) -> Optional[str]:
        """個別デバイスからの読み取り（非同期）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            reader.read_card, 
            timeout
        )
    
    async def _monitor_devices(self):
        """デバイスの継続的な監視"""
        while True:
            try:
                await asyncio.sleep(30)  # 30秒ごとにチェック
                
                # 各デバイスの状態をチェック
                for reader in self.readers.values():
                    if reader.is_active and reader.error_count > 10:
                        logger.warning(
                            f"Reader {reader.device_id} has high error count, "
                            f"attempting reconnection"
                        )
                        reader.disconnect()
                        reader.connect()
                
                # 役割の再割り当て
                self._assign_reader_roles()
                
                # 新しいデバイスの検出
                await self._check_new_devices()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in device monitoring: {str(e)}")
    
    async def _check_new_devices(self):
        """新しいデバイスをチェック"""
        current_devices = self._detect_pasori_devices()
        current_ids = {d["id"] for d in current_devices}
        known_ids = set(self.readers.keys())
        
        # 新しいデバイスを検出
        new_ids = current_ids - known_ids
        
        for device_info in current_devices:
            if device_info["id"] in new_ids:
                logger.info(f"New device detected: {device_info['id']}")
                
                reader = ReaderDevice(
                    device_info["id"], 
                    device_info["path"]
                )
                
                if reader.connect():
                    self.readers[device_info["id"]] = reader
                    logger.info(f"Added new reader: {device_info['id']}")
    
    async def get_reader_status(self) -> Dict[str, any]:
        """全リーダーの状態を取得"""
        status = {
            "total_readers": len(self.readers),
            "active_readers": sum(1 for r in self.readers.values() if r.is_active),
            "primary": None,
            "readers": []
        }
        
        if self.primary_reader:
            status["primary"] = self.primary_reader.device_id
        
        for reader in self.readers.values():
            reader_status = {
                "device_id": reader.device_id,
                "is_active": reader.is_active,
                "health_score": reader.get_health_score(),
                "read_count": reader.read_count,
                "error_count": reader.error_count,
                "last_read": reader.last_read_time.isoformat() if reader.last_read_time else None,
                "role": "primary" if reader == self.primary_reader else 
                       "backup" if reader in self.backup_readers else "inactive"
            }
            status["readers"].append(reader_status)
        
        return status
    
    def shutdown(self):
        """マネージャーをシャットダウン"""
        logger.info("Shutting down multi-reader manager")
        
        # 監視タスクを停止
        if self._monitor_task:
            self._monitor_task.cancel()
        
        # 全リーダーを切断
        for reader in self.readers.values():
            reader.disconnect()
        
        self.readers.clear()
        self.primary_reader = None
        self.backup_readers = []
        self._initialization_complete = False


# グローバルインスタンス
multi_reader_manager = MultiReaderManager()