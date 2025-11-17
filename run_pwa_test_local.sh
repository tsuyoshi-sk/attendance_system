#!/bin/bash
# PWAテスト実行スクリプト（ローカル環境版 - Dockerなし）

set -e

echo "========================================="
echo "  PWAテスト実行 (ローカル環境)"
echo "========================================="
echo ""

# カラー定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# テスト結果ディレクトリ作成
mkdir -p test-results

# 既存のサーバープロセスを停止
echo -e "${BLUE}[1/4]${NC} 既存のサーバープロセスを停止中..."
pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✅ クリーンアップ完了${NC}"
echo ""

# 依存関係チェック
echo -e "${BLUE}[2/4]${NC} 依存関係を確認中..."

if ! python -c "import playwright" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Playwrightがインストールされていません${NC}"
    echo -e "${BLUE}インストール中...${NC}"
    pip install pytest-playwright==0.4.3 playwright==1.40.0 pytest-html==4.1.1
    playwright install chromium
fi

echo -e "${GREEN}✅ 依存関係OK${NC}"
echo ""

# サーバー起動
echo -e "${BLUE}[3/4]${NC} FastAPIサーバーを起動中..."
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > /tmp/pwa_test_server.log 2>&1 &
SERVER_PID=$!

echo -e "${YELLOW}⏳ サーバーの起動を待機中...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ サーバー起動完了 (PID: $SERVER_PID)${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ サーバーの起動がタイムアウトしました${NC}"
        echo -e "${RED}ログを確認してください: /tmp/pwa_test_server.log${NC}"
        cat /tmp/pwa_test_server.log
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done
echo ""

# テスト実行
echo -e "${BLUE}[4/4]${NC} PWAテストを実行中..."
echo "========================================="

# PWAテスト実行（エラーを無視して実行）
pytest tests/pwa/ -v --tb=short --color=yes \
    --html=test-results/pwa_report.html \
    --self-contained-html \
    || TEST_EXIT_CODE=$?

# デフォルト値設定（エラーがなければ0）
TEST_EXIT_CODE=${TEST_EXIT_CODE:-0}

echo ""
echo "========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ すべてのテストが成功しました！${NC}"
elif [ $TEST_EXIT_CODE -eq 5 ]; then
    echo -e "${YELLOW}⚠️  テストが見つかりませんでした${NC}"
else
    echo -e "${YELLOW}⚠️  一部のテストが失敗しました (Exit code: $TEST_EXIT_CODE)${NC}"
    echo -e "${BLUE}💡 ヒント: ブラウザ起動エラーの場合は、Dockerの使用を推奨します${NC}"
fi

echo ""
echo -e "${BLUE}📊 テストレポート:${NC} test-results/pwa_report.html"
echo -e "${BLUE}📋 サーバーログ:${NC} /tmp/pwa_test_server.log"
echo ""

# クリーンアップ
echo -e "${BLUE}[クリーンアップ]${NC} サーバーを停止中..."
kill $SERVER_PID 2>/dev/null || true
sleep 1

echo -e "${GREEN}✅ 完了${NC}"
echo "========================================="

# HTMLレポートが存在すれば開く
if [ -f "test-results/pwa_report.html" ]; then
    echo -e "${BLUE}📊 HTMLレポートを開きますか? (y/n)${NC}"
    read -t 5 -n 1 OPEN_REPORT || OPEN_REPORT="n"
    echo ""
    if [ "$OPEN_REPORT" = "y" ] || [ "$OPEN_REPORT" = "Y" ]; then
        open test-results/pwa_report.html 2>/dev/null || \
        xdg-open test-results/pwa_report.html 2>/dev/null || \
        echo "ブラウザで test-results/pwa_report.html を開いてください"
    fi
fi

exit $TEST_EXIT_CODE
