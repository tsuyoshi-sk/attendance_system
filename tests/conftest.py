import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import os
import sys

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(scope="session")
def event_loop():
    """asyncio event loop fixture for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_database():
    """Mock database session"""
    return Mock()

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True
    }

@pytest.fixture
def sample_idm_data():
    """Sample NFC IDM data for testing"""
    return "0123456789ABCDEF"

@pytest.fixture
def test_settings():
    """Test environment settings"""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key-64-characters-long-for-testing-purposes"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"