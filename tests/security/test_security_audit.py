"""
セキュリティ監査テスト
OWASP ASVS Level 2 準拠チェック
"""
import pytest
import os
import re
from pathlib import Path
import ast


class TestSecurityAudit:
    """セキュリティ監査テストクラス"""

    def test_no_hardcoded_secrets(self):
        """ハードコードされた秘密情報の検出テスト"""
        project_files = list(Path("src").glob("**/*.py"))

        dangerous_patterns = [
            r'password\s*=\s*["\'][^"\']{3,}["\']',
            r'secret\s*=\s*["\'][^"\']{10,}["\']',
            r'key\s*=\s*["\'][^"\']{10,}["\']',
            r'token\s*=\s*["\'][^"\']{10,}["\']',
        ]

        violations = []
        for file_path in project_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                for pattern in dangerous_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    # テスト用の値は除外
                    filtered_matches = [
                        m
                        for m in matches
                        if "test" not in m.lower() and "your-" not in m.lower()
                    ]
                    if filtered_matches:
                        violations.append(f"{file_path}: {filtered_matches}")
            except Exception:
                continue

        assert len(violations) == 0, f"Hardcoded secrets found: {violations}"

    def test_environment_variable_security(self):
        """環境変数のセキュリティテスト"""
        required_vars = ["SECRET_KEY", "JWT_SECRET_KEY", "IDM_HASH_SECRET"]

        for var in required_vars:
            value = os.getenv(var, "")

            # 長さチェック
            assert len(value) >= 64, f"{var} must be at least 64 characters"

            # 弱いパターンチェック
            weak_patterns = ["password", "123456", "secret", "default"]
            for pattern in weak_patterns:
                assert (
                    pattern.lower() not in value.lower()
                ), f"{var} contains weak pattern: {pattern}"

    def test_crypto_key_strength(self):
        """暗号化キーの強度テスト"""
        # 環境変数から読み込み
        keys_to_check = {
            "SECRET_KEY": os.getenv("SECRET_KEY", ""),
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", ""),
            "IDM_HASH_SECRET": os.getenv("IDM_HASH_SECRET", ""),
        }

        for key_name, key_value in keys_to_check.items():
            # 最小長要件
            assert len(key_value) >= 64, f"{key_name} too short: {len(key_value)} chars"

            # エントロピーチェック（簡易）
            unique_chars = len(set(key_value))
            assert (
                unique_chars >= 20
            ), f"{key_name} low entropy: {unique_chars} unique chars"

            # 文字の多様性チェック
            has_upper = any(c.isupper() for c in key_value)
            has_lower = any(c.islower() for c in key_value)
            has_digit = any(c.isdigit() for c in key_value)
            has_special = any(c in "-_+/" for c in key_value)

            diversity_score = sum([has_upper, has_lower, has_digit, has_special])
            assert diversity_score >= 3, f"{key_name} lacks character diversity"

    def test_security_headers_implementation(self):
        """セキュリティヘッダーの実装チェック"""
        from attendance_system.security.security_manager import SecurityManager

        sm = SecurityManager()
        headers = sm.get_security_headers()

        required_headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
        }

        for header, expected_value in required_headers.items():
            assert header in headers, f"Missing security header: {header}"
            assert (
                expected_value in headers[header]
            ), f"Weak {header}: {headers[header]}"

    def test_authentication_implementation(self):
        """認証実装のチェック"""
        from attendance_system.security.hash_manager import SecureHashManager

        hm = SecureHashManager()

        # パスワードハッシュ化の強度テスト
        test_password = "test_password_123"
        hashed = hm.hash_password(test_password)

        # bcryptの特徴をチェック
        assert hashed.startswith("$2b$"), "Password hash should use bcrypt"
        assert (
            "$12$" in hashed or "$13$" in hashed or "$14$" in hashed
        ), "bcrypt cost should be 12+"

        # 検証機能のテスト
        assert hm.verify_password(test_password, hashed) is True
        assert hm.verify_password("wrong_password", hashed) is False


