"""
Enhanced Security and Authentication System

Advanced security features including:
- WebSocket token authentication
- Data encryption
- Intrusion detection
- Security event auditing
"""

import os
import secrets
import hashlib
import hmac
import time
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import jwt
from passlib.context import CryptContext
import redis.asyncio as redis
from fastapi import HTTPException, status
import ipaddress
import re
from collections import defaultdict, deque
import base64
import logging

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration"""

    # JWT settings - Load from environment or config
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", None)
    if not JWT_SECRET_KEY:
        # Import from config if available
        try:
            from config.config import settings

            JWT_SECRET_KEY = settings.JWT_SECRET_KEY
        except ImportError:
            # Fallback for development only
            logger.warning(
                "JWT_SECRET_KEY not found in environment or config. Using generated key for development."
            )
            JWT_SECRET_KEY = secrets.token_urlsafe(32)

    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

    # WebSocket token settings
    WS_TOKEN_EXPIRE_MINUTES = 60

    # Encryption settings
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", None)
    if not ENCRYPTION_KEY:
        ENCRYPTION_KEY = Fernet.generate_key()
    else:
        ENCRYPTION_KEY = (
            ENCRYPTION_KEY.encode()
            if isinstance(ENCRYPTION_KEY, str)
            else ENCRYPTION_KEY
        )

    # Password policy
    MIN_PASSWORD_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL = True

    # Rate limiting
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    # IP whitelist/blacklist
    IP_WHITELIST_ENABLED = False
    IP_WHITELIST: Set[str] = set()
    IP_BLACKLIST: Set[str] = set()

    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }


class TokenManager:
    """Enhanced token management"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.fernet = Fernet(SecurityConfig.ENCRYPTION_KEY)

    async def initialize(self):
        """Initialize token manager"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Token manager initialized")

    def generate_websocket_token(
        self, client_id: str, user_id: Optional[str] = None
    ) -> str:
        """Generate secure WebSocket authentication token"""
        payload = {
            "client_id": client_id,
            "user_id": user_id,
            "exp": datetime.utcnow()
            + timedelta(minutes=SecurityConfig.WS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow(),
            "type": "websocket",
            "nonce": secrets.token_urlsafe(16),
        }

        token = jwt.encode(
            payload,
            SecurityConfig.JWT_SECRET_KEY,
            algorithm=SecurityConfig.JWT_ALGORITHM,
        )

        # Store token metadata in Redis
        asyncio.create_task(self._store_token_metadata(token, payload))

        return token

    async def _store_token_metadata(self, token: str, payload: Dict[str, Any]):
        """Store token metadata for tracking"""
        if self.redis_client:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            await self.redis_client.setex(
                f"ws_token:{token_hash}",
                SecurityConfig.WS_TOKEN_EXPIRE_MINUTES * 60,
                json.dumps(
                    {
                        "client_id": payload["client_id"],
                        "user_id": payload.get("user_id"),
                        "created_at": payload["iat"].isoformat(),
                    }
                ),
            )

    async def validate_websocket_token(self, token: str) -> Dict[str, Any]:
        """Validate WebSocket token"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                SecurityConfig.JWT_SECRET_KEY,
                algorithms=[SecurityConfig.JWT_ALGORITHM],
            )

            # Verify token type
            if payload.get("type") != "websocket":
                raise ValueError("Invalid token type")

            # Check if token is blacklisted
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if self.redis_client:
                is_blacklisted = await self.redis_client.exists(
                    f"blacklist:{token_hash}"
                )
                if is_blacklisted:
                    raise ValueError("Token has been revoked")

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )

    async def revoke_token(self, token: str):
        """Revoke a token"""
        if self.redis_client:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            # Add to blacklist with expiration
            await self.redis_client.setex(
                f"blacklist:{token_hash}",
                SecurityConfig.WS_TOKEN_EXPIRE_MINUTES * 60,
                "1",
            )

    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()


