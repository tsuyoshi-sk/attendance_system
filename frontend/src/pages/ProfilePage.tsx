import { useEffect, useState } from 'react';
import { ArrowLeft, Save, User } from 'lucide-react';
import { supabase } from '../lib/supabase';

interface ProfilePageProps {
  session: any;
  onBack: () => void;
}

export default function ProfilePage({ session, onBack }: ProfilePageProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState(session.user.email);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [departments, setDepartments] = useState<any[]>([]);
  const [workPatterns, setWorkPatterns] = useState<any[]>([]);
  const [departmentId, setDepartmentId] = useState('');
  const [workPatternId, setWorkPatternId] = useState('');

  useEffect(() => {
    loadProfile();
    loadDepartments();
    loadWorkPatterns();
  }, []);

  const loadProfile = async () => {
    const { data } = await supabase
      .from('profiles')
      .select('name, department_id, work_pattern_id')
      .eq('id', session.user.id)
      .maybeSingle();

    if (data) {
      setName(data.name || '');
      setDepartmentId(data.department_id || '');
      setWorkPatternId(data.work_pattern_id || '');
    }
  };

  const loadDepartments = async () => {
    const { data } = await supabase.from('departments').select('*').order('name');
    if (data) {
      setDepartments(data);
    }
  };

  const loadWorkPatterns = async () => {
    const { data } = await supabase.from('work_patterns').select('*').order('name');
    if (data) {
      setWorkPatterns(data);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setMessage('');

    try {
      const { data: existingProfile } = await supabase
        .from('profiles')
        .select('id')
        .eq('id', session.user.id)
        .maybeSingle();

      if (existingProfile) {
        const { error } = await supabase
          .from('profiles')
          .update({
            name,
            department_id: departmentId || null,
            work_pattern_id: workPatternId || null,
          })
          .eq('id', session.user.id);

        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('profiles')
          .insert([{
            id: session.user.id,
            name,
            department_id: departmentId || null,
            work_pattern_id: workPatternId || null,
          }]);

        if (error) throw error;
      }

      setMessage('プロフィールを保存しました');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('保存に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-bold text-gray-900">プロフィール設定</h1>
        </div>
      </header>

      <main className="max-w-md mx-auto px-4 py-6">
        <div className="bg-white rounded-2xl shadow-md p-6">
          <div className="flex items-center justify-center mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
              <User className="w-10 h-10 text-white" />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                名前
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="山田 太郎"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                メールアドレス
              </label>
              <input
                type="email"
                value={email}
                disabled
                className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
              />
              <p className="mt-1 text-xs text-gray-500">
                メールアドレスは変更できません
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                所属部署
              </label>
              <select
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">未設定</option>
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                勤務パターン
              </label>
              <select
                value={workPatternId}
                onChange={(e) => setWorkPatternId(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">未設定</option>
                {workPatterns.map((pattern) => (
                  <option key={pattern.id} value={pattern.id}>
                    {pattern.name}
                  </option>
                ))}
              </select>
            </div>

            {message && (
              <div
                className={`p-3 rounded-lg text-sm ${
                  message.includes('失敗')
                    ? 'bg-red-50 text-red-700'
                    : 'bg-green-50 text-green-700'
                }`}
              >
                {message}
              </div>
            )}

            <button
              onClick={handleSave}
              disabled={loading}
              className="w-full py-3 px-4 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Save className="w-5 h-5" />
              {loading ? '保存中...' : '保存'}
            </button>
          </div>
        </div>

        <div className="mt-6 bg-white rounded-2xl shadow-md p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">アカウント情報</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">ユーザーID</span>
              <span className="text-gray-900 font-mono text-xs">
                {session.user.id.slice(0, 8)}...
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">登録日</span>
              <span className="text-gray-900">
                {new Date(session.user.created_at).toLocaleDateString('ja-JP')}
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
