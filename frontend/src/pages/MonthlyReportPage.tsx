import { useEffect, useState } from 'react';
import { ArrowLeft, FileText, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { supabase } from '../lib/supabase';

interface MonthlyReportPageProps {
  session: any;
  onBack: () => void;
}

interface MonthlyStats {
  totalDays: number;
  totalHours: number;
  overtimeHours: number;
  lateDays: number;
  earlyLeaveDays: number;
  averageHours: number;
}

export default function MonthlyReportPage({ session, onBack }: MonthlyReportPageProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [stats, setStats] = useState<MonthlyStats>({
    totalDays: 0,
    totalHours: 0,
    overtimeHours: 0,
    lateDays: 0,
    earlyLeaveDays: 0,
    averageHours: 0,
  });
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMonthlyData();
  }, [currentMonth]);

  const loadMonthlyData = async () => {
    setLoading(true);
    const year = currentMonth.getFullYear();
    const month = String(currentMonth.getMonth() + 1).padStart(2, '0');
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
      setRecords(data);

      let totalHours = 0;
      let overtimeHours = 0;
      let lateDays = 0;
      let earlyLeaveDays = 0;

      data.forEach((record) => {
        if (record.check_out_time) {
          const checkIn = new Date(record.check_in_time);
          const checkOut = new Date(record.check_out_time);
          const hours = (checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60);

          let breakHours = 0;
          if (record.break_start_time && record.break_end_time) {
            const breakStart = new Date(record.break_start_time);
            const breakEnd = new Date(record.break_end_time);
            breakHours = (breakEnd.getTime() - breakStart.getTime()) / (1000 * 60 * 60);
          }

          totalHours += hours - breakHours;
        }

        overtimeHours += record.overtime_hours || 0;
        if (record.is_late) lateDays++;
        if (record.is_early_leave) earlyLeaveDays++;
      });

      setStats({
        totalDays: data.length,
        totalHours: Math.round(totalHours * 10) / 10,
        overtimeHours: Math.round(overtimeHours * 10) / 10,
        lateDays,
        earlyLeaveDays,
        averageHours: data.length > 0 ? Math.round((totalHours / data.length) * 10) / 10 : 0,
      });
    }

    setLoading(false);
  };

  const handlePreviousMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  const handleExportPDF = () => {
    const csvRows = [
      ['日付', '出勤時刻', '退勤時刻', '勤務時間', '残業時間', '遅刻', '早退', 'メモ'],
      ...records.map((r) => {
        const checkIn = r.check_in_time ? new Date(r.check_in_time) : null;
        const checkOut = r.check_out_time ? new Date(r.check_out_time) : null;
        const hours = checkIn && checkOut
          ? Math.round(((checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60)) * 10) / 10
          : 0;

        return [
          r.date,
          checkIn ? checkIn.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }) : '-',
          checkOut ? checkOut.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }) : '-',
          `${hours}h`,
          `${r.overtime_hours || 0}h`,
          r.is_late ? 'あり' : 'なし',
          r.is_early_leave ? 'あり' : 'なし',
          r.notes || '',
        ];
      }),
    ];

    const csvContent = csvRows.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `月次レポート_${monthString}.csv`;
    link.click();
  };

  const monthString = currentMonth.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <FileText className="w-6 h-6 text-green-600" />
              <h1 className="text-xl font-bold text-gray-900">月次レポート</h1>
            </div>
          </div>
          <button
            onClick={handleExportPDF}
            className="p-2 hover:bg-green-50 rounded-lg transition-colors text-green-600"
            title="CSVエクスポート"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <button
              onClick={handlePreviousMonth}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <h2 className="text-lg font-bold text-gray-900">{monthString}</h2>
            <button
              onClick={handleNextMonth}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {loading ? (
            <div className="p-12 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-6 border-b border-gray-200">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-blue-600 mb-1">出勤日数</p>
                  <p className="text-3xl font-bold text-blue-700">{stats.totalDays}日</p>
                </div>

                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-600 mb-1">総勤務時間</p>
                  <p className="text-3xl font-bold text-green-700">{stats.totalHours}h</p>
                </div>

                <div className="bg-amber-50 rounded-lg p-4">
                  <p className="text-sm text-amber-600 mb-1">残業時間</p>
                  <p className="text-3xl font-bold text-amber-700">{stats.overtimeHours}h</p>
                </div>

                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-sm text-slate-600 mb-1">平均勤務時間</p>
                  <p className="text-3xl font-bold text-slate-700">{stats.averageHours}h</p>
                </div>

                <div className="bg-red-50 rounded-lg p-4">
                  <p className="text-sm text-red-600 mb-1">遅刻回数</p>
                  <p className="text-3xl font-bold text-red-700">{stats.lateDays}回</p>
                </div>

                <div className="bg-orange-50 rounded-lg p-4">
                  <p className="text-sm text-orange-600 mb-1">早退回数</p>
                  <p className="text-3xl font-bold text-orange-700">{stats.earlyLeaveDays}回</p>
                </div>
              </div>

              <div className="p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">勤務記録詳細</h3>
                {records.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">記録がありません</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">日付</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">出勤</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">退勤</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-600">勤務時間</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-600">残業</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-600">備考</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {records.map((record) => {
                          const checkIn = record.check_in_time ? new Date(record.check_in_time) : null;
                          const checkOut = record.check_out_time ? new Date(record.check_out_time) : null;
                          const hours = checkIn && checkOut
                            ? Math.round(((checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60)) * 10) / 10
                            : 0;

                          return (
                            <tr key={record.id} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm text-gray-900">
                                {new Date(record.date + 'T00:00:00').toLocaleDateString('ja-JP', {
                                  month: 'short',
                                  day: 'numeric',
                                })}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                {checkIn ? checkIn.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }) : '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                {checkOut ? checkOut.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }) : '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-900 text-right font-medium">
                                {hours}h
                              </td>
                              <td className="px-4 py-3 text-sm text-amber-600 text-right font-medium">
                                {record.overtime_hours || 0}h
                              </td>
                              <td className="px-4 py-3 text-center">
                                {record.is_late && (
                                  <span className="inline-block px-2 py-1 text-xs bg-red-100 text-red-700 rounded mr-1">
                                    遅刻
                                  </span>
                                )}
                                {record.is_early_leave && (
                                  <span className="inline-block px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded">
                                    早退
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
