#!/bin/bash

# macOS用セットアップスクリプト
# RC-S380/RC-S300の環境設定を自動化

echo "🍎 macOS PaSoRi環境セットアップ"
echo "================================"

# Homebrewの確認
check_homebrew() {
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrewがインストールされていません"
        echo "以下のコマンドでインストールしてください:"
        echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        exit 1
    fi
    echo "✅ Homebrew: インストール済み"
}

# 必要なパッケージのインストール
install_packages() {
    echo ""
    echo "📦 必要なパッケージをインストール中..."
    
    # libusb
    if brew list libusb &> /dev/null; then
        echo "✅ libusb: インストール済み"
    else
        echo "📥 libusb をインストール中..."
        brew install libusb
    fi
    
    # Python
    if command -v python3 &> /dev/null; then
        echo "✅ Python3: $(python3 --version)"
    else
        echo "📥 Python3 をインストール中..."
        brew install python@3.11
    fi
}

# Python環境のセットアップ
setup_python() {
    echo ""
    echo "🐍 Python環境をセットアップ中..."
    
    # 仮想環境の作成
    if [ ! -d "venv" ]; then
        echo "📥 仮想環境を作成中..."
        python3 -m venv venv
    fi
    
    # 仮想環境の有効化
    source venv/bin/activate
    
    # pipのアップグレード
    pip install --upgrade pip
    
    # nfcpyのインストール
    echo "📥 nfcpy をインストール中..."
    pip install nfcpy==1.0.4
    
    # 他の依存関係
    if [ -f "requirements.txt" ]; then
        echo "📥 プロジェクトの依存関係をインストール中..."
        pip install -r requirements.txt
    fi
}

# RC-S380/RC-S300の接続テスト
test_pasori() {
    echo ""
    echo "🔌 PaSoRi接続テスト"
    echo "==================="
    
    # Python環境を有効化
    source venv/bin/activate 2>/dev/null || true
    
    # デバイスリストの確認
    echo "📋 USBデバイスをスキャン中..."
    python3 -m nfc 2>&1 | tee nfc_test.log
    
    # 結果の解析
    if grep -q "usb:054c:06c1" nfc_test.log; then
        echo "✅ RC-S380 が検出されました！"
        export PASORI_DEVICE=rcs380
        export PASORI_DEVICE_ID="usb:054c:06c1"
    elif grep -q "usb:054c:06c3" nfc_test.log; then
        echo "✅ RC-S380/P が検出されました！"
        export PASORI_DEVICE=rcs380
        export PASORI_DEVICE_ID="usb:054c:06c3"
    elif grep -q "usb:054c:0dc9" nfc_test.log; then
        echo "✅ RC-S300 が検出されました！"
        export PASORI_DEVICE=rcs300
        export PASORI_DEVICE_ID="usb:054c:0dc9"
    else
        echo "⚠️  PaSoRiが検出されませんでした"
        echo ""
        echo "トラブルシューティング:"
        echo "1. PaSoRiがUSBポートに接続されているか確認"
        echo "2. macOSのセキュリティ設定を確認"
        echo "3. SIPが有効な場合は一時的に無効化を検討"
    fi
    
    rm -f nfc_test.log
}

# SIP関連の情報表示
show_sip_info() {
    echo ""
    echo "🔒 macOS セキュリティ情報"
    echo "========================"
    
    # SIP状態の確認
    if csrutil status | grep -q "enabled"; then
        echo "⚠️  SIP (System Integrity Protection) が有効です"
        echo ""
        echo "RC-S380が認識されない場合の対処法:"
        echo "1. リカバリーモードで起動 (電源ボタン長押し)"
        echo "2. ターミナルで実行: csrutil disable"
        echo "3. 再起動"
        echo "4. PaSoRiテスト後、csrutil enable で再度有効化"
    else
        echo "✅ SIP が無効になっています"
    fi
    
    # macOSバージョンの確認
    echo ""
    echo "📱 macOS バージョン: $(sw_vers -productVersion)"
    echo "🖥️  アーキテクチャ: $(uname -m)"
}

# 環境変数の設定
setup_env() {
    echo ""
    echo "⚙️  環境変数を設定中..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "✅ .env ファイルを作成しました"
    fi
    
    # RC-S380用の設定を追加
    if [ -n "$PASORI_DEVICE_ID" ]; then
        echo ""
        echo "以下を .bashrc または .zshrc に追加してください:"
        echo "export PASORI_DEVICE=$PASORI_DEVICE"
        echo "export PASORI_DEVICE_ID=$PASORI_DEVICE_ID"
    fi
}

# メイン処理
main() {
    echo "開始時刻: $(date)"
    echo ""
    
    check_homebrew
    install_packages
    setup_python
    test_pasori
    show_sip_info
    setup_env
    
    echo ""
    echo "✨ セットアップ完了！"
    echo "====================="
    echo ""
    echo "次のステップ:"
    echo "1. source venv/bin/activate  # 仮想環境を有効化"
    echo "2. python hardware/pasori_test.py  # デバイステスト"
    echo "3. python rc_s380_attendance.py  # 勤怠システム起動"
    echo ""
    echo "終了時刻: $(date)"
}

# スクリプト実行
main