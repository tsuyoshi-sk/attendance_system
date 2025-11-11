#!/bin/bash

# 勤怠管理システム セットアップスクリプト

set -e  # エラーで停止

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ロゴ表示
echo -e "${BLUE}"
echo "======================================"
echo "   勤怠管理システム セットアップ"
echo "======================================"
echo -e "${NC}"

# 関数定義
print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Python環境チェック
print_step "Python環境をチェックしています..."

# Python 3.8以上が必要
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)
        
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 8 ]; then
            PYTHON_CMD=$cmd
            print_success "Python $VERSION が見つかりました"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    print_error "Python 3.8以上が見つかりません"
    echo "Python 3.8以上をインストールしてください"
    exit 1
fi

# 仮想環境のセットアップ
print_step "仮想環境をセットアップしています..."

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    print_success "仮想環境を作成しました"
else
    print_warning "仮想環境は既に存在します"
fi

# 仮想環境の有効化
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    ACTIVATE_CMD="venv\\Scripts\\activate"
else
    # Unix系
    ACTIVATE_CMD="source venv/bin/activate"
fi

echo -e "\n仮想環境を有効化するには以下のコマンドを実行してください:"
echo -e "${GREEN}$ACTIVATE_CMD${NC}"

# 依存関係のインストール
print_step "依存関係をインストールしています..."

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    venv/Scripts/pip install --upgrade pip
    venv/Scripts/pip install -r requirements.txt
else
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt
fi

print_success "依存関係のインストールが完了しました"

# 必要なディレクトリの作成
print_step "必要なディレクトリを作成しています..."

directories=("data" "logs" "exports")
for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "$dir ディレクトリを作成しました"
    else
        echo "  $dir ディレクトリは既に存在します"
    fi
done

# 環境設定ファイルのセットアップ
print_step "環境設定ファイルをセットアップしています..."

if [ ! -f ".env" ]; then
    if [ -f "config/.env.example" ]; then
        cp config/.env.example .env
        print_success ".envファイルを作成しました"
        print_warning ".envファイルを編集して適切な値を設定してください"
    else
        print_error "config/.env.exampleが見つかりません"
    fi
else
    print_warning ".envファイルは既に存在します"
fi

# データベースの初期化
print_step "データベースを初期化しています..."

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    venv/Scripts/python -c "from backend.app.database import init_db; init_db()"
else
    venv/bin/python -c "from backend.app.database import init_db; init_db()"
fi

print_success "データベースの初期化が完了しました"

# PaSoRi環境のチェック
print_step "PaSoRi環境をチェックしています..."

# nfcpyのインポートテスト
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    NFC_CHECK=$(venv/Scripts/python -c "import nfc; print('OK')" 2>&1)
else
    NFC_CHECK=$(venv/bin/python -c "import nfc; print('OK')" 2>&1)
fi

if [[ "$NFC_CHECK" == "OK" ]]; then
    print_success "nfcpyが正常にインストールされています"
    
    # PaSoRi接続テスト（オプション）
    echo -e "\nPaSoRiの接続テストを実行しますか？ (y/N): \c"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_step "PaSoRiテストを実行しています..."
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            venv/Scripts/python hardware/pasori_test.py
        else
            venv/bin/python hardware/pasori_test.py
        fi
    fi
else
    print_warning "nfcpyのインポートに失敗しました"
    print_warning "PaSoRiはモックモードで動作します"
fi

# 完了メッセージ
echo -e "\n${GREEN}======================================"
echo "   セットアップが完了しました！"
echo "======================================${NC}"

echo -e "\n次のステップ:"
echo "1. 仮想環境を有効化:"
echo -e "   ${GREEN}$ACTIVATE_CMD${NC}"
echo ""
echo "2. 環境変数を設定:"
echo -e "   ${GREEN}編集: .env${NC}"
echo ""
echo "3. アプリケーションを起動:"
echo -e "   ${GREEN}make run${NC} または ${GREEN}make dev${NC}"
echo ""
echo "4. APIドキュメントを確認:"
echo -e "   ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo "5. PaSoRiテストを実行:"
echo -e "   ${GREEN}make hardware-test${NC}"

# システム情報
echo -e "\n${BLUE}システム情報:${NC}"
echo "Python: $($PYTHON_CMD --version)"
echo "OS: $(uname -s)"
echo "プロジェクトパス: $(pwd)"

# 追加の推奨事項
if [ ! -f ".env" ] || grep -q "your-secret-key-change-in-production" .env 2>/dev/null; then
    echo -e "\n${YELLOW}重要: .envファイルのSECRET_KEYとIDM_HASH_SECRETを変更してください${NC}"