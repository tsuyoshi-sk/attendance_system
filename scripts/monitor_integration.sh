#!/bin/bash
# Integration Monitor Script for Terminal D
# 4並行開発の統合状況をリアルタイムで監視

echo "🔗 Terminal D: Integration Monitor Starting..."

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 監視ループ
while true; do
    clear
    echo -e "${BLUE}=== 勤怠管理システム 4並行開発統合状況 ===${NC}"
    echo -e "更新時刻: $(date '+%Y-%m-%d %H:%M:%S')\n"
    
    # Terminal A: 打刻システム
    echo -e "${GREEN}[A] 打刻システム (Claude Code)${NC}"
    if git show-ref --verify --quiet refs/heads/feature/punch-api-system; then
        echo -e "  Branch: feature/punch-api-system"
        echo -e "  最新: $(git log --oneline -1 feature/punch-api-system 2>/dev/null | cut -c1-60)"
        echo -e "  差分: $(git rev-list --count main..feature/punch-api-system 2>/dev/null || echo 0) commits ahead"
    else
        echo -e "  ${YELLOW}Branch not found${NC}"
    fi
    echo ""
    
    # Terminal B: 従業員管理
    echo -e "${GREEN}[B] 従業員管理 (Devin Core)${NC}"
    if git show-ref --verify --quiet refs/heads/feature/employee-management; then
        echo -e "  Branch: feature/employee-management"
        echo -e "  最新: $(git log --oneline -1 feature/employee-management 2>/dev/null | cut -c1-60)"
        echo -e "  差分: $(git rev-list --count main..feature/employee-management 2>/dev/null || echo 0) commits ahead"
    else
        echo -e "  ${YELLOW}Branch not found${NC}"
    fi
    echo ""
    
    # Terminal C: レポート分析
    echo -e "${GREEN}[C] レポート分析 (Cursor Pro)${NC}"
    if git show-ref --verify --quiet refs/heads/feature/report-analytics; then
        echo -e "  Branch: feature/report-analytics"
        echo -e "  最新: $(git log --oneline -1 feature/report-analytics 2>/dev/null | cut -c1-60)"
        echo -e "  差分: $(git rev-list --count main..feature/report-analytics 2>/dev/null || echo 0) commits ahead"
    else
        echo -e "  ${YELLOW}Branch not found${NC}"
    fi
    echo ""
    
    # Terminal D: 統合ハブ
    echo -e "${BLUE}[D] 統合ハブ (ChatGPT Plus)${NC}"
    if git show-ref --verify --quiet refs/heads/feature/integration-hub; then
        echo -e "  Branch: feature/integration-hub"
        echo -e "  最新: $(git log --oneline -1 feature/integration-hub 2>/dev/null | cut -c1-60)"
        echo -e "  差分: $(git rev-list --count main..feature/integration-hub 2>/dev/null || echo 0) commits ahead"
    else
        echo -e "  ${YELLOW}Branch not found${NC}"
    fi
    echo ""
    
    # 統合準備状況
    echo -e "${YELLOW}=== 統合準備状況 ===${NC}"
    
    # 各ブランチとの差分チェック
    if git show-ref --verify --quiet refs/heads/feature/integration-hub; then
        echo -e "統合待ち:"
        for branch in feature/punch-api-system feature/employee-management feature/report-analytics; do
            if git show-ref --verify --quiet refs/heads/$branch; then
                diff_count=$(git rev-list --count feature/integration-hub..$branch 2>/dev/null || echo 0)
                if [ "$diff_count" -gt 0 ]; then
                    echo -e "  ${RED}• $branch: $diff_count commits behind${NC}"
                else
                    echo -e "  ${GREEN}• $branch: 最新${NC}"
                fi
            fi
        done
    fi
    
    echo -e "\n${YELLOW}Press Ctrl+C to exit${NC}"
    echo -e "次回更新: 20秒後..."
    
    # 20秒待機
    sleep 20
done