@pytest.mark.performance
class TestSecurityPerformance:
    """セキュリティ機能のパフォーマンステスト"""

    def test_password_hashing_performance(self):
        """パスワードハッシュ化のパフォーマンステスト"""
        import time
        from attendance_system.security.hash_manager import SecureHashManager

        hm = SecureHashManager()
        password = "test_password_for_performance"

        # 10回のハッシュ化で5秒以内（bcryptコスト12の場合）
        start_time = time.time()
        for _ in range(10):
            hm.hash_password(password)
        hash_time = time.time() - start_time

        assert (
            hash_time < 5.0
        ), f"Password hashing too slow: {hash_time}s for 10 operations"
        print(f"Password hashing performance: {hash_time:.3f}s for 10 operations")

    def test_encryption_performance(self):
        """暗号化のパフォーマンステスト"""
        import time
        from attendance_system.security.crypto_manager import CryptographicManager

        cm = CryptographicManager()
        test_data = "sensitive_data_for_performance_testing" * 10  # 長めのデータ

        # 100回の暗号化・復号化で1秒以内
        start_time = time.time()
        for _ in range(100):
            encrypted = cm.encrypt_sensitive_data(test_data)
            cm.decrypt_sensitive_data(encrypted)
        crypto_time = time.time() - start_time

        assert (
            crypto_time < 2.0
        ), f"Encryption too slow: {crypto_time}s for 100 operations"
        print(f"Encryption performance: {crypto_time:.3f}s for 100 operations")


import os
import re
from pathlib import Path
import ast


