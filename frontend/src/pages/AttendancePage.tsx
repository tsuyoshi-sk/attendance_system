import React, { useState, useEffect } from 'react';
import { Calendar, Clock, Download } from 'lucide-react';
import axios from 'axios';

interface PunchRecord {
  id: number;
  employee_id: number;
  punch_type: string;
  punch_time: string;
  location?: string;
  note?: string;
}

export const AttendancePage: React.FC = () => {
  const [records, setRecords] = useState<PunchRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]
  );

  useEffect(() => {
    fetchAttendanceRecords();
  }, [selectedDate]);

  const fetchAttendanceRecords = async () => {
    try {
      setLoading(true);
      setError(null);

      // 従業員の打刻履歴を取得（仮実装）
      // 実際のAPIエンドポイントに合わせて調整が必要
      const response = await axios.get(`/api/v1/punch/records`, {
        params: { date: selectedDate }
      });

      setRecords(response.data || []);
    } catch (err: any) {
      console.error('Failed to fetch attendance records:', err);
      setError('打刻履歴の取得に失敗しました');
      setRecords([]);
    } finally {
      setLoading(false);
    }
  };

  const getPunchTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      in: '出勤',
      out: '退勤',
      outside: '外出',
      return: '戻り'
    };
    return labels[type] || type;
  };

  const getPunchTypeBadgeClass = (type: string) => {
    const classes: Record<string, string> = {
      in: 'bg-green-100 text-green-800',
      out: 'bg-blue-100 text-blue-800',
      outside: 'bg-yellow-100 text-yellow-800',
      return: 'bg-purple-100 text-purple-800'
    };
    return classes[type] || 'bg-gray-100 text-gray-800';
  };

  const formatTime = (dateTimeString: string) => {
    const date = new Date(dateTimeString);
    return date.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const exportToCSV = () => {
    // CSV出力機能（仮実装）
    alert('CSV出力機能は開発中です');
  };

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">打刻履歴</h1>
          <p className="text-sm text-slate-600 mt-1">
            日々の打刻記録を確認できます
          </p>
        </div>
        <button
          onClick={exportToCSV}
          className="btn btn-secondary flex items-center gap-2"
        >
          <Download size={18} />
          CSV出力
        </button>
      </div>

      {/* 日付選択 */}
      <div className="card">
        <div className="card-content p-6">
          <div className="flex items-center gap-4">
            <Calendar className="text-slate-400" size={20} />
            <label className="label">日付選択</label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="input max-w-xs"
            />
          </div>
        </div>
      </div>

      {/* 打刻記録一覧 */}
      <div className="card">
        <div className="card-content p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Clock size={20} />
            {selectedDate} の打刻記録
          </h2>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-slate-600 mt-4">読み込み中...</p>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">{error}</p>
              <button
                onClick={fetchAttendanceRecords}
                className="btn btn-primary mt-4"
              >
                再試行
              </button>
            </div>
          ) : records.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="mx-auto text-slate-300 mb-4" size={48} />
              <p className="text-slate-600">この日の打刻記録はありません</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      時刻
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      種別
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      場所
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      備考
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                        {formatTime(record.punch_time)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getPunchTypeBadgeClass(
                            record.punch_type
                          )}`}
                        >
                          {getPunchTypeLabel(record.punch_type)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                        {record.location || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {record.note || '-'}
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
