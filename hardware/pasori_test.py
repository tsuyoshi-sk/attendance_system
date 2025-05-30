#!/usr/bin/env python3
"""
PaSoRi RC-S380/RC-S300 動作確認スクリプト

PaSoRiの接続確認とFeliCaカードの読み取りテストを行います。
"""

import sys
import os
import time
import hashlib
from typing import Optional, Dict, Any

# プロジェクトルートをPythonパスに追加 - src layout uses PYTHONPATH
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import nfc
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False
    print("警告: nfcpyがインストールされていません。モックモードで動作します。")

from config.config import config


class PaSoRiTester:
    """PaSoRi動作テストクラス"""
    
    def __init__(self):
        self.clf = None
        self.mock_mode = config.PASORI_MOCK_MODE or not NFC_AVAILABLE
    
    def check_environment(self) -> Dict[str, Any]:
        """環境チェック"""
        env_info = {
            "os": sys.platform,
            "python_version": sys.version,
            "nfcpy_available": NFC_AVAILABLE,
            "mock_mode": self.mock_mode,
            "config": {
                "timeout": config.PASORI_TIMEOUT,
                "hash_secret_set": bool(config.IDM_HASH_SECRET)
            }
        }
        
        print("=== 環境情報 ===")
        print(f"OS: {env_info['os']}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"nfcpy: {'利用可能' if NFC_AVAILABLE else '利用不可'}")
        print(f"モックモード: {'有効' if self.mock_mode else '無効'}")
        print(f"タイムアウト: {config.PASORI_TIMEOUT}秒")
        print()
        
        return env_info
    
    def connect_reader(self) -> bool:
        """PaSoRiリーダーに接続"""
        if self.mock_mode:
            print("モックモード: 仮想的にPaSoRiに接続しました")
            return True
        
        try:
            print("PaSoRi RC-S380/RC-S300を検索中...")
            self.clf = nfc.ContactlessFrontend('usb')
            print("PaSoRi RC-S380/RC-S300が見つかりました！")
            return True
        except Exception as e:
            print(f"エラー: PaSoRiの接続に失敗しました - {e}")
            print("\n以下を確認してください:")
            print("1. PaSoRi RC-S380/RC-S300がUSBポートに接続されているか")
            print("2. ドライバがインストールされているか")
            print("3. 他のアプリケーションがPaSoRiを使用していないか")
            if sys.platform == "linux":
                print("4. udevルールが設定されているか（Linuxの場合）")
                print("   参考: https://nfcpy.readthedocs.io/en/latest/topics/get-started.html#linux")
            return False
    
    def read_card(self, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """カード読み取り"""
        if timeout is None:
            timeout = config.PASORI_TIMEOUT
        
        if self.mock_mode:
            return self._read_mock_card(timeout)
        
        print(f"\nカードをPaSoRiにかざしてください（{timeout}秒でタイムアウト）...")
        
        def on_connect(tag):
            """カード検出時のコールバック"""
            return tag
        
        try:
            tag = self.clf.connect(
                rdwr={'on-connect': on_connect},
                terminate=lambda: time.time() - start_time > timeout
            )
            
            if tag:
                return self._process_tag(tag)
            else:
                print("タイムアウト: カードが検出されませんでした")
                return None
                
        except Exception as e:
            print(f"エラー: カード読み取り中にエラーが発生しました - {e}")
            return None
    
    def _read_mock_card(self, timeout: int) -> Optional[Dict[str, Any]]:
        """モックカード読み取り"""
        print(f"\nモックモード: 仮想カードの読み取りをシミュレート中（{timeout}秒でタイムアウト）...")
        
        # ユーザー入力を待つ
        print("Enterキーを押してカード読み取りをシミュレート（何も入力しない場合はタイムアウト）:")
        
        import select
        if sys.platform == "win32":
            # Windows環境では単純なinputを使用
            try:
                input()
                mock_idm = "0123456789ABCDEF"
                print(f"モックカード検出: IDm = {mock_idm}")
                return {
                    "idm": mock_idm,
                    "pmm": "0011223344556677",
                    "type": "FeliCa",
                    "system_code": "0003"
                }
            except KeyboardInterrupt:
                return None
        else:
            # Unix系環境ではselectを使用してタイムアウト実装
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                sys.stdin.readline()
                mock_idm = "0123456789ABCDEF"
                print(f"モックカード検出: IDm = {mock_idm}")
                return {
                    "idm": mock_idm,
                    "pmm": "0011223344556677",
                    "type": "FeliCa",
                    "system_code": "0003"
                }
            else:
                print("タイムアウト: カードが検出されませんでした")
                return None
    
    def _process_tag(self, tag) -> Dict[str, Any]:
        """タグ情報を処理"""
        card_info = {
            "idm": tag.idm.hex().upper() if hasattr(tag, 'idm') else None,
            "pmm": tag.pmm.hex().upper() if hasattr(tag, 'pmm') else None,
            "type": tag.type if hasattr(tag, 'type') else "Unknown",
            "system_code": tag.sys.hex().upper() if hasattr(tag, 'sys') else None
        }
        
        print(f"\nカード検出成功！")
        print(f"種類: {card_info['type']}")
        print(f"IDm: {card_info['idm']}")
        print(f"PMm: {card_info['pmm']}")
        if card_info['system_code']:
            print(f"システムコード: {card_info['system_code']}")
        
        return card_info
    
    def hash_idm(self, idm: str) -> str:
        """IDmをハッシュ化"""
        return hashlib.sha256(
            f"{idm}{config.IDM_HASH_SECRET}".encode()
        ).hexdigest()
    
    def disconnect(self):
        """接続を切断"""
        if self.clf and not self.mock_mode:
            self.clf.close()
            print("\nPaSoRiとの接続を切断しました")
    
    def run_continuous_test(self, count: int = 5):
        """連続読み取りテスト"""
        print(f"\n=== 連続読み取りテスト（{count}回） ===")
        
        success_count = 0
        for i in range(count):
            print(f"\n--- テスト {i + 1}/{count} ---")
            card_info = self.read_card()
            
            if card_info:
                success_count += 1
                idm_hash = self.hash_idm(card_info['idm'])
                print(f"IDmハッシュ: {idm_hash[:16]}...")
            
            if i < count - 1:
                print("カードを一度離してください...")
                time.sleep(2)
        
        print(f"\n=== テスト結果 ===")
        print(f"成功: {success_count}/{count}")
        print(f"成功率: {success_count/count*100:.1f}%")


def main():
    """メイン処理"""
    print("=== PaSoRi RC-S380/RC-S300 動作確認ツール ===\n")
    
    tester = PaSoRiTester()
    
    # 環境チェック
    env_info = tester.check_environment()
    
    # PaSoRi接続
    if not tester.connect_reader():
        if not tester.mock_mode:
            print("\nモックモードで継続しますか？ (y/n): ", end="")
            if input().lower() == 'y':
                tester.mock_mode = True
            else:
                return
    
    try:
        while True:
            print("\n=== メニュー ===")
            print("1. 単発カード読み取り")
            print("2. 連続読み取りテスト")
            print("3. 環境情報表示")
            print("0. 終了")
            print("選択してください: ", end="")
            
            choice = input().strip()
            
            if choice == "1":
                card_info = tester.read_card()
                if card_info:
                    idm_hash = tester.hash_idm(card_info['idm'])
                    print(f"\nIDmハッシュ値（データベース保存用）:")
                    print(f"{idm_hash}")
            
            elif choice == "2":
                print("テスト回数を入力（デフォルト: 5）: ", end="")
                count_input = input().strip()
                count = int(count_input) if count_input.isdigit() else 5
                tester.run_continuous_test(count)
            
            elif choice == "3":
                tester.check_environment()
            
            elif choice == "0":
                print("終了します")
                break
            
            else:
                print("無効な選択です")
    
    except KeyboardInterrupt:
        print("\n\n中断されました")
    
    finally:
        tester.disconnect()


if __name__ == "__main__":
    main()