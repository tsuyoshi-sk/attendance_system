#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FeliCa（iPhone Suica対応）勤怠システム
物理カード・iPhone Suica・Android Suica 全対応
"""

import time
import json
import requests
from datetime import datetime
from typing import Optional
import logging

try:
    from pafe import Felica
    PAFE_AVAILABLE = True
except ImportError:
    PAFE_AVAILABLE = False
    print("⚠️  pafe未インストール: pip install pafe")

class FeliCaAttendanceReader:
    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.api_base_url = api_base_url
        self.system_code = 0x0003  # Suica/PASMO
        self.service_code = 0x090F  # RC-S300用サービスコード
        self.last_read_idm = None
        self.last_read_time = 0
        self.debounce_seconds = 2  # 重複読み取り防止
        
        if not PAFE_AVAILABLE:
            raise Exception("pafe library not available")
            
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def start_continuous_reading(self):
        """連続読み取りモード開始"""
        self.logger.info("🎯 FeliCa勤怠リーダー開始")
        self.logger.info("📱 iPhone Suica、物理カード対応")
        self.logger.info("🔄 カードをタッチしてください...")
        
        felica = Felica()
        
        try:
            felica.open()
            
            while True:
                try:
                    # FeliCa ポーリング
                    if felica.polling(self.system_code):
                        idm = felica.idm()
                        if idm:
                            idm_hex = idm.hex()
                            self.handle_card_detected(idm_hex)
                    
                    time.sleep(0.3)  # 300ms間隔
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 システム停止")
                    break
                except Exception as e:
                    self.logger.error(f"❌ 読み取りエラー: {e}")
                    time.sleep(1)
                    
        finally:
            felica.close()
    
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
                "reader_id": "felica-reader-001",
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
        
        felica = Felica()
        
        try:
            felica.open()
            
            # 10秒間待機
            for _ in range(100):
                if felica.polling(self.system_code):
                    idm = felica.idm()
                    if idm:
                        idm_hex = idm.hex()
                        self.logger.info(f"📱 カード読み取り: {idm_hex}")
                        
                        # サーバーに登録
                        if self.register_card_to_user(user_id, idm_hex):
                            self.logger.info("✅ カード登録完了")
                            return idm_hex
                        else:
                            self.logger.error("❌ カード登録失敗")
                            return None
                
                time.sleep(0.1)
            
            self.logger.warning("⏰ タイムアウト：カードが検出されませんでした")
            return None
            
        finally:
            felica.close()
    
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

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FeliCa勤怠リーダー")
    parser.add_argument("--url", default="http://localhost:8001", 
                       help="APIサーバーURL")
    parser.add_argument("--register", type=int, metavar="USER_ID",
                       help="新規カード登録モード")
    
    args = parser.parse_args()
    
    reader = FeliCaAttendanceReader(args.url)
    
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