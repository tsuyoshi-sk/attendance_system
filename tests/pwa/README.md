# PWAテスト実行ガイド

このディレクトリには、勤怠管理システムのProgressive Web App (PWA) 機能をテストするための包括的なテストスイートが含まれています。

---

## 🚀 クイックスタート（推奨: Docker）

最も簡単で確実な方法は、**Dockerを使用する**ことです。

### 1. 前提条件

- Docker Desktop がインストールされていること
- プロジェクトルートディレクトリにいること

### 2. テスト実行（ワンコマンド）

```bash
# プロジェクトルートから実行
./run_pwa_test.sh
```

このスクリプトは以下を自動実行します:
1. ✅ Dockerイメージのビルド
2. ✅ FastAPIサーバーの起動
3. ✅ PWAテストの実行
4. ✅ HTMLレポートの生成
5. ✅ クリーンアップ

### 3. テスト結果の確認

```bash
# HTMLレポートをブラウザで開く
open test-results/pwa_report.html
```

---

## 📋 詳細な手順

### 方法1: Docker Composeを使用（推奨）

#### ステップ1: イメージをビルド

```bash
docker build -f Dockerfile.pwa-test -t attendance-pwa-test:latest .
```

#### ステップ2: サーバーとテストを実行

```bash
# サーバー起動
docker-compose -f docker-compose.pwa-test.yml up -d app

# サーバーの起動を待つ（数秒）
sleep 5

# テスト実行
docker-compose -f docker-compose.pwa-test.yml run --rm pwa-test

# クリーンアップ
docker-compose -f docker-compose.pwa-test.yml down
```

#### トラブルシューティング

**サーバーログを確認:**
```bash
docker-compose -f docker-compose.pwa-test.yml logs app
```

**テストログを確認:**
```bash
docker-compose -f docker-compose.pwa-test.yml logs pwa-test
```

**すべてリセット:**
```bash
docker-compose -f docker-compose.pwa-test.yml down -v
docker rmi attendance-pwa-test:latest
```

---

## 🖥️ ローカル環境での実行

Dockerを使わずにローカル環境でテストを実行する方法です。

### 前提条件

```bash
# Python 3.8以上
python --version

# Playwrightインストール
pip install pytest-playwright==0.4.3 playwright==1.40.0 pytest-html==4.1.1

# ブラウザインストール
playwright install chromium
```

### ステップ1: サーバー起動

```bash
# ターミナル1
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### ステップ2: テスト実行

```bash
# ターミナル2
pytest tests/pwa/ -v
```

### オプション

```bash
# HTMLレポート生成
pytest tests/pwa/ -v --html=pwa_report.html --self-contained-html

# 特定のテストのみ実行
pytest tests/pwa/test_service_worker.py -v

# マーカー指定
pytest tests/pwa/ -m service_worker -v

# ヘッドモード（ブラウザを表示）
pytest tests/pwa/ -v --headed

# 別のブラウザで実行
pytest tests/pwa/ --browser firefox -v
pytest tests/pwa/ --browser webkit -v
```

---

## 📊 テスト内容

### 実装済みテスト

| ファイル | テスト数 | 内容 |
|---------|---------|------|
| `test_service_worker.py` | 13 | Service Worker登録、キャッシュ管理、オフライン対応 |
| `test_spa_routing.py` | 14 | SPAルーティング、URL制御、状態管理 |
| `test_offline_functionality.py` | 9 | オフライン動作、キャッシュ戦略、バックグラウンド同期 |
| `test_ui_ux.py` | 17 | レスポンシブデザイン、タッチ操作、アクセシビリティ |

**総計: 53テスト**

### カテゴリ別実行

```bash
# Service Workerテストのみ
pytest tests/pwa/ -m service_worker -v

# オフライン機能テストのみ
pytest tests/pwa/ -m offline -v

# SPAルーティングテストのみ
pytest tests/pwa/ -m spa -v

