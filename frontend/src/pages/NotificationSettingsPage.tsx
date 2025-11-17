import { useEffect, useState } from 'react';
import { ArrowLeft, Bell, Save } from 'lucide-react';
import { supabase } from '../lib/supabase';

interface NotificationSettingsPageProps {
  session: any;
  onBack: () => void;
}

export default function NotificationSettingsPage({ session, onBack }: NotificationSettingsPageProps) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [settings, setSettings] = useState({
    check_in_reminder: true,
    check_out_reminder: true,
    overtime_alert: true,
    shift_reminder: true,
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    const { data } = await supabase
      .from('notification_settings')
      .select('*')
      .eq('user_id', session.user.id)
      .maybeSingle();

    if (data) {
      setSettings({
        check_in_reminder: data.check_in_reminder,
        check_out_reminder: data.check_out_reminder,
        overtime_alert: data.overtime_alert,
        shift_reminder: data.shift_reminder,
      });
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setMessage('');

    try {
      const { data: existing } = await supabase
        .from('notification_settings')
        .select('id')
        .eq('user_id', session.user.id)
        .maybeSingle();

      if (existing) {
        const { error } = await supabase
          .from('notification_settings')
          .update(settings)
          .eq('user_id', session.user.id);

        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('notification_settings')
          .insert([{ user_id: session.user.id, ...settings }]);

        if (error) throw error;
      }

      setMessage('設定を保存しました');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('保存に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings({ ...settings, [key]: !settings[key] });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Bell className="w-6 h-6 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">通知設定</h1>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-gray-600 mb-6">
            各種通知の受信設定を管理できます。
          </p>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <div>
                <h3 className="font-semibold text-gray-900">出勤リマインダー</h3>
                <p className="text-sm text-gray-600 mt-1">
                  始業時刻に出勤の通知を受け取ります
                </p>
              </div>
              <button
                onClick={() => toggleSetting('check_in_reminder')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.check_in_reminder ? 'bg-indigo-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.check_in_reminder ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <div>
                <h3 className="font-semibold text-gray-900">退勤リマインダー</h3>
                <p className="text-sm text-gray-600 mt-1">
                  終業時刻に退勤の通知を受け取ります
                </p>
              </div>
              <button
                onClick={() => toggleSetting('check_out_reminder')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.check_out_reminder ? 'bg-indigo-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.check_out_reminder ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <div>
                <h3 className="font-semibold text-gray-900">残業アラート</h3>
                <p className="text-sm text-gray-600 mt-1">
                  残業時間が発生した際に通知を受け取ります
                </p>
              </div>
              <button
                onClick={() => toggleSetting('overtime_alert')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.overtime_alert ? 'bg-indigo-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.overtime_alert ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <div>
                <h3 className="font-semibold text-gray-900">シフトリマインダー</h3>
                <p className="text-sm text-gray-600 mt-1">
                  翌日のシフト開始前に通知を受け取ります
                </p>
              </div>
              <button
                onClick={() => toggleSetting('shift_reminder')}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.shift_reminder ? 'bg-indigo-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.shift_reminder ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          {message && (
            <div
              className={`mt-6 p-3 rounded-lg text-sm ${
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
            className="w-full mt-6 py-3 px-4 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Save className="w-5 h-5" />
            {loading ? '保存中...' : '設定を保存'}
          </button>
        </div>

        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
          <h3 className="font-semibold text-blue-900 mb-2">通知について</h3>
          <p className="text-sm text-blue-700">
            通知機能を有効にするには、ブラウザの通知許可が必要です。
            ブラウザの設定から通知を許可してください。
          </p>
        </div>
      </main>
    </div>
  );
}
