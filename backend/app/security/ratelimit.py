"""
レート制限設定

slowapi の Limiter インスタンスをアプリ全体で共有する。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
