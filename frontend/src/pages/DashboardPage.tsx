import { useEffect, useState } from 'react';
import { ArrowLeft, Calendar, TrendingUp, Edit2, Trash2, Download } from 'lucide-react';
import { supabase } from '../lib/supabase';
import EditRecordModal from '../components/EditRecordModal';

interface DashboardPageProps {
  session: any;
  onBack: () => void;
}

interface DailyRecord {
  id: string;
  date: string;
  check_in: string;
  check_out: string;
  hours: number;
  notes: string;
  rawRecord: any;
}

export default function DashboardPage({ session, onBack }: DashboardPageProps) {
  const [records, setRecords] = useState<DailyRecord[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date());
  const [stats, setStats] = useState({
    totalHours: 0,
    workDays: 0,
    avgHours: 0,
  });
  const [loading, setLoading] = useState(true);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [weeklyStats, setWeeklyStats] = useState<any[]>([]);

  useEffect(() => {
    loadMonthlyRecords();
  }, [selectedMonth]);

  const loadMonthlyRecords = async () => {
    setLoading(true);
    const year = selectedMonth.getFullYear();
    const month = String(selectedMonth.getMonth() + 1).padStart(2, '0');
    const startDate = `${year}-${month}-01`;
    const endDate = `${year}-${month}-31`;

    const { data } = await supabase
      .from('attendance_records')
      .select('*')
      .eq('user_id', session.user.id)
      .gte('date', startDate)
      .lte('date', endDate)
      .order('date', { ascending: false });

    if (data) {
      const dailyRecords: DailyRecord[] = data.map((record) => {
        const checkIn = new Date(record.check_in_time);
        const checkOut = record.check_out_time
          ? new Date(record.check_out_time)
          : new Date();

        const diffMs = checkOut.getTime() - checkIn.getTime();
        const hours = Math.round((diffMs / (1000 * 60 * 60)) * 10) / 10;

        return {
          id: record.id,
          date: record.date,
          check_in: checkIn.toLocaleTimeString('ja-JP', {
            hour: '2-digit',
            minute: '2-digit',
          }),
          check_out: record.check_out_time
            ? checkOut.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
            : '退勤なし',
          hours,
          notes: record.notes || '',
          rawRecord: record,
        };
      });

      setRecords(dailyRecords);

      const totalHours = dailyRecords.reduce((sum, r) => sum + r.hours, 0);
      const workDays = dailyRecords.filter((r) => r.check_out !== '退勤なし').length;

      setStats({
        totalHours: Math.round(totalHours * 10) / 10,
        workDays,
        avgHours: workDays > 0 ? Math.round((totalHours / workDays) * 10) / 10 : 0,
      });

      calculateWeeklyStats(data);
    }

    setLoading(false);
  };

  const handlePreviousMonth = () => {
    setSelectedMonth(
      new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() - 1)
    );
  };

  const handleNextMonth = () => {
    setSelectedMonth(
      new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() + 1)
    );
  };

  const calculateWeeklyStats = (data: any[]) => {
    const weeks: any = {};

    data.forEach((record) => {
      const date = new Date(record.date + 'T00:00:00');
      const weekStart = new Date(date);
      weekStart.setDate(date.getDate() - date.getDay());
      const weekKey = weekStart.toISOString().split('T')[0];

      if (!weeks[weekKey]) {
        weeks[weekKey] = { weekStart, totalHours: 0, days: 0 };
      }

      if (record.check_out_time) {
        const checkIn = new Date(record.check_in_time);
        const checkOut = new Date(record.check_out_time);
        const hours = (checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60);
        weeks[weekKey].totalHours += hours;
        weeks[weekKey].days += 1;
      }
    });

    const weeklyArray = Object.values(weeks)
      .map((week: any) => ({
        weekStart: week.weekStart,
        totalHours: Math.round(week.totalHours * 10) / 10,
        days: week.days,
      }))
      .sort((a: any, b: any) => b.weekStart.getTime() - a.weekStart.getTime())
      .slice(0, 4);

    setWeeklyStats(weeklyArray);
  };

  const handleEditRecord = async (id: string, updates: any) => {
    await supabase
      .from('attendance_records')
      .update({
        ...updates,
        last_modified_by: session.user.id,
      })
      .eq('id', id);

    await loadMonthlyRecords();
  };

  const handleDeleteRecord = async (id: string) => {
    if (confirm('この勤務記録を削除してもよろしいですか？')) {
      await supabase.from('attendance_records').delete().eq('id', id);
      await loadMonthlyRecords();
    }
  };

  const handleExportCSV = () => {
    const csvRows = [
      ['日付', '出勤', '退勤', '勤務時間', 'メモ'],
      ...records.map((r) => [
        r.date,
        r.check_in,
        r.check_out,
        `${r.hours}h`,
        r.notes,
      ]),
    ];

    const csvContent = csvRows.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `勤務記録_${monthString}.csv`;
    link.click();
  };

  const monthString = selectedMonth.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
  });

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
          <h1 className="text-xl font-bold text-gray-900">勤務実績</h1>
          <button
            onClick={handleExportCSV}
            className="ml-auto p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            title="CSVエクスポート"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="bg-white rounded-2xl shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={handlePreviousMonth}
              className="px-3 py-1 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              ← 前月
            </button>
            <h2 className="text-lg font-bold text-gray-900">{monthString}</h2>
            <button
              onClick={handleNextMonth}
              className="px-3 py-1 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              翌月 →
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
              <p className="text-xs text-blue-600 mb-1">合計勤務時間</p>
              <p className="text-2xl font-bold text-blue-900">{stats.totalHours}h</p>
            </div>

            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
              <p className="text-xs text-green-600 mb-1">勤務日数</p>
              <p className="text-2xl font-bold text-green-900">{stats.workDays}日</p>
            </div>

            <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg p-4 border border-amber-200">
              <p className="text-xs text-amber-600 mb-1">平均勤務時間</p>
              <p className="text-2xl font-bold text-amber-900">{stats.avgHours}h</p>
            </div>
          </div>
        </div>

        {weeklyStats.length > 0 && (
          <div className="bg-white rounded-2xl shadow-md p-6 mb-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">週別統計</h3>
            <div className="space-y-3">
              {weeklyStats.map((week, index) => {
                const weekEnd = new Date(week.weekStart);
                weekEnd.setDate(weekEnd.getDate() + 6);
                return (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {week.weekStart.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' })} -{' '}
                        {weekEnd.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' })}
                      </p>
                      <p className="text-xs text-gray-500">{week.days}日勤務</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-indigo-600">{week.totalHours}h</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-md overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-2"></div>
              <p className="text-gray-600">読み込み中...</p>
            </div>
          ) : records.length === 0 ? (
            <div className="p-8 text-center">
              <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-600">この月の勤務記録がありません</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {records.map((record) => (
                <div key={record.date} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">
                      {new Date(record.date + 'T00:00:00').toLocaleDateString('ja-JP', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </h3>
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1 bg-indigo-50 px-3 py-1 rounded-full">
                        <TrendingUp className="w-4 h-4 text-indigo-600" />
                        <span className="text-sm font-semibold text-indigo-700">
                          {record.hours}h
                        </span>
                      </div>
                      <button
                        onClick={() => setEditingRecord(record.rawRecord)}
                        className="p-1.5 hover:bg-indigo-50 rounded transition-colors text-indigo-600"
                        title="編集"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteRecord(record.id)}
                        className="p-1.5 hover:bg-red-50 rounded transition-colors text-red-600"
                        title="削除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  <div className="flex gap-4 text-sm text-gray-600">
                    <span>
                      出勤: <span className="font-medium text-gray-900">{record.check_in}</span>
                    </span>
                    <span>
                      退勤:{' '}
                      <span
                        className={`font-medium ${
                          record.check_out === '退勤なし'
                            ? 'text-orange-600'
                            : 'text-gray-900'
                        }`}
                      >
                        {record.check_out}
                      </span>
                    </span>
                  </div>
                  {record.notes && (
                    <p className="mt-2 text-xs text-gray-500 italic">メモ: {record.notes}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {editingRecord && (
        <EditRecordModal
          record={editingRecord}
          onClose={() => setEditingRecord(null)}
          onSave={handleEditRecord}
        />
      )}
    </div>
  );
}
