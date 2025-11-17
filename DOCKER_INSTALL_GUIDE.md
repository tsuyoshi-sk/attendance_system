# Docker Desktop インストールガイド

**対象環境:** macOS 15.6.1 (Apple Silicon)

---

## 🚀 インストール手順

### 方法1: 公式サイトからインストール（推奨）

#### ステップ1: ダウンロード

以下のリンクからDocker Desktopをダウンロードしてください：

**Apple Silicon (M1/M2/M3) Mac用:**
https://desktop.docker.com/mac/main/arm64/Docker.dmg

または公式サイト:
https://www.docker.com/products/docker-desktop/

#### ステップ2: インストール

1. ダウンロードした `Docker.dmg` を開く
2. `Docker.app` を `Applications` フォルダにドラッグ＆ドロップ
3. `Applications` フォルダから `Docker` を起動

#### ステップ3: 初回起動

1. Docker Desktopが起動すると、利用規約が表示されます
2. 利用規約に同意（Accept）
3. **推奨設定**を選択（Use recommended settings）
4. macOSのパスワードを入力して、権限を付与

#### ステップ4: 起動確認

Docker Desktopのアイコンがメニューバーに表示されれば起動成功です。

---

### 方法2: ターミナルで手動ダウンロード

```bash
# ダウンロード
curl -L https://desktop.docker.com/mac/main/arm64/Docker.dmg -o ~/Downloads/Docker.dmg

# DMGをマウント
open ~/Downloads/Docker.dmg
```

その後、Finder で `Docker.app` を `Applications` にドラッグ＆ドロップしてください。

---

## ✅ インストール確認

### ステップ1: Docker Desktopを起動

```bash
open -a Docker
```

### ステップ2: 起動を待つ

Docker Desktopの初回起動には30秒〜1分程度かかります。
メニューバーのDockerアイコンが**緑色**になれば準備完了です。

### ステップ3: ターミナルで確認

```bash
# Dockerバージョン確認
docker --version

# 出力例:
# Docker version 24.0.7, build afdd53b

# Docker Composeバージョン確認
docker-compose --version

# 出力例:
# Docker Compose version v2.23.3
```

### ステップ4: 動作テスト

```bash
# Hello Worldコンテナを実行
docker run hello-world

# 成功すると以下のようなメッセージが表示されます:
# Hello from Docker!
# This message shows that your installation appears to be working correctly.
```

---

## 🎯 PWAテストを実行

Dockerが正常にインストールされたら、PWAテストを実行できます。

### クイックスタート

```bash
# プロジェクトルートディレクトリで実行
cd /Users/sakai/attendance_system

# PWAテストを実行
./run_pwa_test.sh
```

このスクリプトは以下を自動実行します:
1. ✅ Dockerイメージのビルド
2. ✅ FastAPIサーバーの起動
3. ✅ PWAテスト実行（53テスト）
4. ✅ HTMLレポート生成
5. ✅ クリーンアップ

### 実行例

```bash
$ ./run_pwa_test.sh

=========================================
  PWAテスト実行 (Docker環境)
=========================================

[1/4] Dockerイメージをビルド中...
✅ ビルド完了

[2/4] 既存のコンテナを停止中...
✅ クリーンアップ完了

[3/4] FastAPIサーバーを起動中...
✅ サーバー起動完了

[4/4] PWAテストを実行中...
=========================================
collecting ... collected 53 items

tests/pwa/test_service_worker.py ✓✓✓✓✓✓✓✓✓✓✓✓✓    [25%]
tests/pwa/test_spa_routing.py ✓✓✓✓✓✓✓✓✓✓✓✓✓✓       [52%]
tests/pwa/test_offline_functionality.py ✓✓✓✓✓✓✓✓✓  [69%]
tests/pwa/test_ui_ux.py ✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓          [100%]

====== 53 passed in 45.23s ======

✅ すべてのテストが成功しました！

📊 テストレポート: test-results/pwa_report.html
=========================================
```

### テスト結果の確認

```bash
# HTMLレポートを開く
open test-results/pwa_report.html
```

---

## 🐛 トラブルシューティング

### 問題1: "Docker Desktop is starting..." が長時間続く

**解決策:**
```bash
# Docker Desktopを再起動
pkill Docker
open -a Docker
```

### 問題2: "Cannot connect to the Docker daemon"

**原因:** Docker Desktopが起動していない

**解決策:**
```bash
# Docker Desktopを起動
open -a Docker

# 起動を待つ（30秒程度）
sleep 30

# 確認
docker ps
```

### 問題3: ポート8000が使用中

**解決策:**
```bash
# 既存のプロセスを停止
pkill -f "uvicorn backend.app.main:app"

# または
lsof -ti:8000 | xargs kill -9
```

### 問題4: ディスク容量不足

Docker Desktopの設定から不要なイメージを削除:

```bash
# 未使用のイメージを削除
docker system prune -a

# 確認
docker system df
```

---

## 📚 Docker Desktop の設定

### 推奨設定

1. **Resources（リソース）:**
   - CPUs: 4以上
   - Memory: 4GB以上
   - Disk: 20GB以上

2. **設定方法:**
   - Docker Desktop を起動
   - メニューバーのアイコンをクリック
   - Settings → Resources で調整

---

## 🔧 高度な設定

### Docker Composeでテスト実行

```bash
# イメージをビルド
docker build -f Dockerfile.pwa-test -t attendance-pwa-test:latest .

# サーバーとテストを起動
docker-compose -f docker-compose.pwa-test.yml up

# クリーンアップ
docker-compose -f docker-compose.pwa-test.yml down
```

### 個別のテストを実行

```bash
# Service Workerテストのみ
docker-compose -f docker-compose.pwa-test.yml run --rm pwa-test \
  pytest tests/pwa/test_service_worker.py -v

# SPAルーティングテストのみ
docker-compose -f docker-compose.pwa-test.yml run --rm pwa-test \
  pytest tests/pwa/test_spa_routing.py -v
```

---

## 📞 サポート

### 公式リソース

- **Docker Desktop 公式ドキュメント:** https://docs.docker.com/desktop/
- **Docker for Mac:** https://docs.docker.com/desktop/install/mac-install/
- **Docker Hub:** https://hub.docker.com/

### よくある質問

**Q: Docker Desktopは無料ですか？**
A: 個人利用や小規模ビジネス（従業員250名未満、年間売上1000万ドル未満）は無料です。

**Q: M1/M2/M3 Macで動きますか？**
A: はい、Apple Silicon用のバージョンがあります。

**Q: アンインストールするには？**
A: Applications フォルダから Docker.app をゴミ箱に移動するだけです。

---

## ✨ 次のステップ

1. ✅ Docker Desktopをインストール
2. ✅ Docker Desktopを起動
3. ✅ `docker --version` で確認
4. ✅ `./run_pwa_test.sh` でPWAテストを実行
5. 📊 `test-results/pwa_report.html` で結果を確認

---

**インストールが完了したら、すぐにPWAテストが実行できます！** 🚀

**© 2025 Attendance System Project - Docker Installation Guide**