class SecurityValidator:
    """Security validation and policy enforcement"""

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """Validate password meets security requirements"""
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

        checks = [
            not SecurityConfig.REQUIRE_UPPERCASE or has_upper,
            not SecurityConfig.REQUIRE_LOWERCASE or has_lower,
            not SecurityConfig.REQUIRE_NUMBERS or has_digit,
            not SecurityConfig.REQUIRE_SPECIAL or has_special,
        ]

        return all(checks)

    @staticmethod
    def validate_nfc_scan_request(request_data: Dict[str, Any]) -> bool:
        """Validate NFC scan request for security"""
        required_fields = ["scan_id", "client_id", "timestamp", "card_data"]

        # Check required fields
        if not all(field in request_data for field in required_fields):
            logger.warning("Missing required fields in NFC scan request")
            return False

        # Validate timestamp (prevent replay attacks)
        try:
            request_time = datetime.fromtimestamp(request_data["timestamp"] / 1000)
            time_diff = abs((datetime.now() - request_time).total_seconds())
            if time_diff > 300:  # 5 minutes
                logger.warning(f"Request timestamp too old: {time_diff} seconds")
                return False
        except Exception as e:
            logger.error(f"Invalid timestamp: {e}")
            return False

        # Validate scan_id format (prevent injection)
        scan_id = request_data["scan_id"]
        if not re.match(r"^[a-zA-Z0-9\-_]{10,64}$", scan_id):
            logger.warning(f"Invalid scan_id format: {scan_id}")
            return False

        # Validate card_data structure
        card_data = request_data.get("card_data", {})
        if not isinstance(card_data, dict) or "idm" not in card_data:
            logger.warning("Invalid card_data structure")
            return False

        return True

    @staticmethod
    def sanitize_input(data: Any, max_length: int = 1000) -> Any:
        """Sanitize input data to prevent injection attacks"""
        if isinstance(data, str):
            # Remove null bytes
            data = data.replace("\x00", "")
            # Limit length
            data = data[:max_length]
            # Remove control characters
            data = "".join(char for char in data if ord(char) >= 32 or char in "\n\r\t")
        elif isinstance(data, dict):
            return {
                k: SecurityValidator.sanitize_input(v, max_length)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [SecurityValidator.sanitize_input(item, max_length) for item in data]

        return data


class IntrusionDetector:
    """Detect and prevent suspicious activities"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None

        # In-memory tracking for performance
        self.request_tracker = defaultdict(lambda: deque(maxlen=100))
        self.failed_attempts = defaultdict(int)
        self.suspicious_patterns = {
            "rapid_requests": {"threshold": 50, "window": 60},  # 50 requests/minute
            "failed_auth": {"threshold": 5, "window": 300},  # 5 failures/5min
            "scan_flood": {"threshold": 20, "window": 60},  # 20 scans/minute
            "invalid_tokens": {"threshold": 10, "window": 300},  # 10 invalid/5min
        }

    async def initialize(self):
        """Initialize intrusion detector"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Intrusion detector initialized")

    async def track_request(
        self, client_id: str, request_type: str, success: bool = True
    ):
        """Track request for anomaly detection"""
        timestamp = time.time()

        # Track in memory
        self.request_tracker[client_id].append(
            {"timestamp": timestamp, "type": request_type, "success": success}
        )

        # Track in Redis for distributed systems
        if self.redis_client:
            key = f"requests:{client_id}:{request_type}"
            await self.redis_client.zadd(key, {str(timestamp): timestamp})
            # Expire old entries
            await self.redis_client.zremrangebyscore(key, 0, timestamp - 3600)
            await self.redis_client.expire(key, 3600)

        # Check for suspicious activity
        if not success:
            self.failed_attempts[client_id] += 1
            await self._check_failed_attempts(client_id)

        await self._check_rate_limits(client_id, request_type)

    async def _check_failed_attempts(self, client_id: str):
        """Check for too many failed attempts"""
        pattern = self.suspicious_patterns["failed_auth"]

        if self.failed_attempts[client_id] >= pattern["threshold"]:
            await self._trigger_security_event(
                client_id,
                "excessive_failed_attempts",
                f"Client {client_id} has {self.failed_attempts[client_id]} failed attempts",
            )
            # Reset counter
            self.failed_attempts[client_id] = 0

    async def _check_rate_limits(self, client_id: str, request_type: str):
        """Check for rate limit violations"""
        pattern_key = "scan_flood" if "scan" in request_type else "rapid_requests"
        pattern = self.suspicious_patterns[pattern_key]

        # Count recent requests
        current_time = time.time()
        window_start = current_time - pattern["window"]

        recent_requests = [
            req
            for req in self.request_tracker[client_id]
            if req["timestamp"] > window_start
        ]

        if len(recent_requests) > pattern["threshold"]:
            await self._trigger_security_event(
                client_id,
                "rate_limit_exceeded",
                f"Client {client_id} exceeded rate limit: {len(recent_requests)} requests in {pattern['window']}s",
            )

    async def _trigger_security_event(
        self, client_id: str, event_type: str, message: str
    ):
        """Trigger security event and take action"""
        logger.warning(f"Security event: {event_type} - {message}")

        # Log to security audit
        await self.log_security_event(
            {
                "client_id": client_id,
                "event_type": event_type,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "severity": "HIGH",
            }
        )

        # Take action based on event type
        if event_type in ["excessive_failed_attempts", "rate_limit_exceeded"]:
            await self.block_client(client_id, duration_minutes=30)

    async def block_client(self, client_id: str, duration_minutes: int = 30):
        """Temporarily block a client"""
        if self.redis_client:
            await self.redis_client.setex(
                f"blocked:{client_id}",
                duration_minutes * 60,
                json.dumps(
                    {
                        "blocked_at": datetime.now().isoformat(),
                        "duration_minutes": duration_minutes,
                    }
                ),
            )
        logger.info(f"Blocked client {client_id} for {duration_minutes} minutes")

    async def is_client_blocked(self, client_id: str) -> bool:
        """Check if client is blocked"""
        if self.redis_client:
            return await self.redis_client.exists(f"blocked:{client_id}") > 0
        return False

    async def detect_suspicious_activity(
        self, request_data: Dict[str, Any]
    ) -> List[str]:
        """Detect various suspicious patterns"""
        warnings = []

        # Check for SQL injection patterns
        sql_patterns = [
            "SELECT",
            "DROP",
            "INSERT",
            "UPDATE",
            "DELETE",
            "--",
            "/*",
            "*/",
            "UNION",
        ]
        data_str = json.dumps(request_data).upper()
        for pattern in sql_patterns:
            if pattern in data_str:
                warnings.append(f"Potential SQL injection pattern detected: {pattern}")

        # Check for XSS patterns
        xss_patterns = [
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
            "eval(",
            "alert(",
        ]
        data_str_lower = json.dumps(request_data).lower()
        for pattern in xss_patterns:
            if pattern in data_str_lower:
                warnings.append(f"Potential XSS pattern detected: {pattern}")

        # Check for path traversal
        if "../" in data_str or "..\\" in data_str:
            warnings.append("Potential path traversal attempt detected")

        # Check for abnormal data sizes
        if len(json.dumps(request_data)) > 10000:
            warnings.append("Abnormally large request data")

        return warnings

    async def log_security_event(self, event: Dict[str, Any]):
        """Log security event for audit trail"""
        if self.redis_client:
            # Store in Redis list
            await self.redis_client.lpush("security_events", json.dumps(event))
            # Keep only last 10000 events
            await self.redis_client.ltrim("security_events", 0, 9999)

        # Also log to file/monitoring system
        logger.info(f"Security event: {json.dumps(event)}")


