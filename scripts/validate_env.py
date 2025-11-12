#!/usr/bin/env python3
"""
環境設定検証スクリプト

.env.exampleとconfig/config.pyの整合性をチェック
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.config import Settings
    from pydantic import ValidationError
    from dotenv import load_dotenv
except ImportError as e:
    print(f"必要なモジュールがインストールされていません: {e}")
    sys.exit(1)


def validate_env_example():
    """
    .env.exampleの内容でSettingsが正常に初期化できるかテスト
    """
    print("🔍 .env.example の検証を開始...")
    
    # .env.exampleを読み込み
    env_example_path = project_root / ".env.example"
    if not env_example_path.exists():
        print("❌ .env.example が見つかりません")
        return False
    
    # 一時的に環境変数をクリア
    original_env = dict(os.environ)
    
    try:
        # 既存の環境変数をクリア（テスト用）
        for key in list(os.environ.keys()):
            if key.startswith(('JWT_', 'SECRET_', 'IDM_')):
                del os.environ[key]
        
        # .env.exampleを読み込み
        load_dotenv(env_example_path, override=True)
        
        # Settingsインスタンス作成テスト
        settings = Settings()
        
        # 重要な設定項目のチェック
        checks = [
            ("JWT_SECRET_KEY", len(settings.JWT_SECRET_KEY) >= 64, f"長さ: {len(settings.JWT_SECRET_KEY)}"),
            ("SECRET_KEY", len(settings.SECRET_KEY) >= 64, f"長さ: {len(settings.SECRET_KEY)}"),
            ("IDM_HASH_SECRET", len(settings.IDM_HASH_SECRET) >= 8, f"長さ: {len(settings.IDM_HASH_SECRET)}"),
            ("DATABASE_URL", settings.DATABASE_URL.startswith('sqlite'), f"値: {settings.DATABASE_URL}"),
            ("JWT_ALGORITHM", settings.JWT_ALGORITHM == 'HS256', f"値: {settings.JWT_ALGORITHM}"),
        ]
        
        all_passed = True
        for key, condition, detail in checks:
            if condition:
                print(f"✅ {key}: OK ({detail})")
            else:
                print(f"❌ {key}: NG ({detail})")
                all_passed = False
        
        if all_passed:
            print("✅ すべての設定項目が正常です")
            return True
        else:
            print("❌ 一部の設定項目に問題があります")
            return False
            
    except ValidationError as e:
        print(f"❌ Pydantic検証エラー:")
        for error in e.errors():
            print(f"  - {error['loc'][0]}: {error['msg']}")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False
    finally:
        # 環境変数を復元
        os.environ.clear()
        os.environ.update(original_env)


def generate_random_keys():
    """
    本番用のランダムキーを生成
    """
    import secrets
    
    print("\n🔑 本番用ランダムキーの生成...")
    
    keys = {
        "JWT_SECRET_KEY": secrets.token_urlsafe(64),
        "SECRET_KEY": secrets.token_urlsafe(64),
        "IDM_HASH_SECRET": secrets.token_urlsafe(32),
    }
    
    print("以下のキーを本番環境で使用してください:")
    print("=" * 50)
    for key, value in keys.items():
        print(f"{key}={value}")
    print("=" * 50)
    
    return keys


def check_ci_compatibility():
    """
    CI環境での互換性をチェック
    """
    print("\n🚀 CI互換性チェック...")
    
    # CI用のテストキー設定
    test_env = {
        "SECRET_KEY": "test-secret-key-must-be-at-least-64-characters-long-for-comprehensive-testing-extended-version-complete",
        "JWT_SECRET_KEY": "test-jwt-secret-must-be-at-least-64-characters-long-for-comprehensive-testing-extended-version-complete",
        "IDM_HASH_SECRET": "test-idm-hash-secret-must-be-at-least-64-characters-long-for-comprehensive-testing-extended-version",
        "DATABASE_URL": "sqlite:///:memory:",
        "ENVIRONMENT": "testing",
        "PASORI_MOCK_MODE": "true"
    }
    
    # 現在の環境変数を保存
    original_env = dict(os.environ)
    
    try:
        # テスト環境変数を設定
        os.environ.update(test_env)
        
        # Settings作成テスト
        settings = Settings()
        
        print("✅ CI環境での設定は正常です")
        print(f"  - JWT_SECRET_KEY: {len(settings.JWT_SECRET_KEY)}文字")
        print(f"  - SECRET_KEY: {len(settings.SECRET_KEY)}文字")
        print(f"  - Environment: {settings.ENVIRONMENT}")
        
        return True
        
    except Exception as e:
        print(f"❌ CI環境設定エラー: {e}")
        return False
    finally:
        # 環境変数を復元
        os.environ.clear()
        os.environ.update(original_env)


def main():
    """メイン処理"""
    print("🔧 勤怠管理システム環境設定検証ツール")
    print("=" * 50)
    
    success = True
    
    # .env.example検証
    if not validate_env_example():
        success = False
    
    # CI互換性チェック
    if not check_ci_compatibility():
        success = False
    
    # 本番用キー生成
    generate_random_keys()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 検証完了: すべての設定が正常です")
        print("\n次のステップ:")
        print("1. cp .env.example .env")
        print("2. .envファイルの秘密鍵を本番用に変更")
        print("3. python scripts/init_database.py")
        print("4. uvicorn backend.app.main:app --reload")
        sys.exit(0)
    else:
        print("❌ 検証失敗: 設定に問題があります")
        print("上記のエラーを修正してから再実行してください")
        sys.exit(1)


if __name__ == "__main__":
    main()