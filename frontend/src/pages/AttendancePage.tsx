import React, { useState, useEffect } from 'react';
import { Calendar, Search, Download } from 'lucide-react';
import { format, subDays } from 'date-fns';
import PageHeader from '../components/Layout/PageHeader';
import apiClient from '../lib/api';
import { DailyReport, PunchType } from '../types';

const AttendancePage: React.FC = () => {
  const [startDate, setStartDate] = useState(
    format(subDays(new Date(), 7), 'yyyy-MM-dd')
  );
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [records, setRecords] = useState<DailyReport[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchRecords();
  }, []);

  const fetchRecords = async () => {
    setIsLoading(true);
    try {
      // 簡易実装: 各日付ごとにAPIを呼び出す
      const promises: Promise<DailyReport>[] = [];
      const start = new Date(startDate);
      const end = new Date(endDate);

      for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        const dateStr = format(d, 'yyyy-MM-dd');
        promises.push(apiClient.getDailyReport(dateStr));
      }

      const results = await Promise.allSettled(promises);
      const validRecords = results
        .filter((r): r is PromiseFulfilledPromise<DailyReport> => r.status === 'fulfilled')
        .map((r) => r.value)
        .filter((r) => r.punch_records && r.punch_records.length > 0);

      setRecords(validRecords);
    } catch (error) {
      console.error('Failed to fetch records:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { label: string; className: string }> = {
      working: { label: '勤務中', className: 'badge-success' },
      break: { label: '休憩中', className: 'badge-warning' },
      outside: { label: '外出中', className: 'badge-info' },
      off: { label: '退勤済み', className: 'badge-default' },
    };
    const badge = badges[status] || badges.off;
    return <span className={`badge ${badge.className}`}>{badge.label}</span>;
  };

  const getPunchTypeLabel = (type: PunchType) => {
    const labels: Record<PunchType, string> = {
      in: '出勤',
      out: '退勤',
      outside: '外出',
      return: '戻り',
    };
    return labels[type];
  };

  const getPunchTypeBadgeClass = (type: PunchType) => {
    const classes: Record<PunchType, string> = {
      in: 'badge-success',
      out: 'badge-danger',
      outside: 'badge-info',
      return: 'badge-info',
    };
    return classes[type];
  };

  return (
    <div>
      <PageHeader
        title="打刻履歴"
        description="過去の打刻記録を確認できます"
      />

      {/* フィルター */}
      <div className="card mb-6">
        <div className="card-content p-6">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex-1 min-w-[200px]">
              <label className="label">開始日</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input"
              />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="label">終了日</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="input"
              />
            </div>
            <button
              onClick={fetchRecords}
              disabled={isLoading}
              className="btn btn-primary"
            >
              <Search size={18} />
              <span>検索</span>
            </button>
            <button className="btn btn-secondary">
              <Download size={18} />
              <span>CSV出力</span>
            </button>
          </div>
        </div>
      </div>

      {/* 打刻履歴テーブル */}
      <div className="card">
        <div className="card-content p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
            </div>
          ) : records.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      日付
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      状態
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      出勤時刻
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      退勤時刻
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      勤務時間
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
                      打刻回数
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {records.map((record, index) => (
                    <tr key={index} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Calendar size={16} className="text-slate-400" />
                          <span className="text-sm font-medium text-slate-900">
                            {format(new Date(record.date), 'yyyy/MM/dd')}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(record.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        {record.punch_in_time
                          ? format(new Date(record.punch_in_time), 'HH:mm')
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        {record.punch_out_time
                          ? format(new Date(record.punch_out_time), 'HH:mm')
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                        {record.working_hours
                          ? `${(record.working_hours / 60).toFixed(1)}h`
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="badge badge-default">
                          {record.punch_records.length}回
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-slate-500">
              <Calendar size={48} className="mx-auto mb-3 opacity-30" />
              <p>指定期間の打刻履歴がありません</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AttendancePage;
