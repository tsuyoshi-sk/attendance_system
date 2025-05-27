#!/usr/bin/env python3
"""
Mac mini 環境セットアップ確認スクリプト
"""
import sys
import subprocess
import sqlite3
import os
from pathlib import Path
import importlib.util

def check_python_version():
    """Python バージョン確認"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python バージョンが不適切: {version}")
        return False

def check_dependencies():
    """依存関係確認"""
    try:
        import fastapi
        import sqlalchemy
        import uvicorn
        import pydantic
        import alembic
        print("✅ 主要依存関係インストール済み")
        
        # バージョン情報も表示
        print(f"   - FastAPI: {fastapi.__version__}")
        print(f"   - SQLAlchemy: {sqlalchemy.__version__}")
        print(f"   - Uvicorn: {uvicorn.__version__}")
        print(f"   - Pydantic: {pydantic.__version__}")
        print(f"   - Alembic: {alembic.__version__}")
        return True
    except ImportError as e:
        print(f"❌ 依存関係エラー: {e}")
        return False

def check_database():
    """データベース確認"""
    try:
        db_path = Path("data/attendance.db")
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"✅ データベース正常 ({len(tables)} テーブル)")
            
            # テーブル名も表示
            for table in tables:
                print(f"   - {table[0]}")
            conn.close()
            return True
        else:
            print("❌ データベースファイルが存在しません")
            return False
    except Exception as e:
        print(f"❌ データベースエラー: {e}")
        return False

def check_env_file():
    """環境設定ファイル確認"""
    try:
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                required_vars = [
                    "SECRET_KEY",
                    "DATABASE_URL",
                    "IDM_HASH_SECRET",
                    "PASORI_MOCK_MODE"
                ]
                found_vars = []
                for line in lines:
                    for var in required_vars:
                        if line.strip().startswith(f"{var}="):
                            found_vars.append(var)
                
                if len(found_vars) == len(required_vars):
                    print("✅ 環境設定ファイル (.env) 正常")
                    return True
                else:
                    missing = set(required_vars) - set(found_vars)
                    print(f"❌ 環境設定ファイルに必須変数が不足: {missing}")
                    return False
        else:
            print("❌ 環境設定ファイル (.env) が存在しません")
            return False
    except Exception as e:
        print(f"❌ 環境設定ファイルエラー: {e}")
        return False

def check_directories():
    """必要なディレクトリ確認"""
    required_dirs = ["data", "logs", "backup", "backend", "config", "scripts"]
    all_exist = True
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✅ ディレクトリ存在: {dir_name}/")
        else:
            print(f"❌ ディレクトリ不足: {dir_name}/")
            all_exist = False
    
    return all_exist

def check_pasori():
    """PaSoRi デバイス確認"""
    try:
        result = subprocess.run(['system_profiler', 'SPUSBDataType'], 
                              capture_output=True, text=True)
        if 'pasori' in result.stdout.lower() or 'rc-s300' in result.stdout.lower():
            print("✅ PaSoRi デバイス検出")
            return True
        else:
            print("⚠️  PaSoRi デバイス未検出（モックモードで動作）")
            return True  # モックモードがあるので警告のみ
    except Exception as e:
        print(f"⚠️  PaSoRi 確認エラー: {e}")
        return True  # モックモードがあるので警告のみ

def check_libusb():
    """libusb インストール確認"""
    try:
        result = subprocess.run(['brew', 'list', 'libusb'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ libusb インストール済み")
            return True
        else:
            print("❌ libusb 未インストール")
            return False
    except Exception as e:
        print(f"⚠️  libusb 確認エラー: {e}")
        return True  # 必須ではないので警告のみ

def check_port_availability():
    """ポート利用可能性確認"""
    import socket
    
    port = 8000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result != 0:
        print(f"✅ ポート {port} 利用可能")
        return True
    else:
        print(f"⚠️  ポート {port} は既に使用中です")
        return True  # 警告のみ

def check_virtual_env():
    """仮想環境確認"""
    if os.environ.get('VIRTUAL_ENV'):
        venv_path = os.environ.get('VIRTUAL_ENV')
        print(f"✅ 仮想環境アクティブ: {venv_path}")
        return True
    else:
        print("⚠️  仮想環境が有効化されていません")
        return True  # 警告のみ

def check_mac_mini_config():
    """Mac mini 設定ファイル確認"""
    config_path = Path("config/mac_mini_config.py")
    if config_path.exists():
        print("✅ Mac mini 最適化設定ファイル存在")
        
        # 設定を読み込んでみる
        try:
            spec = importlib.util.spec_from_file_location("mac_mini_config", config_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            print(f"   - ワーカー数: {module.MAC_MINI_CONFIG['WORKER_COUNT']}")
            print(f"   - 最大接続数: {module.MAC_MINI_CONFIG['MAX_CONNECTIONS']}")
            return True
        except Exception as e:
            print(f"⚠️  設定ファイル読み込みエラー: {e}")
            return True
    else:
        print("⚠️  Mac mini 最適化設定ファイルが存在しません")
        return True  # オプショナルなので警告のみ

def main():
    """メイン処理"""
    print("=== Mac mini 勤怠管理システム環境確認 ===")
    print()
    
    checks = [
        ("Python バージョン", check_python_version),
        ("仮想環境", check_virtual_env),
        ("Python 依存関係", check_dependencies),
        ("環境設定ファイル", check_env_file),
        ("ディレクトリ構造", check_directories),
        ("データベース", check_database),
        ("libusb", check_libusb),
        ("PaSoRi デバイス", check_pasori),
        ("ポート利用可能性", check_port_availability),
        ("Mac mini 設定", check_mac_mini_config),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n【{name}】")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ チェック中にエラー: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    
    # 必須項目のチェック（最初の6項目）
    required_checks = results[:6]
    if all(required_checks):
        print("\n🎉 Mac mini 環境セットアップ完了！")
        print("\nアプリケーション起動コマンド:")
        print("  ./scripts/start_mac_mini.sh")
        print("\nまたは:")
        print("  python -m uvicorn backend.app.main:app --reload --host 0.0.0.0")
        return 0
    else:
        print("\n❌ セットアップに問題があります")
        print("上記のエラーを修正してください")
        return 1

if __name__ == "__main__":
    sys.exit(main())