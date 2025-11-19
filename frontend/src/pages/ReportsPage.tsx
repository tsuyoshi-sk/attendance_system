import React, { useState, useEffect } from 'react';
import { BarChart3, Calendar, Download, FileText } from 'lucide-react';
import axios from 'axios';

interface MonthlyStats {
  totalWorkDays: number;
  totalWorkHours: number;
  totalOvertimeHours: number;
  lateDays: number;
  earlyLeaveDays: number;
}

export const ReportsPage: React.FC = () => {
  const [stats, setStats] = useState<MonthlyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState(
    new Date().toISOString().slice(0, 7) // YYYY-MM format
  );

  useEffect(() => {
    fetchMonthlyReport();
  }, [selectedMonth]);

  const fetchMonthlyReport = async () => {
    try {
      setLoading(true);
      setError(null);

      // 月次レポートを取得（仮実装）
      // 実際のAPIエンドポイントに合わせて調整が必要
      const response = await axios.get(`/api/v1/reports/monthly/${selectedMonth}`);

      setStats({
        totalWorkDays: response.data.total_work_days || 0,
        totalWorkHours: response.data.total_work_hours || 0,
        totalOvertimeHours: response.data.total_overtime_hours || 0,
        lateDays: response.data.late_days || 0,
        earlyLeaveDays: response.data.early_leave_days || 0,
      });
    } catch (err: any) {
      console.error('Failed to fetch monthly report:', err);
      setError('レポートの取得に失敗しました');
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = () => {
    // レポート出力機能（仮実装）
    alert('レポート出力機能は開発中です');
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    subtitle?: string;
    icon: React.ReactNode;
    colorClass: string;
  }> = ({ title, value, subtitle, icon, colorClass }) => (
    <div className="card">
      <div className="card-content p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-600">{title}</p>
            <p className={`text-3xl font-bold mt-2 ${colorClass}`}>{value}</p>
            {subtitle && (
              <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
            )}
          </div>
          <div className={`p-3 rounded-lg ${colorClass} bg-opacity-10`}>
            {icon}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">レポート</h1>
          <p className="text-sm text-slate-600 mt-1">
            月次勤怠レポートを確認できます
          </p>
        </div>
        <button
          onClick={exportReport}
          className="btn btn-secondary flex items-center gap-2"
        >
          <Download size={18} />
          PDF出力
        </button>
      </div>

      {/* 月選択 */}
      <div className="card">
        <div className="card-content p-6">
          <div className="flex items-center gap-4">
            <Calendar className="text-slate-400" size={20} />
            <label className="label">対象月</label>
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="input max-w-xs"
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-slate-600 mt-4">読み込み中...</p>
        </div>
      ) : error ? (
        <div className="card">
          <div className="card-content p-12 text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <button onClick={fetchMonthlyReport} className="btn btn-primary">
              再試行
            </button>
          </div>
        </div>
      ) : stats ? (
        <>
          {/* 統計カード */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="勤務日数"
              value={stats.totalWorkDays}
              subtitle="日"
              icon={<Calendar className="text-blue-600" size={24} />}
              colorClass="text-blue-600"
            />
            <StatCard
              title="総労働時間"
              value={stats.totalWorkHours.toFixed(1)}
              subtitle="時間"
              icon={<BarChart3 className="text-green-600" size={24} />}
              colorClass="text-green-600"
            />
            <StatCard
              title="残業時間"
              value={stats.totalOvertimeHours.toFixed(1)}
              subtitle="時間"
              icon={<FileText className="text-orange-600" size={24} />}
              colorClass="text-orange-600"
            />
            <StatCard
              title="遅刻/早退"
              value={`${stats.lateDays} / ${stats.earlyLeaveDays}`}
              subtitle="日"
              icon={<FileText className="text-red-600" size={24} />}
              colorClass="text-red-600"
            />
          </div>

          {/* 詳細レポート */}
          <div className="card">
            <div className="card-content p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <BarChart3 size={20} />
                月次サマリー
              </h2>
              <div className="text-center py-12">
                <p className="text-slate-600">
                  詳細なレポート機能は開発中です
                </p>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};
