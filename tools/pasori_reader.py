#!/usr/bin/env python3
"""
PaSoRi カードリーダー連続打刻スクリプト

カードをタップするたびに、in → outside → return → out の順で
自動的に打刻タイプを切り替えてAPIに送信します。

使い方:
    # デフォルト設定で起動
    python tools/pasori_reader.py

    # 環境変数で設定を変更
    API_BASE=http://localhost:8080 API_USER=admin API_PASS=admin123! python tools/pasori_reader.py

必要なパッケージ:
    pip install nfcpy requests
"""

import os
import time
import sys
import json
import requests
import signal
import nfc

# 環境変数から設定を読み込み
API_BASE = os.getenv("API_BASE", "http://localhost:8080")
API_USER = os.getenv("API_USER", "admin")
API_PASS = os.getenv("API_PASS", "admin123!")

# タップの度にこの順で送る
PUNCH_ORDER = ["in", "outside", "return", "out"]
last_idx = -1  # 起動直後は in から

# グローバル変数
token = None
terminate_flag = False


def get_token():
    """APIにログインしてJWTトークンを取得"""
    print(f"[i] ログイン中... (user={API_USER})")
    try:
        r = requests.post(
            f"{API_BASE}/api/v1/auth/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"username": API_USER, "password": API_PASS},
            timeout=10,
        )
        r.raise_for_status()
        token_data = r.json()
        print(f"[i] ログイン成功")
        return token_data["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"[!] ログインエラー: {e}")
        sys.exit(1)


def post_punch(token, card_idm_hex, punch_type):
    """打刻APIにリクエストを送信"""
    payload = {"card_idm": card_idm_hex, "punch_type": punch_type}
    try:
        r = requests.post(
            f"{API_BASE}/api/v1/punch/",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            data=json.dumps(payload),
            timeout=10,
        )
        # 409(重複)や400(遷移不正)はそのまま表示
        return r.status_code, r.text
    except requests.exceptions.RequestException as e:
        return 0, f"Network Error: {e}"


def on_connect(tag):
    """カードがタップされたときのコールバック"""
    global last_idx, token

    try:
        # FeliCa (IDm) を取得
        if hasattr(tag, "idm"):
            idm = tag.idm.hex()  # 例: 0123456789abcdef
        else:
            # FeliCa以外でもIDが取れる場合は fallback
            idm = getattr(tag, "identifier", b"").hex()

        if not idm:
            print("[!] このタグからIDmが取得できませんでした")
            return True

        # 次の打刻タイプを決定
        last_idx = (last_idx + 1) % len(PUNCH_ORDER)
        punch_type = PUNCH_ORDER[last_idx]

        print(f"\n[+] タップ検知: IDm={idm}")
        print(f"    → 打刻タイプ: {punch_type}")

        # API呼び出し
        status, body = post_punch(token, idm, punch_type)

        # レスポンスを整形して表示
        if status == 200:
            try:
                response_json = json.loads(body)
                message = response_json.get("message", "")
                print(f"    ✓ 成功 [{status}]: {message}")
            except json.JSONDecodeError:
                print(f"    ✓ 成功 [{status}]")
        elif status == 409:
            print(f"    ⚠ 重複エラー [{status}]: 3分以上待ってから再試行してください")
        elif status == 400:
            try:
                error_json = json.loads(body)
                error_msg = error_json.get("error", {}).get("message", body)
                print(f"    ✗ エラー [{status}]: {error_msg}")
            except json.JSONDecodeError:
                print(f"    ✗ エラー [{status}]: {body}")
        else:
            print(f"    ✗ エラー [{status}]: {body}")

        # デバウンス（連続タップ防止）
        time.sleep(1.5)

    except Exception as e:
        print(f"[!] 処理中にエラーが発生: {e}")

    return True  # Trueで待ち受け継続


def signal_handler(sig, frame):
    """シグナルハンドラ（Ctrl+C対応）"""
    global terminate_flag
    print("\n\n[i] 終了シグナルを受信しました...")
    terminate_flag = True


def main():
    """メイン処理"""
    global token, terminate_flag

    # シグナルハンドラを設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("PaSoRi カードリーダー連続打刻スクリプト")
    print("=" * 60)
    print(f"API Base URL: {API_BASE}")
    print(f"User: {API_USER}")
    print(f"打刻順序: {' → '.join(PUNCH_ORDER)}")
    print("=" * 60)

    # トークン取得
    token = get_token()

    # 接続文字列の候補（汎用 → RC-S380 → RC-S300）
    candidates = [
        "usb",              # 汎用（自動検出）
        "usb:054c:06c3",    # RC-S380の別バージョン
        "usb:054c:06c1",    # RC-S380
        "usb:054c:0dc9",    # RC-S300
    ]

    clf = None
    for dev in candidates:
        try:
            print(f"[i] デバイス接続試行: {dev}")
            clf = nfc.ContactlessFrontend(dev)
            print(f"[✓] デバイス接続成功: {dev}")
            print(f"[i] リーダー情報: {clf}")
            break
        except Exception as e:
            print(f"[i] 接続失敗 ({dev}): {e}")

    if clf is None:
        print("\n" + "=" * 60)
        print("[✗] PaSoRiリーダーをオープンできませんでした")
        print("=" * 60)
        print("\n対処方法:")
        print("1. USBケーブルが正しく接続されているか確認")
        print("2. nfcpyがインストールされているか確認:")
        print("   pip install nfcpy")
        print("3. macOSの場合、libusbをインストール:")
        print("   brew install libusb")
        print("4. リーダーのアクセス権限を確認:")
        print("   sudo python tools/pasori_reader.py")
        print("5. 対応機種を確認:")
        print("   - RC-S380 (推奨)")
        print("   - RC-S300")
        print("=" * 60)
        sys.exit(1)

    def terminate_callback():
        """終了判定用コールバック"""
        return terminate_flag

    try:
        print("\n" + "=" * 60)
        print("[i] カードをタップしてください（Ctrl+Cで終了）")
        print("=" * 60 + "\n")

        while not terminate_flag:
            # タイムアウト付きでconnect
            # terminate コールバックで終了制御
            try:
                clf.connect(
                    rdwr={
                        "on-connect": on_connect,
                        "on-discover": lambda tag: True  # カード検知時は処理継続
                    },
                    terminate=terminate_callback
                )
            except Exception as e:
                if terminate_flag:
                    break
                print(f"[!] 接続エラー: {e}")
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n[i] 終了します...")
        terminate_flag = True
    except Exception as e:
        print(f"\n[!] 予期しないエラー: {e}")
        terminate_flag = True
    finally:
        if clf:
            try:
                clf.close()
                print("[i] リーダーを閉じました")
            except Exception:
                pass


if __name__ == "__main__":
    main()