class SecurityAuditor:
    """Security event auditing and compliance"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.audit_categories = {
            "authentication": ["login", "logout", "token_issued", "token_revoked"],
            "nfc_scanning": ["scan_attempt", "scan_success", "scan_failure"],
            "access_control": ["permission_granted", "permission_denied"],
            "security": ["intrusion_detected", "client_blocked", "suspicious_activity"],
            "data": ["data_accessed", "data_modified", "data_exported"],
        }

    async def initialize(self):
        """Initialize auditor"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Security auditor initialized")

    async def log_nfc_scan_attempt(
        self,
        card_id_hash: str,
        client_id: str,
        success: bool,
        details: Dict[str, Any] = None,
    ):
        """Log NFC scan attempt for audit"""
        event = {
            "category": "nfc_scanning",
            "event_type": "scan_success" if success else "scan_failure",
            "card_id_hash": card_id_hash[:8] + "...",  # Partial hash for privacy
            "client_id": client_id,
            "success": success,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
            "ip_address": details.get("ip_address") if details else None,
        }

        await self._store_audit_event(event)

    async def log_authentication_event(
        self,
        user_id: str,
        event_type: str,
        success: bool,
        details: Dict[str, Any] = None,
    ):
        """Log authentication event"""
        event = {
            "category": "authentication",
            "event_type": event_type,
            "user_id": user_id,
            "success": success,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }

        await self._store_audit_event(event)

    async def log_security_event(
        self, event_type: str, severity: str, details: Dict[str, Any]
    ):
        """Log security event"""
        event = {
            "category": "security",
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }

        await self._store_audit_event(event)

    async def _store_audit_event(self, event: Dict[str, Any]):
        """Store audit event"""
        if self.redis_client:
            # Store in time-series format
            score = time.time()
            await self.redis_client.zadd(
                f"audit:{event['category']}", {json.dumps(event): score}
            )

            # Also store in daily bucket for compliance
            date_key = datetime.now().strftime("%Y-%m-%d")
            await self.redis_client.lpush(f"audit:daily:{date_key}", json.dumps(event))
            await self.redis_client.expire(
                f"audit:daily:{date_key}", 90 * 86400
            )  # 90 days

    async def get_audit_trail(
        self,
        category: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit trail"""
        if not self.redis_client:
            return []

        # Default to last 24 hours
        if not start_time:
            start_time = datetime.now() - timedelta(days=1)
        if not end_time:
            end_time = datetime.now()

        start_score = start_time.timestamp()
        end_score = end_time.timestamp()

        events = []

        if category:
            # Get specific category
            raw_events = await self.redis_client.zrangebyscore(
                f"audit:{category}", start_score, end_score, start=0, num=limit
            )
            events.extend([json.loads(e) for e in raw_events])
        else:
            # Get all categories
            for cat in self.audit_categories:
                raw_events = await self.redis_client.zrangebyscore(
                    f"audit:{cat}",
                    start_score,
                    end_score,
                    start=0,
                    num=limit // len(self.audit_categories),
                )
                events.extend([json.loads(e) for e in raw_events])

        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"], reverse=True)

        return events[:limit]

    async def generate_compliance_report(self, date: datetime) -> Dict[str, Any]:
        """Generate daily compliance report"""
        date_str = date.strftime("%Y-%m-%d")

        # Get all events for the day
        if self.redis_client:
            raw_events = await self.redis_client.lrange(
                f"audit:daily:{date_str}", 0, -1
            )
            events = [json.loads(e) for e in raw_events]
        else:
            events = []

        # Analyze events
        report = {
            "date": date_str,
            "total_events": len(events),
            "events_by_category": defaultdict(int),
            "security_incidents": [],
            "failed_authentications": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "unique_users": set(),
            "unique_clients": set(),
        }

        for event in events:
            category = event.get("category", "unknown")
            report["events_by_category"][category] += 1

            if category == "security" and event.get("severity") in ["HIGH", "CRITICAL"]:
                report["security_incidents"].append(event)

            if category == "authentication" and not event.get("success"):
                report["failed_authentications"] += 1

            if category == "nfc_scanning":
                if event.get("success"):
                    report["successful_scans"] += 1
                else:
                    report["failed_scans"] += 1

            if event.get("user_id"):
                report["unique_users"].add(event["user_id"])
            if event.get("client_id"):
                report["unique_clients"].add(event["client_id"])

        # Convert sets to counts
        report["unique_users"] = len(report["unique_users"])
        report["unique_clients"] = len(report["unique_clients"])
        report["events_by_category"] = dict(report["events_by_category"])

        return report


class SecurityManager:
    """Main security management class"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.token_manager = TokenManager(redis_url)
        self.intrusion_detector = IntrusionDetector(redis_url)
        self.security_auditor = SecurityAuditor(redis_url)
        self.validator = SecurityValidator()

    async def initialize(self):
        """Initialize all security components"""
        await self.token_manager.initialize()
        await self.intrusion_detector.initialize()
        await self.security_auditor.initialize()
        logger.info("Security manager initialized")

    async def authenticate_websocket(
        self, token: str, client_id: str
    ) -> Dict[str, Any]:
        """Authenticate WebSocket connection"""
        try:
            # Validate token
            payload = await self.token_manager.validate_websocket_token(token)

            # Check if client is blocked
            if await self.intrusion_detector.is_client_blocked(client_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Client is temporarily blocked",
                )

            # Track successful authentication
            await self.intrusion_detector.track_request(
                client_id, "ws_auth", success=True
            )
            await self.security_auditor.log_authentication_event(
                payload.get("user_id", "anonymous"),
                "websocket_auth",
                True,
                {"client_id": client_id},
            )

            return payload

        except Exception as e:
            # Track failed authentication
            await self.intrusion_detector.track_request(
                client_id, "ws_auth", success=False
            )
            await self.security_auditor.log_authentication_event(
                "unknown",
                "websocket_auth",
                False,
                {"client_id": client_id, "error": str(e)},
            )
            raise

    async def validate_nfc_request(
        self, request_data: Dict[str, Any], client_id: str
    ) -> bool:
        """Validate and audit NFC scan request"""
        # Check if client is blocked
        if await self.intrusion_detector.is_client_blocked(client_id):
            return False

        # Validate request
        if not self.validator.validate_nfc_scan_request(request_data):
            await self.intrusion_detector.track_request(
                client_id, "nfc_scan", success=False
            )
            return False

        # Check for suspicious patterns
        warnings = await self.intrusion_detector.detect_suspicious_activity(
            request_data
        )
        if warnings:
            await self.security_auditor.log_security_event(
                "suspicious_activity",
                "MEDIUM",
                {"client_id": client_id, "warnings": warnings},
            )

        # Track request
        await self.intrusion_detector.track_request(client_id, "nfc_scan", success=True)

        return True

    def encrypt_card_data(self, card_data: Dict[str, Any]) -> str:
        """Encrypt sensitive card data"""
        json_data = json.dumps(card_data)
        return self.token_manager.encrypt_sensitive_data(json_data)

    def decrypt_card_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt card data"""
        json_data = self.token_manager.decrypt_sensitive_data(encrypted_data)
        return json.loads(json_data)

    async def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        # Get recent security events
        recent_events = await self.security_auditor.get_audit_trail(
            category="security", limit=10
        )

        # Count blocked clients
        blocked_count = 0
        if self.intrusion_detector.redis_client:
            keys = await self.intrusion_detector.redis_client.keys("blocked:*")
            blocked_count = len(keys)

        return {
            "status": "operational",
            "recent_security_events": len(recent_events),
            "blocked_clients": blocked_count,
            "security_level": "high",
            "last_audit": datetime.now().isoformat(),
        }


# Global instance
security_manager = SecurityManager()


# Middleware helpers
async def verify_api_key(api_key: str) -> bool:
    """Verify API key for service-to-service communication"""
    # In production, this would check against a database
    valid_keys = {"development": "dev-key-123", "production": "prod-key-456"}
    return api_key in valid_keys.values()


def generate_api_key() -> str:
    """Generate a new API key"""
    return f"ak_{secrets.token_urlsafe(32)}"


# Encryption helpers
def generate_encryption_key() -> bytes:
    """Generate a new encryption key"""
    return Fernet.generate_key()


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))
