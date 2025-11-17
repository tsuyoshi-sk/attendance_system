import React, { useState } from 'react';
import { Lock, User, AlertCircle } from 'lucide-react';
import apiClient from '../lib/api';

interface LoginPageProps {
  onLoginSuccess: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await apiClient.login(username, password);
      onLoginSuccess();
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'ログインに失敗しました。もう一度お試しください。'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-slate-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* ロゴ・ヘッダー */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 text-white mb-4 shadow-lg">
            <Lock size={32} />
          </div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">勤怠管理システム</h1>
          <p className="text-slate-600">Attendance Management System</p>
        </div>

        {/* ログインフォーム */}
        <div className="card shadow-xl">
          <div className="card-content p-8">
            <h2 className="text-xl font-semibold text-slate-900 mb-6">ログイン</h2>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="label">
                  ユーザーID
                </label>
                <div className="relative">
                  <User
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={20}
                  />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="input pl-11"
                    placeholder="test_user"
                    required
                    autoComplete="username"
                  />
                </div>
              </div>

              <div>
                <label className="label">
                  パスワード
                </label>
                <div className="relative">
                  <Lock
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={20}
                  />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input pl-11"
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="btn btn-primary w-full py-3 text-base font-semibold shadow-lg"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>ログイン中...</span>
                  </div>
                ) : (
                  'ログイン'
                )}
              </button>
            </form>

            {/* デモ用の説明 */}
            <div className="mt-6 pt-6 border-t border-slate-100">
              <p className="text-xs text-slate-500 text-center">
                テスト用アカウント: test_admin / test123
              </p>
            </div>
          </div>
        </div>

        {/* フッター */}
        <div className="mt-8 text-center text-sm text-slate-500">
          © 2024 Attendance System. All rights reserved.
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
