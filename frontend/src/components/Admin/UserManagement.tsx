import React, { useState, useEffect } from 'react';
import { UserPlus, Edit, Trash2, Search, Shield, User as UserIcon } from 'lucide-react';
import axios from 'axios';

interface User {
  id: number;
  username: string;
  role: string;
  employee_id: number | null;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

interface Employee {
  id: number;
  name: string;
}

interface UserFormData {
  username: string;
  password: string;
  role: string;
  employee_id: number | null;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    password: '',
    role: 'user',
    employee_id: null,
  });

  useEffect(() => {
    fetchUsers();
    fetchEmployees();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/users');
      setUsers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchEmployees = async () => {
    try {
      const response = await axios.get('/api/v1/employees');
      setEmployees(response.data || []);
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingUser) {
        // 更新（パスワードが空の場合は更新しない）
        const updateData: any = {
          username: formData.username,
          role: formData.role,
          employee_id: formData.employee_id,
        };
        if (formData.password) {
          updateData.password = formData.password;
        }
        await axios.put(`/api/v1/users/${editingUser.id}`, updateData);
        alert('ユーザー情報を更新しました');
      } else {
        // 新規作成
        await axios.post('/api/v1/users', formData);
        alert('ユーザーを登録しました');
      }
      resetForm();
      fetchUsers();
    } catch (error: any) {
      alert(error.response?.data?.detail || '操作に失敗しました');
    }
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      password: '', // パスワードは空にしておく
      role: user.role,
      employee_id: user.employee_id,
    });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('このユーザーを削除してもよろしいですか？')) return;

    try {
      await axios.delete(`/api/v1/users/${id}`);
      alert('ユーザーを削除しました');
      fetchUsers();
    } catch (error: any) {
      alert(error.response?.data?.detail || '削除に失敗しました');
    }
  };

  const resetForm = () => {
    setFormData({
      username: '',
      password: '',
      role: 'user',
      employee_id: null,
    });
    setEditingUser(null);
    setShowForm(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const value = e.target.name === 'employee_id'
      ? (e.target.value ? parseInt(e.target.value) : null)
      : e.target.value;

    setFormData({
      ...formData,
      [e.target.name]: value,
    });
  };

  const filteredUsers = users.filter((user) =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getEmployeeName = (employeeId: number | null) => {
    if (!employeeId) return '-';
    const employee = employees.find(e => e.id === employeeId);
    return employee ? employee.name : `ID: ${employeeId}`;
  };

  return (
    <div className="space-y-6">
      {/* アクションバー */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="ユーザーを検索..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input pl-10 w-full"
          />
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn btn-primary flex items-center gap-2"
        >
          <UserPlus size={18} />
          新規登録
        </button>
      </div>

      {/* 登録フォーム */}
      {showForm && (
        <div className="card">
          <div className="card-content p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              {editingUser ? 'ユーザー情報の編集' : '新規ユーザーの登録'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label">ユーザー名 *</label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    className="input"
                    required
                  />
                </div>
                <div>
                  <label className="label">
                    パスワード {editingUser ? '(変更する場合のみ入力)' : '*'}
                  </label>
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    className="input"
                    required={!editingUser}
                    placeholder={editingUser ? '変更しない場合は空欄' : ''}
                  />
                </div>
                <div>
                  <label className="label">役割 *</label>
                  <select
                    name="role"
                    value={formData.role}
                    onChange={handleChange}
                    className="input"
                    required
                  >
                    <option value="user">一般ユーザー</option>
                    <option value="admin">管理者</option>
                  </select>
                </div>
                <div>
                  <label className="label">関連従業員</label>
                  <select
                    name="employee_id"
                    value={formData.employee_id || ''}
                    onChange={handleChange}
                    className="input"
                  >
                    <option value="">選択してください</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.name} (ID: {emp.id})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button type="submit" className="btn btn-primary">
                  {editingUser ? '更新' : '登録'}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="btn btn-secondary"
                >
                  キャンセル
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ユーザーリスト */}
      <div className="card">
        <div className="card-content p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">
            ユーザー一覧 ({filteredUsers.length}名)
          </h3>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-slate-600 mt-4">読み込み中...</p>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-600">ユーザーが見つかりませんでした</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      ユーザー名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      役割
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      関連従業員
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      最終ログイン
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      状態
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        {user.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <UserIcon size={16} className="text-slate-400" />
                          <span className="font-medium text-slate-900">{user.username}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex items-center gap-1 text-xs leading-5 font-semibold rounded-full ${
                            user.role === 'admin'
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          <Shield size={12} />
                          {user.role === 'admin' ? '管理者' : '一般'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                        {getEmployeeName(user.employee_id)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                        {user.last_login
                          ? new Date(user.last_login).toLocaleDateString('ja-JP')
                          : '未ログイン'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            user.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {user.is_active ? '有効' : '無効'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleEdit(user)}
                          className="text-blue-600 hover:text-blue-900 mr-3"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(user.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserManagement;