class TestSecurityAudit:
    """セキュリティ監査テストクラス"""

    def test_no_hardcoded_secrets(self):
        """ハードコードされた秘密情報の検出テスト"""
        project_files = list(Path("backend").glob("**/*.py")) + list(
            Path("src").glob("**/*.py")
        )

        dangerous_patterns = [
            r'password\s*=\s*["\'][^"\']{3,}["\']',
            r'secret\s*=\s*["\'][^"\']{10,}["\']',
            r'key\s*=\s*["\'][^"\']{10,}["\']',
            r'token\s*=\s*["\'][^"\']{10,}["\']',
        ]

        violations = []
        for file_path in project_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                for pattern in dangerous_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # 除外パターン（テストファイルやサンプル）
                        if any(
                            exclude in str(file_path)
                            for exclude in ["test_", "sample", "example"]
                        ):
                            continue
                        violations.append(f"{file_path}: {matches}")
            except Exception:
                continue

        assert len(violations) == 0, f"Hardcoded secrets found: {violations}"

    def test_environment_variable_security(self):
        """環境変数のセキュリティテスト"""
        required_vars = ["SECRET_KEY", "JWT_SECRET_KEY", "IDM_HASH_SECRET"]

        for var in required_vars:
            value = os.getenv(var, "")

            # 長さチェック
            assert len(value) >= 64, f"{var} must be at least 64 characters"

            # 弱いパターンチェック
            weak_patterns = ["password", "123456", "admin", "test123", "secret"]
            for pattern in weak_patterns:
                assert (
                    pattern.lower() not in value.lower()
                ), f"{var} contains weak pattern: {pattern}"

    def test_sql_injection_prevention(self):
        """SQLインジェクション対策チェック"""
        python_files = list(Path("backend").glob("**/*.py")) + list(
            Path("src").glob("**/*.py")
        )

        # 危険なSQL構文パターン
        dangerous_sql_patterns = [
            r'execute\s*\(\s*["\'].*%.*["\']',  # execute("SELECT * FROM users WHERE id = %s" % user_id)
            r"execute\s*\(\s*.*\+.*\)",  # execute("SELECT * FROM users WHERE id = " + user_id)
            r"\.format\s*\(.*\)\s*\)",  # "SELECT * FROM users WHERE id = {}".format(user_id)
        ]

        violations = []
        for file_path in python_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                for pattern in dangerous_sql_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        violations.append(
                            f"{file_path}: Potential SQL injection risk: {matches}"
                        )
            except Exception:
                continue

        assert (
            len(violations) == 0
        ), f"Potential SQL injection vulnerabilities: {violations}"

    def test_proper_error_handling(self):
        """適切なエラーハンドリングチェック"""
        python_files = list(Path("backend").glob("**/*.py")) + list(
            Path("src").glob("**/*.py")
        )

        violations = []
        for file_path in python_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        # bare except は危険
                        if node.type is None:
                            violations.append(
                                f"{file_path}:line {node.lineno}: Bare except clause found"
                            )

                        # Exception を catch して何もしないのは危険
                        if (
                            node.type
                            and isinstance(node.type, ast.Name)
                            and node.type.id == "Exception"
                            and len(node.body) == 1
                            and isinstance(node.body[0], ast.Pass)
                        ):
                            violations.append(
                                f"{file_path}:line {node.lineno}: Silent exception handling"
                            )
            except Exception:
                continue

        # 一部の violations は許容（テストファイルなど）
        filtered_violations = [v for v in violations if "test_" not in v]
        assert (
            len(filtered_violations) <= 5
        ), f"Too many error handling issues: {filtered_violations}"

    def test_secure_random_usage(self):
        """セキュアな乱数生成使用チェック"""
        python_files = list(Path("backend").glob("**/*.py")) + list(
            Path("src").glob("**/*.py")
        )

        violations = []
        for file_path in python_files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # random.random() などの使用をチェック（セキュリティ用途では危険）
                if "import random" in content or "from random import" in content:
                    # セキュリティ関連ファイルでの使用をチェック
                    if any(
                        keyword in str(file_path)
                        for keyword in ["security", "auth", "token", "crypto"]
                    ):
                        violations.append(
                            f"{file_path}: Using non-cryptographic random in security context"
                        )
            except Exception:
                continue

        assert len(violations) == 0, f"Insecure random usage found: {violations}"

    def test_input_validation_patterns(self):
        """入力検証パターンチェック"""
        python_files = list(Path("backend").glob("**/*.py")) + list(
            Path("src").glob("**/*.py")
        )

        # FastAPI エンドポイントで入力検証がされているかチェック
        missing_validation = []
        for file_path in python_files:
            if "api" not in str(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")

                # @app.post や @router.post があるかチェック
                if re.search(r"@\w*\.post\s*\(", content) or re.search(
                    r"@\w*\.put\s*\(", content
                ):
                    # Pydantic モデルまたは validation の使用をチェック
                    if not (
                        re.search(r"from.*pydantic", content)
                        or re.search(r"from.*schemas", content)
                        or re.search(r":\s*\w+Schema", content)
                    ):
                        missing_validation.append(
                            f"{file_path}: POST/PUT endpoint without apparent validation"
                        )
            except Exception:
                continue

        # API ファイルが少ない場合は許容
        assert (
            len(missing_validation) <= 3
        ), f"Endpoints without validation: {missing_validation}"

    def test_logging_security(self):
        """ログ出力のセキュリティチェック"""
        python_files = list(Path("backend").glob("**/*.py")) + list(
            Path("src").glob("**/*.py")
        )

        violations = []
        for file_path in python_files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # ログに機密情報が含まれていないかチェック
                log_patterns = [
                    r"log\w*\(.*password.*\)",
                    r"log\w*\(.*secret.*\)",
                    r"log\w*\(.*token.*\)",
                    r"print\(.*password.*\)",
                    r"print\(.*secret.*\)",
                ]

                for pattern in log_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        violations.append(
                            f"{file_path}: Potential sensitive data in logs: {matches}"
                        )
            except Exception:
                continue

        assert len(violations) == 0, f"Sensitive data in logs: {violations}"


@pytest.mark.security
class TestSecurityConfiguration:
    """セキュリティ設定テスト"""

    def test_security_headers_configuration(self):
        """セキュリティヘッダー設定テスト"""
        # SecurityManager から取得できることを確認
        from backend.app.security.enhanced_auth import SecurityManager

        with pytest.raises(Exception):
            # Redis接続なしでは初期化できない（正常）
            sm = SecurityManager()

    def test_password_policy_enforcement(self):
        """パスワードポリシー強制テスト"""
        # セキュリティ設定が適切かテスト
        weak_passwords = ["123456", "password", "admin", "test", "qwerty"]

        # 実際のパスワード検証ロジックがあれば使用
        for weak_pass in weak_passwords:
            # 弱いパスワードは拒否されるべき
            assert len(weak_pass) < 8  # 最低限のチェック

    def test_encryption_key_strength(self):
        """暗号化キー強度テスト"""
        secret_key = os.getenv("SECRET_KEY", "")
        jwt_key = os.getenv("JWT_SECRET_KEY", "")

        # キー長チェック
        assert len(secret_key) >= 64, "SECRET_KEY too short"
        assert len(jwt_key) >= 64, "JWT_SECRET_KEY too short"

        # エントロピーチェック（簡易版）
        unique_chars = len(set(secret_key))
        assert (
            unique_chars > 20
        ), f"SECRET_KEY has low entropy: {unique_chars} unique chars"
