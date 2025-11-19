import React, { useState, useEffect } from 'react';
import { User, Mail, Building2, Save, Key } from 'lucide-react';
import PageHeader from '../components/Layout/PageHeader';
import apiClient from '../lib/api';
import { User as UserType } from '../types';

const SettingsPage: React.FC = () => {
  const [user, setUser] = useState<UserType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    department: '',
    position: '',
  });

  useEffect(() => {
    fetchUserProfile();
  }, []);

  const fetchUserProfile = async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.getCurrentUser();
      setUser(data);
      setFormData({
        name: data.name || '',
        email: data.email || '',
        department: data.department || '',
        position: data.position || '',
      });
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await apiClient.updateProfile(formData);
      alert('プロフィールを更新しました');
      await fetchUserProfile();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'プロフィールの更新に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="設定"
        description="ユーザー情報の確認と変更"
      />

      <div className="max-w-3xl">
        {/* プロフィール情報 */}
        <div className="card mb-6">
          <div className="card-header">
            <h2 className="text-lg font-semibold text-slate-900">プロフィール情報</h2>
          </div>
          <div className="card-content p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 従業員ID (読み取り専用) */}
              <div>
                <label className="label">従業員ID</label>
                <div className="relative">
                  <User
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={20}
                  />
                  <input
                    type="text"
                    value={user?.employee_id || ''}
                    className="input pl-11 bg-slate-50"
                    disabled
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  ※ 従業員IDは変更できません
                </p>
              </div>

              {/* 名前 */}
              <div>
                <label className="label">名前</label>
                <div className="relative">
                  <User
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={20}
                  />
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className="input pl-11"
                    required
                  />
                </div>
              </div>

              {/* メールアドレス */}
              <div>
                <label className="label">メールアドレス</label>
                <div className="relative">
                  <Mail
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={20}
                  />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="input pl-11"
                    required
                  />
                </div>
              </div>

              {/* 部署 */}
              <div>
                <label className="label">部署</label>
                <div className="relative">
                  <Building2
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={20}
                  />
                  <input
                    type="text"
                    name="department"
                    value={formData.department}
                    onChange={handleChange}
                    className="input pl-11"
                  />
                </div>
              </div>

              {/* 役職 */}
              <div>
                <label className="label">役職</label>
                <div className="relative">
                  <Building2
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={20}
                  />
                  <input
                    type="text"
                    name="position"
                    value={formData.position}
                    onChange={handleChange}
                    className="input pl-11"
                  />
                </div>
              </div>

              {/* 保存ボタン */}
              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="btn btn-primary"
                >
                  <Save size={18} />
                  <span>{isSaving ? '保存中...' : '変更を保存'}</span>
                </button>
                <button
                  type="button"
                  onClick={fetchUserProfile}
                  className="btn btn-secondary"
                  disabled={isSaving}
                >
                  キャンセル
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* アカウント情報 */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-semibold text-slate-900">アカウント情報</h2>
          </div>
          <div className="card-content p-6 space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Key className="text-slate-600" size={20} />
                <div>
                  <p className="font-medium text-slate-900">パスワード</p>
                  <p className="text-sm text-slate-500">最終更新: 2024/01/01</p>
                </div>
              </div>
              <button className="btn btn-secondary text-sm">変更</button>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium text-slate-900">アカウントタイプ</p>
                <p className="text-sm text-slate-500">
                  {user?.role === 'admin' ? '管理者' : '一般ユーザー'}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium text-slate-900">アカウント作成日</p>
                <p className="text-sm text-slate-500">
                  {user?.created_at
                    ? new Date(user.created_at).toLocaleDateString('ja-JP')
                    : '-'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
