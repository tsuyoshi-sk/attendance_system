#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FeliCa RC-S300専用 勤怠リーダー（レガシー）
nfcpyライブラリ使用版（RC-S380が推奨されますが、RC-S300もサポート）
"""

import time
import json
import requests
from datetime import datetime
from typing import Optional
import logging
import binascii

try:
    import nfc
    NFCPY_AVAILABLE = True
except ImportError:
    NFCPY_AVAILABLE = False
    print("⚠️  nfcpy未インストール: pip install nfcpy")

class RC300AttendanceReader:
    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.api_base_url = api_base_url
        self.last_read_idm = None
        self.last_read_time = 0
        self.debounce_seconds = 2  # 重複読み取り防止
        
        if not NFCPY_AVAILABLE:
            raise Exception("nfcpy library not available")
            
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def start_continuous_reading(self):
        """連続読み取りモード開始"""
        self.logger.info("🎯 RC-S300 FeliCa勤怠リーダー開始（レガシー）")
        self.logger.info("📱 iPhone Suica、物理カード対応")
        self.logger.info("💡 RC-S380の使用を推奨します")
        self.logger.info("🔄 カードをタッチしてください...")
        
        try:
            # RC-S300接続
            clf = nfc.ContactlessFrontend('usb')
            
            while True:
                try:
                    # カード検出待機
                    tag = clf.connect(
                        rdwr={
                            'on-connect': self.on_connect,
                            'on-release': self.on_release
                        }
                    )
                    
                    if tag is None:
                        break
                        
                except KeyboardInterrupt:
                    self.logger.info("🛑 システム停止")
                    break
                except Exception as e:
                    self.logger.error(f"❌ 読み取りエラー: {e}")
                    time.sleep(1)
                    
        finally:
            clf.close()
    
    def on_connect(self, tag):
        """カード接続時の処理"""
        try:
            # FeliCa判定
            if isinstance(tag, nfc.tag.tt3.Type3Tag):
                idm = binascii.hexlify(tag.idm).decode('utf-8').upper()
                self.handle_card_detected(idm)
                
                # ビープ音代わりのログ
                self.logger.info("🔔 カード読み取り成功")
            else:
                self.logger.warning("⚠️  FeliCaカードではありません")
                
        except Exception as e:
            self.logger.error(f"カード処理エラー: {e}")
            
        return True  # Trueを返すとカードを離すまで待機
    
    def on_release(self, tag):
        """カード離脱時の処理"""
        self.logger.debug("カードが離されました")
        time.sleep(0.5)  # 連続読み取り防止
    
    def handle_card_detected(self, idm: str):
        """カード検出時の処理"""
        current_time = time.time()
        
        # 重複読み取り防止
        if (self.last_read_idm == idm and 
            current_time - self.last_read_time < self.debounce_seconds):
            return
        
        self.last_read_idm = idm
        self.last_read_time = current_time
        
        self.logger.info(f"📱 カード検出: {idm}")
        
        # サーバーに送信
        success = self.send_attendance_record(idm)
        
        if success:
            self.logger.info("✅ 勤怠記録成功")
        else:
            self.logger.error("❌ 勤怠記録失敗")
    
    def send_attendance_record(self, idm: str) -> bool:
        """勤怠記録をサーバーに送信"""
        try:
            payload = {
                "felica_idm": idm,
                "timestamp": datetime.utcnow().isoformat(),
                "reader_id": "rcs300-001",
                "method": "felica"
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/felica-attendance",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"👤 {result.get('user_name', '不明')} - {result.get('type', '不明')}")
                return True
            else:
                self.logger.error(f"API エラー: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"通信エラー: {e}")
            return False
    
    def register_new_card(self, user_id: int) -> Optional[str]:
        """新しいカード登録"""
        self.logger.info(f"🆕 ユーザー{user_id}のカード登録開始")
        self.logger.info("📱 カードをタッチしてください...")
        
        try:
            clf = nfc.ContactlessFrontend('usb')
            
            # タイムアウト10秒で待機
            tag = clf.connect(
                rdwr={'on-connect': lambda tag: tag},
                terminate=lambda: time.time() - self.start_time > 10
            )
            
            if tag and isinstance(tag, nfc.tag.tt3.Type3Tag):
                idm = binascii.hexlify(tag.idm).decode('utf-8').upper()
                self.logger.info(f"📱 カード読み取り: {idm}")
                
                # サーバーに登録
                if self.register_card_to_user(user_id, idm):
                    self.logger.info("✅ カード登録完了")
                    return idm
                else:
                    self.logger.error("❌ カード登録失敗")
                    return None
            else:
                self.logger.warning("⏰ タイムアウト：カードが検出されませんでした")
                return None
                
        finally:
            clf.close()
    
    def register_card_to_user(self, user_id: int, idm: str) -> bool:
        """カードをユーザーに紐付け"""
        try:
            payload = {
                "user_id": user_id,
                "felica_idm": idm
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/admin/felica/register",
                json=payload,
                timeout=5
            )
            
            return response.status_code == 200
            
        except requests.exceptions.RequestException:
            return False

def check_device():
    """デバイス接続確認"""
    try:
        clf = nfc.ContactlessFrontend('usb')
        device_info = str(clf.device)
        clf.close()
        print(f"✅ デバイス検出: {device_info}")
        return True
    except Exception as e:
        print(f"❌ デバイスが見つかりません: {e}")
        print("💡 以下を確認してください:")
        print("  - RC-S300がUSB接続されているか")
        print("  - USB権限が適切に設定されているか")
        print("  - 他のプログラムがデバイスを使用していないか")
        print("  - RC-S380の使用を検討してください（macOSで推奨）")
        return False

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RC-S300 FeliCa勤怠リーダー（レガシー）")
    parser.add_argument("--url", default="http://localhost:8001", 
                       help="APIサーバーURL")
    parser.add_argument("--register", type=int, metavar="USER_ID",
                       help="新規カード登録モード")
    parser.add_argument("--check", action="store_true",
                       help="デバイス接続確認")
    
    args = parser.parse_args()
    
    if args.check:
        # デバイスチェックモード
        check_device()
        return
    
    reader = RC300AttendanceReader(args.url)
    reader.start_time = time.time()
    
    if args.register:
        # 登録モード
        idm = reader.register_new_card(args.register)
        if idm:
            print(f"✅ ユーザー{args.register}にカード{idm}を登録しました")
        else:
            print("❌ カード登録に失敗しました")
    else:
        # 連続読み取りモード
        reader.start_continuous_reading()

if __name__ == "__main__":
    main()