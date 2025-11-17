import React, { useState, useEffect } from 'react';
import { Calendar, TrendingUp, Clock, BarChart3 } from 'lucide-react';
import { format } from 'date-fns';
import PageHeader from '../components/Layout/PageHeader';
import apiClient from '../lib/api';
import { MonthlyReport } from '../types';

const ReportsPage: React.FC = () => {
  const [selectedMonth, setSelectedMonth] = useState(format(new Date(), 'yyyy-MM'));
  const [monthlyReport, setMonthlyReport] = useState<MonthlyReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchMonthlyReport();
  }, [selectedMonth]);

  const fetchMonthlyReport = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getMonthlyReport(selectedMonth);
      setMonthlyReport(data);
    } catch (error) {
      console.error('Failed to fetch monthly report:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="レポート"
        description="月次・日次の勤怠レポートを確認できます"
      />

      {/* 月選択 */}
      <div className="card mb-6">
        <div className="card-content p-6">
          <div className="flex items-center gap-4">
            <label className="label mb-0">対象月</label>
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="input max-w-xs"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      ) : monthlyReport ? (
        <>
          {/* サマリーカード */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="card">
              <div className="card-content p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Calendar className="text-blue-600" size={20} />
                  </div>
                  <h3 className="text-sm font-medium text-slate-600">出勤日数</h3>
                </div>
                <p className="text-3xl font-bold text-slate-900">
                  {monthlyReport.summary?.present_days || 0}
                  <span className="text-lg font-normal text-slate-500 ml-1">日</span>
                </p>
              </div>
            </div>

            <div className="card">
              <div className="card-content p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Clock className="text-green-600" size={20} />
                  </div>
                  <h3 className="text-sm font-medium text-slate-600">総勤務時間</h3>
                </div>
                <p className="text-3xl font-bold text-slate-900">
                  {(monthlyReport.total_hours / 60).toFixed(1)}
                  <span className="text-lg font-normal text-slate-500 ml-1">h</span>
                </p>
              </div>
            </div>

            <div className="card">
              <div className="card-content p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <TrendingUp className="text-purple-600" size={20} />
                  </div>
                  <h3 className="text-sm font-medium text-slate-600">平均勤務時間</h3>
                </div>
                <p className="text-3xl font-bold text-slate-900">
                  {monthlyReport.summary?.average_working_hours
                    ? (monthlyReport.summary.average_working_hours / 60).toFixed(1)
                    : '0.0'}
                  <span className="text-lg font-normal text-slate-500 ml-1">h</span>
                </p>
              </div>
            </div>

            <div className="card">
              <div className="card-content p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <BarChart3 className="text-orange-600" size={20} />
                  </div>
                  <h3 className="text-sm font-medium text-slate-600">残業時間</h3>
                </div>
                <p className="text-3xl font-bold text-slate-900">
                  {(monthlyReport.total_overtime / 60).toFixed(1)}
                  <span className="text-lg font-normal text-slate-500 ml-1">h</span>
                </p>
              </div>
            </div>
          </div>

          {/* 日別詳細 */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold text-slate-900">日別詳細</h2>
            </div>
            <div className="card-content p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                        日付
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                        出勤
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                        退勤
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                        勤務時間
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                        休憩時間
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                        残業時間
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                        状態
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {monthlyReport.daily_reports.map((daily, index) => (
                      <tr key={index} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                          {format(new Date(daily.date), 'M/d (E)')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                          {daily.punch_in_time
                            ? format(new Date(daily.punch_in_time), 'HH:mm')
                            : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                          {daily.punch_out_time
                            ? format(new Date(daily.punch_out_time), 'HH:mm')
                            : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                          {daily.working_hours ? `${(daily.working_hours / 60).toFixed(1)}h` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                          {daily.break_time ? `${daily.break_time}分` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                          {daily.overtime ? `${(daily.overtime / 60).toFixed(1)}h` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`badge ${
                              daily.status === 'working'
                                ? 'badge-success'
                                : daily.status === 'break'
                                ? 'badge-warning'
                                : 'badge-default'
                            }`}
                          >
                            {daily.status === 'working'
                              ? '勤務中'
                              : daily.status === 'break'
                              ? '休憩中'
                              : daily.status === 'off'
                              ? '退勤済み'
                              : daily.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <div className="card-content py-12 text-center text-slate-500">
            <Calendar size={48} className="mx-auto mb-3 opacity-30" />
            <p>レポートデータがありません</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
