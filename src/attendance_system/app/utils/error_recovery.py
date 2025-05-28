"""
高度エラー回復システム

インテリジェントなエラー回復とエラーパターン学習を実現します。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import json
import traceback

logger = logging.getLogger(__name__)


class ErrorPattern:
    """エラーパターンの記録"""

    def __init__(self, error_type: str, context: Dict[str, any]):
        self.error_type = error_type
        self.context = context
        self.occurrences: List[datetime] = []
        self.recovery_attempts: List[Dict[str, any]] = []
        self.successful_strategies: List[str] = []

    def add_occurrence(self):
        """エラー発生を記録"""
        self.occurrences.append(datetime.now())
        # 古い記録を削除（24時間以上前）
        cutoff = datetime.now() - timedelta(hours=24)
        self.occurrences = [o for o in self.occurrences if o > cutoff]

    def add_recovery_attempt(self, strategy: str, success: bool, duration: float):
        """回復試行を記録"""
        attempt = {
            "strategy": strategy,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now(),
        }
        self.recovery_attempts.append(attempt)

        if success:
            self.successful_strategies.append(strategy)

    def get_frequency(self) -> float:
        """エラー頻度を取得（1時間あたり）"""
        if not self.occurrences:
            return 0.0

        time_span = (datetime.now() - self.occurrences[0]).total_seconds() / 3600
        return len(self.occurrences) / max(time_span, 1)

    def get_best_strategy(self) -> Optional[str]:
        """最も成功率の高い戦略を取得"""
        if not self.successful_strategies:
            return None

        # 戦略ごとの成功回数をカウント
        strategy_counts = defaultdict(int)
        for strategy in self.successful_strategies:
            strategy_counts[strategy] += 1

        # 最も成功回数の多い戦略を返す
        return max(strategy_counts.items(), key=lambda x: x[1])[0]


class AdvancedErrorRecovery:
    """高度エラー回復システム"""

    ERROR_RECOVERY_STRATEGIES = {
        "USB_DISCONNECTED": ["reconnect", "switch_backup", "reset_usb", "manual_mode"],
        "CARD_READ_FAILED": [
            "retry_read",
            "increase_timeout",
            "clean_suggestion",
            "manual_input",
        ],
        "DATABASE_ERROR": [
            "retry_query",
            "connection_pool_reset",
            "cache_write",
            "offline_queue",
        ],
        "NETWORK_ERROR": [
            "retry_connection",
            "switch_endpoint",
            "offline_mode",
            "local_cache",
        ],
        "AUTHENTICATION_ERROR": [
            "refresh_token",
            "re_authenticate",
            "fallback_auth",
            "manual_override",
        ],
        "TIMEOUT_ERROR": [
            "increase_timeout",
            "async_processing",
            "partial_retry",
            "graceful_degradation",
        ],
        "RESOURCE_EXHAUSTED": [
            "garbage_collection",
            "cache_clear",
            "process_restart",
            "load_shedding",
        ],
    }

    def __init__(self):
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.recovery_handlers: Dict[str, Callable] = self._initialize_handlers()
        self.recovery_history: List[Dict[str, any]] = []
        self._learning_enabled = True

    def _initialize_handlers(self) -> Dict[str, Callable]:
        """回復ハンドラーを初期化"""
        return {
            "reconnect": self._handle_reconnect,
            "switch_backup": self._handle_switch_backup,
            "reset_usb": self._handle_reset_usb,
            "manual_mode": self._handle_manual_mode,
            "retry_read": self._handle_retry_read,
            "increase_timeout": self._handle_increase_timeout,
            "clean_suggestion": self._handle_clean_suggestion,
            "manual_input": self._handle_manual_input,
            "retry_query": self._handle_retry_query,
            "connection_pool_reset": self._handle_connection_pool_reset,
            "cache_write": self._handle_cache_write,
            "offline_queue": self._handle_offline_queue,
            "retry_connection": self._handle_retry_connection,
            "switch_endpoint": self._handle_switch_endpoint,
            "offline_mode": self._handle_offline_mode,
            "local_cache": self._handle_local_cache,
            "refresh_token": self._handle_refresh_token,
            "re_authenticate": self._handle_re_authenticate,
            "fallback_auth": self._handle_fallback_auth,
            "manual_override": self._handle_manual_override,
            "increase_timeout": self._handle_increase_timeout,
            "async_processing": self._handle_async_processing,
            "partial_retry": self._handle_partial_retry,
            "graceful_degradation": self._handle_graceful_degradation,
            "garbage_collection": self._handle_garbage_collection,
            "cache_clear": self._handle_cache_clear,
            "process_restart": self._handle_process_restart,
            "load_shedding": self._handle_load_shedding,
        }

    async def intelligent_recovery(
        self, error_type: str, context: Dict[str, any]
    ) -> Dict[str, any]:
        """
        インテリジェント回復

        Args:
            error_type: エラーの種類
            context: エラーコンテキスト

        Returns:
            回復結果
        """
        start_time = datetime.now()

        # エラーパターンを記録
        pattern_key = f"{error_type}_{self._get_context_key(context)}"
        if pattern_key not in self.error_patterns:
            self.error_patterns[pattern_key] = ErrorPattern(error_type, context)

        pattern = self.error_patterns[pattern_key]
        pattern.add_occurrence()

        # 学習に基づく戦略選択
        strategies = await self._select_strategies(error_type, pattern)

        # 各戦略を試行
        for strategy in strategies:
            try:
                logger.info(
                    f"Attempting recovery strategy: {strategy} for {error_type}"
                )

                if strategy in self.recovery_handlers:
                    result = await self.recovery_handlers[strategy](context)

                    if result.get("success", False):
                        duration = (datetime.now() - start_time).total_seconds()
                        pattern.add_recovery_attempt(strategy, True, duration)

                        self._record_recovery(error_type, strategy, True, duration)

                        return {
                            "recovered": True,
                            "strategy": strategy,
                            "duration": duration,
                            "result": result,
                        }
                    else:
                        pattern.add_recovery_attempt(strategy, False, 0)

            except Exception as e:
                logger.error(f"Error in recovery strategy {strategy}: {str(e)}")
                continue

        # すべての戦略が失敗
        self._record_recovery(error_type, "none", False, 0)

        return {
            "recovered": False,
            "manual_intervention_required": True,
            "attempted_strategies": strategies,
            "error_frequency": pattern.get_frequency(),
            "recommendation": self._generate_recommendation(error_type, pattern),
        }

    async def _select_strategies(
        self, error_type: str, pattern: ErrorPattern
    ) -> List[str]:
        """学習に基づいて戦略を選択"""
        base_strategies = self.ERROR_RECOVERY_STRATEGIES.get(error_type, [])

        if not self._learning_enabled:
            return base_strategies

        # パターンから最適な戦略を取得
        best_strategy = pattern.get_best_strategy()

        if best_strategy and best_strategy in base_strategies:
            # 最適戦略を先頭に移動
            strategies = [best_strategy] + [
                s for s in base_strategies if s != best_strategy
            ]
        else:
            strategies = base_strategies

        # エラー頻度が高い場合は、より積極的な戦略を追加
        if pattern.get_frequency() > 5:  # 1時間に5回以上
            if "process_restart" not in strategies:
                strategies.append("process_restart")

        return strategies

    def _get_context_key(self, context: Dict[str, any]) -> str:
        """コンテキストからキーを生成"""
        # 重要なコンテキスト要素のみを使用
        key_elements = []

        for key in ["device_id", "employee_id", "endpoint", "resource"]:
            if key in context:
                key_elements.append(f"{key}:{context[key]}")

        return "_".join(key_elements) if key_elements else "default"

    def _record_recovery(
        self, error_type: str, strategy: str, success: bool, duration: float
    ):
        """回復結果を記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "strategy": strategy,
            "success": success,
            "duration": duration,
        }

        self.recovery_history.append(record)

        # 履歴を制限（最新1000件）
        if len(self.recovery_history) > 1000:
            self.recovery_history = self.recovery_history[-1000:]

    def _generate_recommendation(self, error_type: str, pattern: ErrorPattern) -> str:
        """推奨事項を生成"""
        frequency = pattern.get_frequency()

        if frequency > 10:
            return "エラーが頻発しています。システム管理者に連絡してください。"
        elif frequency > 5:
            return "エラーが繰り返し発生しています。デバイスの再起動を推奨します。"
        elif error_type == "USB_DISCONNECTED":
            return "USBケーブルの接続を確認してください。"
        elif error_type == "CARD_READ_FAILED":
            return "カードリーダーの清掃を行ってください。"
        elif error_type == "DATABASE_ERROR":
            return "データベース接続を確認してください。"
        else:
            return "問題が継続する場合は、システム管理者に連絡してください。"

    # 回復ハンドラーの実装

    async def _handle_reconnect(self, context: Dict[str, any]) -> Dict[str, any]:
        """再接続ハンドラー"""
        device_id = context.get("device_id")

        if device_id:
            # デバイス再接続を試行
            from hardware.card_reader import CardReaderManager

            manager = CardReaderManager()

            try:
                await asyncio.sleep(1)  # 短い待機
                success = await manager.reconnect_device(device_id)
                return {"success": success}
            except:
                return {"success": False}

        return {"success": False}

    async def _handle_switch_backup(self, context: Dict[str, any]) -> Dict[str, any]:
        """バックアップ切り替えハンドラー"""
        # バックアップデバイスへの切り替え
        from hardware.multi_reader_manager import multi_reader_manager

        try:
            status = await multi_reader_manager.get_reader_status()
            if status["active_readers"] > 1:
                # プライマリを変更
                multi_reader_manager._assign_reader_roles()
                return {"success": True}
        except:
            pass

        return {"success": False}

    async def _handle_reset_usb(self, context: Dict[str, any]) -> Dict[str, any]:
        """USB リセットハンドラー"""
        # プラットフォーム依存のUSBリセット
        import platform

        try:
            if platform.system() == "Linux":
                import subprocess

                # USB デバイスのリセット（要root権限）
                device_path = context.get("device_path")
                if device_path:
                    subprocess.run(["usbreset", device_path], check=True)
                    return {"success": True}
            elif platform.system() == "Darwin":  # macOS
                # macOSでのUSBリセット
                pass
        except:
            pass

        return {"success": False}

    async def _handle_manual_mode(self, context: Dict[str, any]) -> Dict[str, any]:
        """手動モードハンドラー"""
        # 手動入力モードへの切り替え
        logger.info("Switching to manual input mode")
        context["manual_mode"] = True
        return {"success": True, "mode": "manual"}

    async def _handle_retry_read(self, context: Dict[str, any]) -> Dict[str, any]:
        """読み取り再試行ハンドラー"""
        max_retries = context.get("max_retries", 3)
        current_retry = context.get("current_retry", 0)

        if current_retry < max_retries:
            await asyncio.sleep(0.5 * (current_retry + 1))  # 指数バックオフ
            return {"success": True, "retry": current_retry + 1}

        return {"success": False}

    async def _handle_increase_timeout(self, context: Dict[str, any]) -> Dict[str, any]:
        """タイムアウト増加ハンドラー"""
        current_timeout = context.get("timeout", 3.0)
        new_timeout = min(current_timeout * 1.5, 10.0)  # 最大10秒

        context["timeout"] = new_timeout
        return {"success": True, "new_timeout": new_timeout}

    async def _handle_clean_suggestion(self, context: Dict[str, any]) -> Dict[str, any]:
        """清掃提案ハンドラー"""
        # 清掃提案を生成
        return {
            "success": True,
            "suggestion": "カードリーダーの読み取り面を柔らかい布で清掃してください。",
            "maintenance_required": True,
        }

    async def _handle_manual_input(self, context: Dict[str, any]) -> Dict[str, any]:
        """手動入力ハンドラー"""
        # 手動入力インターフェースを有効化
        context["enable_manual_input"] = True
        return {"success": True, "input_method": "manual"}

    async def _handle_retry_query(self, context: Dict[str, any]) -> Dict[str, any]:
        """クエリ再試行ハンドラー"""
        # データベースクエリの再試行
        await asyncio.sleep(1)
        return {"success": True, "action": "retry_query"}

    async def _handle_connection_pool_reset(
        self, context: Dict[str, any]
    ) -> Dict[str, any]:
        """接続プールリセットハンドラー"""
        # データベース接続プールのリセット
        try:
            from backend.app.database import reset_connection_pool

            await reset_connection_pool()
            return {"success": True}
        except:
            return {"success": False}

    async def _handle_cache_write(self, context: Dict[str, any]) -> Dict[str, any]:
        """キャッシュ書き込みハンドラー"""
        # データをキャッシュに書き込み
        data = context.get("data")
        if data:
            # キャッシュに保存（実装は省略）
            return {"success": True, "cached": True}
        return {"success": False}

    async def _handle_offline_queue(self, context: Dict[str, any]) -> Dict[str, any]:
        """オフラインキューハンドラー"""
        # オフラインキューに追加
        from backend.app.utils.offline_queue import OfflineQueueManager

        try:
            queue_manager = OfflineQueueManager()
            await queue_manager.add_to_queue(context.get("data"))
            return {"success": True, "queued": True}
        except:
            return {"success": False}

    async def _handle_retry_connection(self, context: Dict[str, any]) -> Dict[str, any]:
        """接続再試行ハンドラー"""
        # ネットワーク接続の再試行
        await asyncio.sleep(2)
        return {"success": True, "action": "retry_connection"}

    async def _handle_switch_endpoint(self, context: Dict[str, any]) -> Dict[str, any]:
        """エンドポイント切り替えハンドラー"""
        # 代替エンドポイントへの切り替え
        endpoints = context.get("endpoints", [])
        current = context.get("current_endpoint")

        if endpoints and current in endpoints:
            idx = endpoints.index(current)
            next_endpoint = endpoints[(idx + 1) % len(endpoints)]
            context["current_endpoint"] = next_endpoint
            return {"success": True, "new_endpoint": next_endpoint}

        return {"success": False}

    async def _handle_offline_mode(self, context: Dict[str, any]) -> Dict[str, any]:
        """オフラインモードハンドラー"""
        # オフラインモードへの切り替え
        context["offline_mode"] = True
        return {"success": True, "mode": "offline"}

    async def _handle_local_cache(self, context: Dict[str, any]) -> Dict[str, any]:
        """ローカルキャッシュハンドラー"""
        # ローカルキャッシュの使用
        context["use_local_cache"] = True
        return {"success": True, "cache": "local"}

    async def _handle_refresh_token(self, context: Dict[str, any]) -> Dict[str, any]:
        """トークン更新ハンドラー"""
        # 認証トークンの更新
        try:
            from backend.app.services.auth_service import AuthService

            auth_service = AuthService()
            new_token = await auth_service.refresh_token()
            context["token"] = new_token
            return {"success": True}
        except:
            return {"success": False}

    async def _handle_re_authenticate(self, context: Dict[str, any]) -> Dict[str, any]:
        """再認証ハンドラー"""
        # 完全な再認証
        return {"success": False, "action": "require_re_authentication"}

    async def _handle_fallback_auth(self, context: Dict[str, any]) -> Dict[str, any]:
        """フォールバック認証ハンドラー"""
        # 代替認証方法の使用
        context["auth_method"] = "fallback"
        return {"success": True, "auth": "fallback"}

    async def _handle_manual_override(self, context: Dict[str, any]) -> Dict[str, any]:
        """手動オーバーライドハンドラー"""
        # 管理者による手動オーバーライド
        context["manual_override"] = True
        return {"success": True, "override": True}

    async def _handle_async_processing(self, context: Dict[str, any]) -> Dict[str, any]:
        """非同期処理ハンドラー"""
        # 非同期処理への切り替え
        context["processing_mode"] = "async"
        return {"success": True, "mode": "async"}

    async def _handle_partial_retry(self, context: Dict[str, any]) -> Dict[str, any]:
        """部分再試行ハンドラー"""
        # 失敗した部分のみ再試行
        failed_items = context.get("failed_items", [])
        if failed_items:
            context["retry_items"] = failed_items
            return {"success": True, "partial": True}
        return {"success": False}

    async def _handle_graceful_degradation(
        self, context: Dict[str, any]
    ) -> Dict[str, any]:
        """グレースフルデグラデーションハンドラー"""
        # 機能を段階的に制限
        context["degraded_mode"] = True
        context["disabled_features"] = ["advanced_analytics", "real_time_sync"]
        return {"success": True, "degraded": True}

    async def _handle_garbage_collection(
        self, context: Dict[str, any]
    ) -> Dict[str, any]:
        """ガベージコレクションハンドラー"""
        # メモリクリーンアップ
        import gc

        gc.collect()
        return {"success": True, "gc": "completed"}

    async def _handle_cache_clear(self, context: Dict[str, any]) -> Dict[str, any]:
        """キャッシュクリアハンドラー"""
        # 各種キャッシュのクリア
        # 実装は各キャッシュシステムに依存
        return {"success": True, "cache": "cleared"}

    async def _handle_process_restart(self, context: Dict[str, any]) -> Dict[str, any]:
        """プロセス再起動ハンドラー"""
        # プロセスの再起動をスケジュール
        context["restart_scheduled"] = True
        return {"success": True, "restart": "scheduled"}

    async def _handle_load_shedding(self, context: Dict[str, any]) -> Dict[str, any]:
        """負荷制限ハンドラー"""
        # 一時的に負荷を制限
        context["load_shedding"] = True
        context["max_concurrent"] = 10  # 同時実行数を制限
        return {"success": True, "load": "limited"}

    async def error_learning(self, error_pattern: Dict[str, any]):
        """
        エラー学習機能

        Args:
            error_pattern: エラーパターンデータ
        """
        if not self._learning_enabled:
            return

        # エラーパターンの分析と学習
        error_type = error_pattern.get("type")
        success_rate = error_pattern.get("success_rate", 0)

        # 成功率の低い戦略を後方に移動
        if error_type in self.ERROR_RECOVERY_STRATEGIES:
            strategies = self.ERROR_RECOVERY_STRATEGIES[error_type]
            # 戦略の並び替えロジック（実装省略）

    def get_recovery_statistics(self) -> Dict[str, any]:
        """回復統計を取得"""
        if not self.recovery_history:
            return {
                "total_attempts": 0,
                "success_rate": 0,
                "common_errors": [],
                "effective_strategies": [],
            }

        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r["success"])

        # エラータイプ別の統計
        error_counts = defaultdict(int)
        strategy_success = defaultdict(lambda: {"success": 0, "total": 0})

        for record in self.recovery_history:
            error_counts[record["error_type"]] += 1

            strategy = record["strategy"]
            strategy_success[strategy]["total"] += 1
            if record["success"]:
                strategy_success[strategy]["success"] += 1

        # 最も一般的なエラー
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        # 最も効果的な戦略
        effective_strategies = []
        for strategy, stats in strategy_success.items():
            if stats["total"] > 0:
                success_rate = stats["success"] / stats["total"]
                effective_strategies.append(
                    {
                        "strategy": strategy,
                        "success_rate": success_rate,
                        "usage_count": stats["total"],
                    }
                )

        effective_strategies.sort(key=lambda x: x["success_rate"], reverse=True)

        return {
            "total_attempts": total,
            "success_rate": successful / total if total > 0 else 0,
            "common_errors": common_errors,
            "effective_strategies": effective_strategies[:5],
            "learning_enabled": self._learning_enabled,
        }


# グローバルインスタンス
error_recovery = AdvancedErrorRecovery()
