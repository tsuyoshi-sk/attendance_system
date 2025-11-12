#!/bin/bash

# RC-S380 セットアップスクリプト
# macOS (Apple Silicon) 環境用

echo "🚀 RC-S380 iPhone Suica勤怠管理システム セットアップ"
echo "=================================================="

# 環境チェック
check_environment() {
    echo "📋 環境チェック中..."
    
    # Python バージョンチェック
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "✅ Python バージョン: $python_version"
    
    # Homebrew チェック
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrewがインストールされていません"
        echo "以下のコマンドでインストールしてください:"
        echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        exit 1
    fi
    echo "✅ Homebrew インストール済み"
    
    # ディレクトリ構造チェック
    if [ ! -f "attendance.db" ]; then
        echo "⚠️  attendance.db が見つかりません"
        echo "データベースセットアップを先に実行してください"
    fi
}

# 依存関係のインストール
install_dependencies() {
    echo ""
    echo "📦 依存関係のインストール..."
    
    # libusb のインストール
    if ! brew list libusb &> /dev/null; then
        echo "📥 libusb をインストール中..."
        brew install libusb
    else
        echo "✅ libusb インストール済み"
    fi
    
    # Python パッケージのインストール
    echo "📥 Python パッケージをインストール中..."
    pip3 install --upgrade pip
    pip3 install nfcpy==1.0.4
    pip3 install pyserial
    
    echo "✅ 依存関係のインストール完了"
}

# RC-S380 接続テスト
test_rc_s380() {
    echo ""
    echo "🔌 RC-S380 接続テスト..."
    
    python3 -c "
import nfc
import sys

try:
    # RC-S380の接続を試行
    clf = nfc.ContactlessFrontend('usb:054c:06c1')  # RC-S380/S
    if clf:
        print('✅ RC-S380 接続成功!')
        clf.close()
        sys.exit(0)
except:
    try:
        clf = nfc.ContactlessFrontend('usb:054c:06c3')  # RC-S380/P
        if clf:
            print('✅ RC-S380 接続成功!')
            clf.close()
            sys.exit(0)
    except:
        pass

print('❌ RC-S380 が見つかりません')
print('以下を確認してください:')
print('1. RC-S380 がUSBで接続されているか')
print('2. ドライバが正しくインストールされているか')
print('3. 他のプログラムがデバイスを使用していないか')
sys.exit(1)
"
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "トラブルシューティング:"
        echo "1. RC-S380 を一度抜いて、再度接続してください"
        echo "2. システム環境設定 > セキュリティとプライバシー で許可が必要な場合があります"
        echo "3. 以下のコマンドでデバイスリストを確認:"
        echo "   python3 -m nfc"
        exit 1
    fi
}

# ディレクトリ作成
create_directories() {
    echo ""
    echo "📁 必要なディレクトリを作成中..."
    
    mkdir -p logs
    mkdir -p data/backups
    mkdir -p data/exports
    
    echo "✅ ディレクトリ作成完了"
}

# 権限設定
set_permissions() {
    echo ""
    echo "🔐 権限設定中..."
    
    # スクリプトの実行権限
    chmod +x rc_s380_attendance.py
    chmod +x setup_rc_s380.sh
    
    echo "✅ 権限設定完了"
}

# LaunchAgent 設定（オプション）
setup_launch_agent() {
    echo ""
    read -p "🤖 システム起動時に自動実行しますか？ (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        plist_path="$HOME/Library/LaunchAgents/com.attendance.rc_s380.plist"
        
        cat > "$plist_path" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.attendance.rc_s380</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$(pwd)/rc_s380_attendance.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$(pwd)/logs/rc_s380_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$(pwd)/logs/rc_s380_stderr.log</string>
</dict>
</plist>
EOF
        
        launchctl load "$plist_path"
        echo "✅ 自動起動設定完了"
    fi
}

# メイン処理
main() {
    check_environment
    install_dependencies
    test_rc_s380
    create_directories
    set_permissions
    setup_launch_agent
    
    echo ""
    echo "✨ セットアップ完了!"
    echo "=================================================="
    echo ""
    echo "📱 システムを起動するには:"
    echo "   python3 rc_s380_attendance.py"
    echo ""
    echo "📋 登録済みの iPhone Suica:"
    echo "   - 坂井毅史さん: JE80F5250217373F"
    echo ""
    echo "🎉 RC-S380 にiPhone Suicaをかざして打刻してください!"
}

# スクリプト実行
main