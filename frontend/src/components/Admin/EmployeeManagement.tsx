import React, { useState, useEffect } from 'react';
import { UserPlus, Edit, Trash2, Search, CreditCard, Wifi } from 'lucide-react';
import axios from 'axios';
import { useNFC } from '../../hooks/useNFC';

interface Employee {
  id: number;
  name: string;
  email: string;
  department?: string;
  position?: string;
  nfc_card_id?: string;
  is_active: boolean;
  created_at: string;
}

interface EmployeeFormData {
  name: string;
  email: string;
  department: string;
  position: string;
  nfc_card_id: string;
}

const EmployeeManagement: React.FC = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [formData, setFormData] = useState<EmployeeFormData>({
    name: '',
    email: '',
    department: '',
    position: '',
    nfc_card_id: '',
  });
  const { isScanning, error: nfcError, scanNFC, checkNFCSupport } = useNFC();

  useEffect(() => {
    fetchEmployees();
  }, []);

  const fetchEmployees = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/employees');
      setEmployees(response.data || []);
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingEmployee) {
        // 更新
        await axios.put(`/api/v1/employees/${editingEmployee.id}`, formData);
        alert('従業員情報を更新しました');
      } else {
        // 新規作成
        await axios.post('/api/v1/employees', formData);
        alert('従業員を登録しました');
      }
      resetForm();
      fetchEmployees();
    } catch (error: any) {
      alert(error.response?.data?.detail || '操作に失敗しました');
    }
  };

  const handleEdit = (employee: Employee) => {
    setEditingEmployee(employee);
    setFormData({
      name: employee.name,
      email: employee.email,
      department: employee.department || '',
      position: employee.position || '',
      nfc_card_id: employee.nfc_card_id || '',
    });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('この従業員を削除してもよろしいですか？')) return;

    try {
      await axios.delete(`/api/v1/employees/${id}`);
      alert('従業員を削除しました');
      fetchEmployees();
    } catch (error: any) {
      alert(error.response?.data?.detail || '削除に失敗しました');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      department: '',
      position: '',
      nfc_card_id: '',
    });
    setEditingEmployee(null);
    setShowForm(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleNFCScan = async () => {
    const support = checkNFCSupport();
    if (!support.supported) {
      alert(support.message);
      return;
    }

    try {
      const cardId = await scanNFC();
      if (cardId) {
        setFormData({
          ...formData,
          nfc_card_id: cardId,
        });
        alert(`NFCカードを読み取りました: ${cardId}`);
      }
    } catch (error: any) {
      alert(error.message || 'NFCカードの読み取りに失敗しました');
    }
  };

  const filteredEmployees = employees.filter((emp) =>
    emp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    emp.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* アクションバー */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="従業員を検索..."
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
              {editingEmployee ? '従業員情報の編集' : '新規従業員の登録'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label">氏名 *</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className="input"
                    required
                  />
                </div>
                <div>
                  <label className="label">メールアドレス *</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="input"
                    required
                  />
                </div>
                <div>
                  <label className="label">部署</label>
                  <input
                    type="text"
                    name="department"
                    value={formData.department}
                    onChange={handleChange}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">役職</label>
                  <input
                    type="text"
                    name="position"
                    value={formData.position}
                    onChange={handleChange}
                    className="input"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="label flex items-center gap-2">
                    <CreditCard size={16} />
                    NFCカードID
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      name="nfc_card_id"
                      value={formData.nfc_card_id}
                      onChange={handleChange}
                      className="input flex-1"
                      placeholder="16桁の16進数"
                    />
                    <button
                      type="button"
                      onClick={handleNFCScan}
                      disabled={isScanning}
                      className={`btn ${
                        isScanning
                          ? 'btn-secondary opacity-50 cursor-not-allowed'
                          : 'btn-primary'
                      } flex items-center gap-2 whitespace-nowrap`}
                    >
                      <Wifi size={18} className={isScanning ? 'animate-pulse' : ''} />
                      {isScanning ? 'スキャン中...' : 'カードをスキャン'}
                    </button>
                  </div>
                  {nfcError && (
                    <p className="mt-1 text-xs text-red-600">{nfcError.message}</p>
                  )}
                  <p className="mt-1 text-xs text-slate-500">
                    カードをスキャンするか、手動で入力してください
                  </p>
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button type="submit" className="btn btn-primary">
                  {editingEmployee ? '更新' : '登録'}
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

      {/* 従業員リスト */}
      <div className="card">
        <div className="card-content p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">
            従業員一覧 ({filteredEmployees.length}名)
          </h3>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-slate-600 mt-4">読み込み中...</p>
            </div>
          ) : filteredEmployees.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-600">従業員が見つかりませんでした</p>
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
                      氏名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      メール
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      部署
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      NFCカード
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
                  {filteredEmployees.map((employee) => (
                    <tr key={employee.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        {employee.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-slate-900">{employee.name}</div>
                        <div className="text-sm text-slate-500">{employee.position || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                        {employee.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                        {employee.department || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                        {employee.nfc_card_id ? (
                          <span className="flex items-center gap-1 text-green-600">
                            <CreditCard size={14} />
                            登録済
                          </span>
                        ) : (
                          <span className="text-slate-400">未登録</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            employee.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {employee.is_active ? '有効' : '無効'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleEdit(employee)}
                          className="text-blue-600 hover:text-blue-900 mr-3"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(employee.id)}
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

export default EmployeeManagement;
