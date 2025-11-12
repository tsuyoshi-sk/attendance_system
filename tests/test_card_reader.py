"""
カードリーダーテスト

PaSoRi RC-S380/RC-S300連携機能の包括的なテストケース
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime
import hashlib

from hardware.card_reader import (
    CardReader,
    CardReaderManager,
    CardReaderError,
    CardReaderConnectionError,
    CardReaderTimeoutError,
)
from config.config import config


class TestCardReader:
    """カードリーダーテストクラス"""

    def test_mock_mode_initialization(self):
        """モックモード初期化のテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            reader = CardReader()
            assert reader.mock_mode is True
            assert reader.connect() is True

    def test_mock_mode_read(self):
        """モックモード読み取りのテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            reader = CardReader()
            reader.connect()

            card_info = reader.read_card_once()

            assert card_info is not None
            assert card_info["idm"] == "0123456789ABCDEF"
            assert len(card_info["idm_hash"]) == 64  # SHA-256ハッシュ
            assert card_info["type"] == "FeliCa"

    @patch("hardware.card_reader.nfc.ContactlessFrontend")
    def test_real_mode_connection(self, mock_nfc):
        """実機モード接続のテスト"""
        with patch("hardware.card_reader.NFC_AVAILABLE", True):
            with patch("config.config.config.PASORI_MOCK_MODE", False):
                reader = CardReader()

                # 正常接続のシミュレート
                mock_clf = MagicMock()
                mock_nfc.return_value = mock_clf

                assert reader.connect() is True
                mock_nfc.assert_called_once_with("usb")

    @patch("hardware.card_reader.nfc.ContactlessFrontend")
    def test_connection_retry(self, mock_nfc):
        """接続リトライのテスト"""
        with patch("hardware.card_reader.NFC_AVAILABLE", True):
            with patch("config.config.config.PASORI_MOCK_MODE", False):
                reader = CardReader()

                # 2回失敗、3回目で成功
                mock_nfc.side_effect = [
                    Exception("Connection failed"),
                    Exception("Connection failed"),
                    MagicMock(),
                ]

                assert reader.connect() is True
                assert mock_nfc.call_count == 3

    @patch("hardware.card_reader.nfc.ContactlessFrontend")
    def test_connection_failure(self, mock_nfc):
        """接続失敗のテスト"""
        with patch("hardware.card_reader.NFC_AVAILABLE", True):
            with patch("config.config.config.PASORI_MOCK_MODE", False):
                reader = CardReader()

                # 全試行失敗
                mock_nfc.side_effect = Exception("Connection failed")

                with pytest.raises(CardReaderConnectionError):
                    reader.connect()

                assert mock_nfc.call_count == reader.MAX_RETRY_COUNT

    def test_idm_hashing(self):
        """IDmハッシュ化のテスト"""
        reader = CardReader()
        test_idm = "0123456789ABCDEF"

        hash1 = reader.hash_idm(test_idm)
        hash2 = reader.hash_idm(test_idm)

        # 同じIDmは同じハッシュ値
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256

        # 異なるIDmは異なるハッシュ値
        hash3 = reader.hash_idm("FEDCBA9876543210")
        assert hash1 != hash3

    @patch("hardware.card_reader.nfc.ContactlessFrontend")
    def test_card_reading_with_timeout(self, mock_nfc):
        """タイムアウト付きカード読み取りのテスト"""
        with patch("hardware.card_reader.NFC_AVAILABLE", True):
            with patch("config.config.config.PASORI_MOCK_MODE", False):
                reader = CardReader()

                mock_clf = MagicMock()
                mock_nfc.return_value = mock_clf
                reader.connect()

                # タイムアウトをシミュレート
                mock_clf.connect.return_value = None

                start_time = time.time()
                result = reader.read_card_once(timeout=1)
                end_time = time.time()

                assert result is None
                assert end_time - start_time >= 0.9  # ほぼ1秒

    def test_performance_metrics(self):
        """パフォーマンスメトリクスのテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            reader = CardReader()
            reader.connect()

            # 複数回読み取り
            for _ in range(5):
                reader.read_card_once()

            stats = reader.get_performance_stats()

            assert stats["total_reads"] == 5
            assert stats["successful_reads"] == 5
            assert stats["failed_reads"] == 0
            assert stats["success_rate"] == "100.0%"
            assert float(stats["average_read_time"][:-1]) < 1.0  # 平均1秒未満

    def test_polling_functionality(self):
        """ポーリング機能のテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            detected_cards = []

            def on_card_detected(card_info):
                detected_cards.append(card_info)

            reader = CardReader(on_card_detected=on_card_detected)
            reader.connect()

            # ポーリング開始
            reader.start_polling(interval=0.1)

            # 0.5秒待機
            time.sleep(0.5)

            # ポーリング停止
            reader.stop_polling()

            # カードが検出されたことを確認
            assert len(detected_cards) > 0
            assert detected_cards[0]["idm"] == "0123456789ABCDEF"

    def test_duplicate_detection_prevention(self):
        """重複検出防止のテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            detected_times = []

            def on_card_detected(card_info):
                detected_times.append(time.time())

            reader = CardReader(on_card_detected=on_card_detected)
            reader.connect()

            # 短い間隔でポーリング
            reader.start_polling(interval=0.05)

            # 1秒待機
            time.sleep(1)

            reader.stop_polling()

            # 検出間隔が3秒以上あることを確認
            if len(detected_times) > 1:
                for i in range(1, len(detected_times)):
                    interval = detected_times[i] - detected_times[i - 1]
                    assert interval >= 2.9  # ほぼ3秒


