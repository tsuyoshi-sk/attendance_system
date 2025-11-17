#!/bin/bash
# PWAテスト実行スクリプト

set -e

echo "========================================="
echo "  PWAテスト実行 (Docker環境)"
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

echo -e "${BLUE}[1/4]${NC} Dockerイメージをビルド中..."
docker build -f Dockerfile.pwa-test -t attendance-pwa-test:latest . || {
    echo -e "${RED}❌ ビルドに失敗しました${NC}"
    exit 1
}

echo -e "${GREEN}✅ ビルド完了${NC}"
echo ""

echo -e "${BLUE}[2/4]${NC} 既存のコンテナを停止中..."
docker-compose -f docker-compose.pwa-test.yml down 2>/dev/null || true
echo -e "${GREEN}✅ クリーンアップ完了${NC}"
echo ""

echo -e "${BLUE}[3/4]${NC} FastAPIサーバーを起動中..."
docker-compose -f docker-compose.pwa-test.yml up -d app

# サーバーの起動を待機
echo -e "${YELLOW}⏳ サーバーの起動を待機中...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ サーバー起動完了${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ サーバーの起動がタイムアウトしました${NC}"
        docker-compose -f docker-compose.pwa-test.yml logs app
        docker-compose -f docker-compose.pwa-test.yml down
        exit 1
    fi
    sleep 1
done
echo ""

echo -e "${BLUE}[4/4]${NC} PWAテストを実行中..."
echo "========================================="
docker-compose -f docker-compose.pwa-test.yml run --rm pwa-test

TEST_EXIT_CODE=$?

echo ""
echo "========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ すべてのテストが成功しました！${NC}"
else
    echo -e "${RED}❌ テストが失敗しました (Exit code: $TEST_EXIT_CODE)${NC}"
fi

echo ""
echo -e "${BLUE}📊 テストレポート:${NC} test-results/pwa_report.html"
echo ""

# クリーンアップ
echo -e "${BLUE}[クリーンアップ]${NC} コンテナを停止中..."
docker-compose -f docker-compose.pwa-test.yml down

echo -e "${GREEN}✅ 完了${NC}"
echo "========================================="

exit $TEST_EXIT_CODE
