#!/bin/bash

echo "🎯 FeliCa勤怠システムセットアップ"

# 1. Python依存関係インストール
echo "📦 依存関係インストール中..."
pip install requests pyusb

# RC-S380用（nfcpy） - macOSで推奨
echo "📦 RC-S380用ライブラリ（nfcpy）インストール..."
pip install nfcpy

# RC-S300用（pafe）- レガシーオプション
echo "📦 RC-S300用ライブラリ（pafe）インストール（レガシーオプション）..."
pip install pafe || echo "ℹ️  pafeのインストールはスキップされました"

# 2. USB権限設定 (Linux/macOS)
echo "🔧 USB権限設定..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux用udev rules
    sudo tee /etc/udev/rules.d/99-felica.rules > /dev/null <<EOF
# FeliCa PaSoRi RC-S380 (推奨)
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="06c3", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="0689", MODE="0666"
# FeliCa PaSoRi RC-S300 (レガシー)
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="01bb", MODE="0666"
EOF
    sudo udevadm control --reload-rules
    echo "✅ Linux udev設定完了"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ macOS: 追加設定不要"
fi

# 3. データベースマイグレーション
echo "🗄️ データベーステーブル作成..."
cd /Users/sakaitakeshishi/attendance_system
PYTHONPATH=src python3 -c "
from src.attendance_system.models.felica import *
from src.attendance_system.database import engine
Base.metadata.create_all(bind=engine)
print('✅ FeliCaテーブル作成完了')
"

# 4. テスト実行
echo "🧪 FeliCaリーダーテスト..."
python3 felica_reader.py --help

echo "🎯 セットアップ完了！"
echo ""
echo "📱 使用方法:"
echo "  勤怠記録: python3 felica_reader.py"
echo "  カード登録: python3 felica_reader.py --register USER_ID"
echo ""
echo "🛒 必要ハードウェア:"
echo "  - Sony PaSoRi RC-S380 (USB FeliCaリーダー - macOSで推奨)"
echo "  - 物理Suica/PASMO または iPhone Suica"