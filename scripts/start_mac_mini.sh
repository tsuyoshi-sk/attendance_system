#!/bin/bash
# Mac mini 向け最適化起動スクリプト

set -e

# カラー出力の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🍎 Mac mini 勤怠管理システム起動中...${NC}"
echo ""

# スクリプトのディレクトリに移動
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."

# 仮想環境確認
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  仮想環境を有効化しています...${NC}"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}❌ 仮想環境が見つかりません。先に python3 -m venv venv を実行してください${NC}"
        exit 1
    fi
fi

# 環境確認
echo -e "${BLUE}🔍 環境確認中...${NC}"
python scripts/check_mac_mini_setup.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 環境セットアップに問題があります${NC}"
    exit 1
fi

echo ""

# データベース初期化（必要な場合）
if [ ! -f "data/attendance.db" ]; then
    echo -e "${YELLOW}🗄️  データベースを初期化しています...${NC}"
    python scripts/init_database.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ データベース初期化に失敗しました${NC}"
        exit 1
    fi
fi

# Mac mini 設定の読み込みと表示
echo -e "${BLUE}⚙️  Mac mini 最適化設定:${NC}"
python -c "
import sys
sys.path.insert(0, '.')
try:
    from config.mac_mini_config import MAC_MINI_CONFIG, get_optimal_workers
    print(f'  - ワーカー数: {get_optimal_workers()}')
    print(f'  - 最大接続数: {MAC_MINI_CONFIG[\"MAX_CONNECTIONS\"]}')
    print(f'  - メモリ制限: {MAC_MINI_CONFIG[\"MEMORY_LIMIT\"]}')
except Exception as e:
    print(f'  標準設定を使用します')
"

echo ""

# アプリケーション起動
echo -e "${GREEN}🚀 アプリケーションを起動しています...${NC}"
echo -e "${GREEN}📱 アクセス URL:${NC}"
echo -e "  - ローカル: http://localhost:8000"

# ローカルIPアドレスの取得と表示
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
if [ ! -z "$LOCAL_IP" ]; then
    echo -e "  - ネットワーク: http://${LOCAL_IP}:8000"
fi

echo -e "${GREEN}📚 API ドキュメント:${NC}"
echo -e "  - http://localhost:8000/docs (Swagger UI)"
echo -e "  - http://localhost:8000/redoc (ReDoc)"
echo ""
echo -e "${YELLOW}停止するには Ctrl+C を押してください${NC}"
echo ""

# 起動時のオプション設定
HOST="0.0.0.0"
PORT="8000"
WORKERS="1"  # 開発環境では1ワーカーで十分

# Mac mini 設定が存在する場合は読み込む
if [ -f "config/mac_mini_config.py" ]; then
    WORKERS=$(python -c "
import sys
sys.path.insert(0, '.')
try:
    from config.mac_mini_config import get_optimal_workers
    print(get_optimal_workers())
except:
    print(1)
    ")
fi

# シグナルハンドラー設定
trap cleanup EXIT INT TERM

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 アプリケーションを停止しています...${NC}"
    # 必要に応じてクリーンアップ処理を追加
    exit 0
}

# アプリケーション起動（開発モード）
if [ "$1" == "--production" ]; then
    # プロダクションモード
    echo -e "${YELLOW}⚡ プロダクションモードで起動中...${NC}"
    python -m uvicorn backend.app.main:app \
        --host $HOST \
        --port $PORT \
        --workers $WORKERS \
        --log-level info
else
    # 開発モード（デフォルト）
    echo -e "${BLUE}🔄 開発モード（ホットリロード有効）${NC}"
    python -m uvicorn backend.app.main:app \
        --host $HOST \
        --port $PORT \
        --reload \
        --reload-dir backend \
        --reload-dir config \
        --log-level debug
fi