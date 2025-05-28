#!/usr/bin/env python3
"""
簡単な動作確認テスト
"""

import sys
import os
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # src layout uses PYTHONPATH

def test_imports():
    """モジュールのインポートテスト"""
    try:
        print("📋 設定ファイルの読み込み...")
        from config.config import config
        print(f"✅ アプリ名: {config.APP_NAME}")
        print(f"✅ デバッグモード: {config.DEBUG}")
        print(f"✅ PaSoRiモックモード: {config.PASORI_MOCK_MODE}")
        
        print("\n🏗️ データベースモジュールの読み込み...")
        from backend.app.database import Base, engine
        print("✅ データベース設定OK")
        
        print("\n📝 モデルの読み込み...")
        from backend.app.models import Employee, PunchRecord, PunchType
        print("✅ モデル定義OK")
        
        print("\n🔧 サービスの読み込み...")
        from backend.app.services.punch_service import PunchService
        print("✅ 打刻サービスOK")
        
        print("\n📡 カードリーダーの読み込み...")
        from hardware.card_reader import CardReader, CardReaderManager
        print("✅ カードリーダーOK")
        
        print("\n🔒 セキュリティの読み込み...")
        from backend.app.utils.security import InputSanitizer, CryptoUtils
        print("✅ セキュリティ機能OK")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_card_reader():
    """カードリーダーの基本動作テスト"""
    try:
        print("\n📱 カードリーダーのテスト...")
        from hardware.card_reader import CardReader
        
        reader = CardReader()
        print(f"✅ カードリーダー初期化: モックモード={reader.mock_mode}")
        
        if reader.connect():
            print("✅ カードリーダー接続OK")
            
            card_info = reader.read_card_once(timeout=1)
            if card_info:
                print(f"✅ カード読み取りOK: IDm={card_info['idm'][:8]}...")
            else:
                print("⚠️ カード読み取りタイムアウト（正常）")
            
            reader.disconnect()
            print("✅ カードリーダー切断OK")
        else:
            print("❌ カードリーダー接続失敗")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ カードリーダーテストエラー: {e}")
        return False

def test_database():
    """データベースの基本動作テスト"""
    try:
        print("\n🗄️ データベースのテスト...")
        from backend.app.database import init_db, SessionLocal
        
        init_db()
        print("✅ データベース初期化OK")
        
        db = SessionLocal()
        result = db.execute("SELECT 1").scalar()
        db.close()
        
        if result == 1:
            print("✅ データベース接続OK")
            return True
        else:
            print("❌ データベース接続失敗")
            return False
            
    except Exception as e:
        print(f"❌ データベーステストエラー: {e}")
        return False

def test_api_basic():
    """API基本動作テスト"""
    try:
        print("\n🌐 API基本テスト...")
        from backend.app.main import app
        
        print("✅ FastAPIアプリ作成OK")
        
        # 簡単な設定確認
        assert app.title == "勤怠管理システム"
        print("✅ アプリタイトル確認OK")
        
        return True
        
    except Exception as e:
        print(f"❌ APIテストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 勤怠管理システム - 動作確認テスト開始\n")
    
    tests = [
        ("基本インポート", test_imports),
        ("カードリーダー", test_card_reader),
        ("データベース", test_database),
        ("API基本機能", test_api_basic),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {name}テスト実行中...")
        print('='*50)
        
        result = test_func()
        results.append((name, result))
        
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"\n📊 {name}テスト結果: {status}")
    
    print(f"\n{'='*50}")
    print("📋 総合結果")
    print('='*50)
    
    success_count = 0
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if result:
            success_count += 1
    
    total_tests = len(results)
    print(f"\n🎯 成功率: {success_count}/{total_tests} ({(success_count/total_tests)*100:.1f}%)")
    
    if success_count == total_tests:
        print("🎉 すべてのテストが成功しました！")
        return 0
    else:
        print("⚠️ 一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)