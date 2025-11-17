import { useEffect, useState } from 'react';
import { ArrowLeft, Calendar, Plus, X } from 'lucide-react';
import { supabase } from '../lib/supabase';

interface LeaveManagementPageProps {
  session: any;
  onBack: () => void;
}

interface LeaveRequest {
  id: string;
  leave_date: string;
  leave_type: string;
  status: string;
  reason: string;
  created_at: string;
}

export default function LeaveManagementPage({ session, onBack }: LeaveManagementPageProps) {
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [balance, setBalance] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    leave_date: '',
    leave_type: 'annual',
    reason: '',
  });

  useEffect(() => {
    loadLeaves();
    loadBalance();
  }, []);

  const loadLeaves = async () => {
    const { data } = await supabase
      .from('paid_leaves')
      .select('*')
      .eq('user_id', session.user.id)
      .order('leave_date', { ascending: false });

    if (data) {
      setLeaves(data);
    }
  };

  const loadBalance = async () => {
    const { data } = await supabase
      .from('profiles')
      .select('annual_leave_balance')
      .eq('id', session.user.id)
      .maybeSingle();

    if (data) {
      setBalance(data.annual_leave_balance || 0);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { error } = await supabase.from('paid_leaves').insert([
        {
          user_id: session.user.id,
          leave_date: formData.leave_date,
          leave_type: formData.leave_type,
          reason: formData.reason,
          status: 'pending',
        },
      ]);

      if (error) throw error;

      setShowModal(false);
      setFormData({ leave_date: '', leave_type: 'annual', reason: '' });
      await loadLeaves();
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'rejected':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'approved':
        return '承認済み';
      case 'rejected':
        return '却下';
      default:
        return '承認待ち';
    }
  };

  const getLeaveTypeText = (type: string) => {
    switch (type) {
      case 'annual':
        return '年次有給';
      case 'sick':
        return '病気休暇';
      case 'personal':
        return '私用休暇';
      default:
        return 'その他';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <Calendar className="w-6 h-6 text-blue-600" />
              <h1 className="text-xl font-bold text-gray-900">有給休暇管理</h1>
            </div>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="p-2 hover:bg-blue-50 rounded-lg transition-colors text-blue-600"
            title="新規申請"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-sm text-gray-600 mb-2">残り有給日数</h2>
          <p className="text-4xl font-bold text-blue-600">{balance}日</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900">申請履歴</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {leaves.length === 0 ? (
              <div className="p-6 text-center text-gray-500">申請履歴がありません</div>
            ) : (
              leaves.map((leave) => (
                <div key={leave.id} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {new Date(leave.leave_date + 'T00:00:00').toLocaleDateString('ja-JP')}
                      </h3>
                      <p className="text-sm text-gray-600">{getLeaveTypeText(leave.leave_type)}</p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(
                        leave.status
                      )}`}
                    >
                      {getStatusText(leave.status)}
                    </span>
                  </div>
                  {leave.reason && (
                    <p className="text-sm text-gray-600 mt-2">理由: {leave.reason}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    申請日: {new Date(leave.created_at).toLocaleDateString('ja-JP')}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </main>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">有給申請</h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 hover:bg-gray-100 rounded transition-colors text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">日付</label>
                <input
                  type="date"
                  value={formData.leave_date}
                  onChange={(e) => setFormData({ ...formData, leave_date: e.target.value })}
                  min={new Date().toISOString().split('T')[0]}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">種類</label>
                <select
                  value={formData.leave_type}
                  onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="annual">年次有給</option>
                  <option value="sick">病気休暇</option>
                  <option value="personal">私用休暇</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">理由</label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="理由を入力してください"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {loading ? '申請中...' : '申請する'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
