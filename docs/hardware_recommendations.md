# ハードウェア推奨事項

## FeliCaリーダー選定ガイド

### 推奨モデル: Sony PaSoRi RC-S380

RC-S380は、特にmacOSでの使用において推奨されるモデルです。

#### RC-S380の利点
- **macOS互換性**: nfcpyライブラリとの優れた互換性
- **安定性**: macOS環境での動作実績が豊富
- **性能**: より高速な読み取り速度
- **将来性**: 最新のドライバーサポート

#### 対応デバイス
- iPhone Suica (Express Transit Card)
- Android Suica/モバイルPASMO
- 物理Suica/PASMOカード
- その他FeliCa対応カード

### レガシーサポート: Sony PaSoRi RC-S300

RC-S300も引き続きサポートされていますが、新規導入の場合はRC-S380を推奨します。

#### RC-S300の使用シーン
- 既存システムでRC-S300を使用中の場合
- 特定のレガシーシステムとの互換性が必要な場合
- 在庫の関係でRC-S300のみ利用可能な場合

### セットアップ手順

#### RC-S380のセットアップ
```bash
# 1. ドライバーインストール
pip install nfcpy

# 2. デバイス確認
python felica_reader.py --check

# 3. 動作テスト
python felica_reader.py
```

#### RC-S300のセットアップ（レガシー）
```bash
# 1. ドライバーインストール
pip install nfcpy

# 2. デバイス確認
python felica_reader_rcs300.py --check

# 3. 動作テスト
python felica_reader_rcs300.py
```

### トラブルシューティング

#### macOSでの注意事項
- RC-S380: 追加のドライバー設定は不要
- RC-S300: 一部のmacOSバージョンで認識に時間がかかる場合があります

#### USB権限設定（Linux）
```bash
# udevルール設定
sudo tee /etc/udev/rules.d/99-felica.rules << EOF
# RC-S380 (推奨)
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="06c3", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="0689", MODE="0666"
# RC-S300 (レガシー)
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="01bb", MODE="0666"
EOF

sudo udevadm control --reload-rules
```

### 購入ガイド

#### RC-S380購入時の確認事項
- 型番: RC-S380 または RC-S380/S
- 対応OS: Windows/macOS/Linux対応版
- 付属品: USBケーブル付属

### サポート情報

技術的な質問や問題が発生した場合は、以下を参照してください：
- [nfcpy公式ドキュメント](https://nfcpy.readthedocs.io/)
- プロジェクトのIssueトラッカー
- README_FELICA.mdの詳細ガイド