class TestCardReaderManager:
    """カードリーダーマネージャーテストクラス"""

    def test_singleton_pattern(self):
        """シングルトンパターンのテスト"""
        manager1 = CardReaderManager()
        manager2 = CardReaderManager()

        assert manager1 is manager2

    def test_initialization(self):
        """初期化のテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            manager = CardReaderManager()

            # 初期化前
            assert manager.is_initialized is False

            # 初期化
            assert manager.initialize() is True
            assert manager.is_initialized is True

            # 二重初期化の防止
            assert manager.initialize() is True  # 警告は出るが成功扱い

    def test_read_once(self):
        """単発読み取りのテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            manager = CardReaderManager()
            manager.initialize()

            card_info = manager.read_once()

            assert card_info is not None
            assert "idm" in card_info
            assert "idm_hash" in card_info

    def test_statistics(self):
        """統計情報取得のテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            manager = CardReaderManager()

            # 初期化前
            stats = manager.get_stats()
            assert stats["error"] == "Not initialized"

            # 初期化後
            manager.initialize()
            manager.read_once()

            stats = manager.get_stats()
            assert "total_reads" in stats
            assert "success_rate" in stats
            assert stats["total_reads"] >= 1

    def test_cleanup(self):
        """クリーンアップのテスト"""
        with patch("config.config.config.PASORI_MOCK_MODE", True):
            manager = CardReaderManager()
            manager.initialize()

            assert manager.is_initialized is True

            manager.cleanup()

            assert manager.is_initialized is False

    @patch("hardware.card_reader.CardReader.connect")
    def test_initialization_failure_handling(self, mock_connect):
        """初期化失敗時の処理テスト"""
        mock_connect.side_effect = CardReaderConnectionError("Connection failed")

        with patch("config.config.config.PASORI_MOCK_MODE", False):
            manager = CardReaderManager()

            assert manager.initialize() is False
            assert manager.is_initialized is False

    def test_async_callback_support(self):
        """非同期コールバックサポートのテスト"""
        import asyncio

        async def async_callback(card_info):
            await asyncio.sleep(0.1)
            return card_info

        with patch("config.config.config.PASORI_MOCK_MODE", True):
            reader = CardReader(on_card_detected=async_callback)

            # asyncio.iscoroutinefunction のチェック
            assert asyncio.iscoroutinefunction(reader.on_card_detected)
