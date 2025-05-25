"""
PaSoRiデバイス監視システム

デバイスの健全性を継続的に監視し、予防保守を支援します。
"""

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import psutil
import usb.core
import platform
import statistics

logger = logging.getLogger(__name__)


class DeviceMetrics:
    """デバイスメトリクスの記録"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.response_times: List[float] = []
        self.error_counts: List[int] = []
        self.success_counts: List[int] = []
        self.timestamps: List[datetime] = []
        self._lock = threading.Lock()
    
    def add_metric(
        self, 
        response_time: Optional[float], 
        success: bool
    ):
        """メトリクスを追加"""
        with self._lock:
            self.timestamps.append(datetime.now())
            
            if response_time is not None:
                self.response_times.append(response_time)
            
            if success:
                self.success_counts.append(1)
                self.error_counts.append(0)
            else:
                self.success_counts.append(0)
                self.error_counts.append(1)
            
            # ウィンドウサイズを維持
            if len(self.timestamps) > self.window_size:
                self.timestamps.pop(0)
                if self.response_times:
                    self.response_times.pop(0)
                self.success_counts.pop(0)
                self.error_counts.pop(0)
    
    def get_statistics(self) -> Dict[str, any]:
        """統計情報を取得"""
        with self._lock:
            if not self.timestamps:
                return {
                    "avg_response_time": 0,
                    "min_response_time": 0,
                    "max_response_time": 0,
                    "error_rate": 0,
                    "success_rate": 0,
                    "total_operations": 0
                }
            
            total_ops = len(self.timestamps)
            total_errors = sum(self.error_counts)
            total_success = sum(self.success_counts)
            
            stats = {
                "avg_response_time": statistics.mean(self.response_times) if self.response_times else 0,
                "min_response_time": min(self.response_times) if self.response_times else 0,
                "max_response_time": max(self.response_times) if self.response_times else 0,
                "error_rate": total_errors / total_ops if total_ops > 0 else 0,
                "success_rate": total_success / total_ops if total_ops > 0 else 0,
                "total_operations": total_ops
            }
            
            # 最近のトレンドを計算
            if len(self.timestamps) >= 10:
                recent_errors = sum(self.error_counts[-10:])
                recent_total = 10
                stats["recent_error_rate"] = recent_errors / recent_total
            
            return stats


class PaSoRiDeviceMonitor:
    """PaSoRiデバイス監視"""
    
    HEALTH_THRESHOLDS = {
        "response_time": {
            "good": 0.5,      # 0.5秒以下は良好
            "warning": 1.0,   # 1.0秒以下は警告
            "critical": 2.0   # 2.0秒以上は危険
        },
        "error_rate": {
            "good": 0.05,     # 5%以下は良好
            "warning": 0.10,  # 10%以下は警告
            "critical": 0.20  # 20%以上は危険
        },
        "temperature": {
            "good": 40,       # 40℃以下は良好
            "warning": 50,    # 50℃以下は警告
            "critical": 60    # 60℃以上は危険
        }
    }
    
    def __init__(self):
        self.device_metrics: Dict[str, DeviceMetrics] = {}
        self.device_info: Dict[str, Dict[str, any]] = {}
        self.health_history: Dict[str, List[Dict[str, any]]] = {}
        self._monitoring = False
        self._monitor_task = None
        self._check_interval = 30  # 秒
    
    async def start_monitoring(self):
        """監視を開始"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self.continuous_health_check())
            logger.info("Device monitoring started")
    
    async def stop_monitoring(self):
        """監視を停止"""
        if self._monitoring:
            self._monitoring = False
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            logger.info("Device monitoring stopped")
    
    async def continuous_health_check(self):
        """連続ヘルスチェック"""
        while self._monitoring:
            try:
                # USB接続状態確認
                usb_status = await self._check_usb_connections()
                
                # 各デバイスの診断
                for device_id in self.device_info:
                    diagnostics = await self.device_diagnostics(device_id)
                    
                    # 健全性履歴に追加
                    if device_id not in self.health_history:
                        self.health_history[device_id] = []
                    
                    self.health_history[device_id].append({
                        "timestamp": datetime.now(),
                        "diagnostics": diagnostics
                    })
                    
                    # 古い履歴を削除（24時間分保持）
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    self.health_history[device_id] = [
                        h for h in self.health_history[device_id]
                        if h["timestamp"] > cutoff_time
                    ]
                    
                    # 予防保守チェック
                    maintenance = await self.predictive_maintenance(device_id)
                    if maintenance["action_required"]:
                        logger.warning(
                            f"Maintenance required for device {device_id}: "
                            f"{maintenance['recommendation']}"
                        )
                
                await asyncio.sleep(self._check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous health check: {str(e)}")
                await asyncio.sleep(60)  # エラー時は1分後に再試行
    
    def register_device(self, device_id: str, device_info: Dict[str, any]):
        """デバイスを登録"""
        self.device_info[device_id] = device_info
        self.device_metrics[device_id] = DeviceMetrics()
        logger.info(f"Registered device for monitoring: {device_id}")
    
    def record_operation(
        self, 
        device_id: str, 
        response_time: Optional[float], 
        success: bool
    ):
        """操作結果を記録"""
        if device_id in self.device_metrics:
            self.device_metrics[device_id].add_metric(response_time, success)
    
    async def _check_usb_connections(self) -> Dict[str, any]:
        """USB接続状態を確認"""
        SONY_VENDOR_ID = 0x054c
        PASORI_PRODUCT_IDS = [0x01bb, 0x02e1, 0x06c1, 0x06c3]
        
        connected_devices = []
        
        try:
            for product_id in PASORI_PRODUCT_IDS:
                devices = usb.core.find(
                    find_all=True,
                    idVendor=SONY_VENDOR_ID,
                    idProduct=product_id
                )
                
                for device in devices:
                    device_info = {
                        "vendor_id": device.idVendor,
                        "product_id": device.idProduct,
                        "bus": device.bus,
                        "address": device.address,
                        "manufacturer": self._get_string_descriptor(device, device.iManufacturer),
                        "product": self._get_string_descriptor(device, device.iProduct),
                        "serial": self._get_string_descriptor(device, device.iSerialNumber)
                    }
                    connected_devices.append(device_info)
        
        except Exception as e:
            logger.error(f"Error checking USB connections: {str(e)}")
        
        return {
            "connected_count": len(connected_devices),
            "devices": connected_devices,
            "check_time": datetime.now().isoformat()
        }
    
    def _get_string_descriptor(self, device, index):
        """USB文字列ディスクリプタを取得"""
        try:
            if index:
                return usb.util.get_string(device, index)
        except:
            pass
        return None
    
    async def device_diagnostics(self, device_id: str) -> Dict[str, any]:
        """詳細診断"""
        diagnostics = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "connection_status": "unknown",
            "health_score": 0.0,
            "metrics": {},
            "system_info": {}
        }
        
        # デバイスメトリクスを取得
        if device_id in self.device_metrics:
            metrics = self.device_metrics[device_id].get_statistics()
            diagnostics["metrics"] = metrics
            
            # 健全性スコアを計算
            health_score = self._calculate_health_score(metrics)
            diagnostics["health_score"] = health_score
            
            # 接続状態を判定
            if metrics["total_operations"] > 0:
                if metrics["recent_error_rate"] < 0.1:
                    diagnostics["connection_status"] = "connected"
                else:
                    diagnostics["connection_status"] = "unstable"
            else:
                diagnostics["connection_status"] = "idle"
        
        # システム情報を追加
        diagnostics["system_info"] = await self._get_system_info()
        
        # ドライバー情報を取得
        diagnostics["driver_info"] = await self._get_driver_info()
        
        return diagnostics
    
    def _calculate_health_score(self, metrics: Dict[str, any]) -> float:
        """健全性スコアを計算（0.0-1.0）"""
        score = 1.0
        
        # レスポンス時間による減点
        avg_response = metrics.get("avg_response_time", 0)
        if avg_response > self.HEALTH_THRESHOLDS["response_time"]["critical"]:
            score -= 0.4
        elif avg_response > self.HEALTH_THRESHOLDS["response_time"]["warning"]:
            score -= 0.2
        elif avg_response > self.HEALTH_THRESHOLDS["response_time"]["good"]:
            score -= 0.1
        
        # エラー率による減点
        error_rate = metrics.get("error_rate", 0)
        if error_rate > self.HEALTH_THRESHOLDS["error_rate"]["critical"]:
            score -= 0.4
        elif error_rate > self.HEALTH_THRESHOLDS["error_rate"]["warning"]:
            score -= 0.2
        elif error_rate > self.HEALTH_THRESHOLDS["error_rate"]["good"]:
            score -= 0.1
        
        return max(0.0, score)
    
    async def _get_system_info(self) -> Dict[str, any]:
        """システム情報を取得"""
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "usb_ports": []
        }
        
        # USB関連のシステム情報
        if platform.system() == "Linux":
            # Linux固有の情報
            try:
                import subprocess
                result = subprocess.run(
                    ["lsusb"], 
                    capture_output=True, 
                    text=True
                )
                info["usb_devices"] = result.stdout.count('\n')
            except:
                pass
                
        elif platform.system() == "Windows":
            # Windows固有の情報
            try:
                import wmi
                c = wmi.WMI()
                usb_devices = c.Win32_USBHub()
                info["usb_hubs"] = len(usb_devices)
            except:
                pass
        
        return info
    
    async def _get_driver_info(self) -> Dict[str, any]:
        """ドライバー情報を取得"""
        driver_info = {
            "nfc_version": None,
            "libusb_version": None,
            "driver_status": "unknown"
        }
        
        try:
            import nfc
            driver_info["nfc_version"] = getattr(nfc, "__version__", "unknown")
            driver_info["driver_status"] = "loaded"
        except:
            driver_info["driver_status"] = "not_found"
        
        try:
            import usb
            driver_info["libusb_version"] = getattr(usb, "__version__", "unknown")
        except:
            pass
        
        return driver_info
    
    async def predictive_maintenance(self, device_id: str) -> Dict[str, any]:
        """予防保守提案"""
        if device_id not in self.health_history:
            return {
                "action_required": False,
                "recommendation": "Insufficient data for prediction"
            }
        
        history = self.health_history[device_id]
        if len(history) < 10:
            return {
                "action_required": False,
                "recommendation": "Gathering baseline data"
            }
        
        # 健全性スコアのトレンドを分析
        recent_scores = [
            h["diagnostics"]["health_score"] 
            for h in history[-10:]
        ]
        
        # スコアの低下傾向をチェック
        score_trend = self._calculate_trend(recent_scores)
        
        maintenance_needed = False
        recommendations = []
        
        # 継続的な低スコア
        if all(score < 0.7 for score in recent_scores[-5:]):
            maintenance_needed = True
            recommendations.append("デバイスが継続的に低パフォーマンス状態です")
        
        # 急激なスコア低下
        if score_trend < -0.05:  # 5%以上の低下傾向
            maintenance_needed = True
            recommendations.append("パフォーマンスが急速に低下しています")
        
        # エラー率の上昇
        recent_error_rates = [
            h["diagnostics"]["metrics"].get("error_rate", 0)
            for h in history[-10:]
        ]
        
        if statistics.mean(recent_error_rates) > 0.15:
            maintenance_needed = True
            recommendations.append("エラー率が高くなっています")
        
        # レスポンス時間の増加
        recent_response_times = [
            h["diagnostics"]["metrics"].get("avg_response_time", 0)
            for h in history[-10:]
            if h["diagnostics"]["metrics"].get("avg_response_time") is not None
        ]
        
        if recent_response_times and statistics.mean(recent_response_times) > 1.5:
            maintenance_needed = True
            recommendations.append("レスポンス時間が遅くなっています")
        
        # 推奨アクション
        if maintenance_needed:
            if len(recommendations) >= 3:
                action = "デバイスの交換を推奨"
            elif any("エラー率" in r for r in recommendations):
                action = "USBポートの変更またはドライバーの再インストールを推奨"
            else:
                action = "デバイスの再起動を推奨"
        else:
            action = "正常動作中"
        
        return {
            "action_required": maintenance_needed,
            "recommendation": action,
            "details": recommendations,
            "health_trend": score_trend,
            "current_score": recent_scores[-1] if recent_scores else 0
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """トレンドを計算（線形回帰の傾き）"""
        if len(values) < 2:
            return 0.0
        
        x = list(range(len(values)))
        n = len(values)
        
        # 線形回帰の傾きを計算
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope
    
    async def get_monitoring_summary(self) -> Dict[str, any]:
        """監視サマリーを取得"""
        summary = {
            "monitoring_active": self._monitoring,
            "device_count": len(self.device_info),
            "devices": []
        }
        
        for device_id in self.device_info:
            device_summary = {
                "device_id": device_id,
                "health_score": 0.0,
                "status": "unknown",
                "last_diagnostic": None
            }
            
            # 最新の診断結果
            if device_id in self.health_history and self.health_history[device_id]:
                latest = self.health_history[device_id][-1]
                device_summary["health_score"] = latest["diagnostics"]["health_score"]
                device_summary["status"] = latest["diagnostics"]["connection_status"]
                device_summary["last_diagnostic"] = latest["timestamp"].isoformat()
            
            # 予防保守状態
            maintenance = await self.predictive_maintenance(device_id)
            device_summary["maintenance_required"] = maintenance["action_required"]
            device_summary["maintenance_recommendation"] = maintenance["recommendation"]
            
            summary["devices"].append(device_summary)
        
        return summary


# グローバルインスタンス
device_monitor = PaSoRiDeviceMonitor()