# UI/UXテストのみ
pytest tests/pwa/ -m ui -v
```

---

## 🐛 トラブルシューティング

### 問題1: Chromiumが起動しない

**エラー:**
```
playwright._impl._errors.TargetClosedError: Target page, context or browser has been closed
```

**解決策:**
1. **Dockerを使用する（最も確実）**
   ```bash
   ./run_pwa_test.sh
   ```

2. **別のブラウザを使用**
   ```bash
   pytest tests/pwa/ --browser firefox -v
   ```

3. **ヘッドレスモードを無効化**
   ```bash
   pytest tests/pwa/ --headed -v
   ```

### 問題2: サーバーに接続できない

**エラー:**
```
playwright._impl._errors.Error: net::ERR_ABORTED at http://localhost:8000/pwa/
```

**解決策:**
```bash
# サーバーが起動しているか確認
curl http://localhost:8000/health

# サーバーを起動
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 問題3: モジュールが見つからない

**エラー:**
```
ModuleNotFoundError: No module named 'playwright'
```

**解決策:**
```bash
# すべての依存関係をインストール
pip install -r requirements.txt

# Playwrightブラウザをインストール
playwright install chromium
```

### 問題4: ポート8000が使用中

**エラー:**
```
Error: [Errno 48] Address already in use
```

**解決策:**
```bash
# 既存のプロセスを停止
pkill -f "uvicorn backend.app.main:app"

# または別のポートを使用
python -m uvicorn backend.app.main:app --port 8001

# テストで使用するポートを変更
export PWA_BASE_URL=http://localhost:8001
pytest tests/pwa/ -v
```

---

## 📖 参考資料

### ドキュメント

- **PWAテスト計画書**: `tests/pwa/PWA_TEST_PLAN.md`
- **PWAテストレポート**: `PWA_TEST_REPORT.md`
- **共通フィクスチャ**: `tests/pwa/conftest.py`

### 外部リンク

- [Playwright Documentation](https://playwright.dev/python/)
- [PWA Best Practices](https://web.dev/progressive-web-apps/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)

---

## 🔧 高度な使い方

### CI/CD統合

#### GitHub Actions

```yaml
name: PWA Tests

on: [push, pull_request]

jobs:
  pwa-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Run PWA Tests
        run: ./run_pwa_test.sh

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: pwa-test-results
          path: test-results/
```

#### GitLab CI

```yaml
pwa-test:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  script:
    - chmod +x run_pwa_test.sh
    - ./run_pwa_test.sh
  artifacts:
    when: always
    paths:
      - test-results/
```

### カスタムフィクスチャの追加

`conftest.py`にカスタムフィクスチャを追加できます:

```python
@pytest.fixture
def custom_viewport():
    """カスタムビューポート"""
    return {"width": 1024, "height": 768}

@pytest.fixture
def authenticated_page(page: Page):
    """認証済みページ"""
    page.goto("http://localhost:8000/pwa/")
    # ログイン処理
    return page
```

### スクリーンショット自動保存

テスト失敗時に自動でスクリーンショットを保存:

```python
@pytest.fixture(autouse=True)
def screenshot_on_failure(request, page: Page):
    yield
    if request.node.rep_call.failed:
        page.screenshot(path=f"test-results/{request.node.name}.png")
```

---

## 💡 ベストプラクティス

1. **Dockerを使用する**: 環境の一貫性が保証される
2. **定期的にテストを実行**: CI/CDに統合して自動化
3. **失敗したテストを調査**: スクリーンショットとログを確認
4. **テストの独立性を保つ**: 各テストが他のテストに依存しない
5. **適切な待機時間**: `wait_for_selector()` を活用

---

## 📞 サポート

問題が発生した場合:

1. **ドキュメントを確認**: `PWA_TEST_PLAN.md` と `PWA_TEST_REPORT.md`
2. **ログを確認**: `docker-compose logs` または `pytest -v -s`
3. **Issueを作成**: GitHubリポジトリでIssueを報告

---

**© 2025 Attendance System Project - PWA Testing Guide**
