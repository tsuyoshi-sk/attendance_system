import React, { useState, useEffect } from 'react';
import {
  Clock,
  LogIn,
  LogOut,
  Coffee,
  ArrowRight,
  Calendar,
  TrendingUp,
} from 'lucide-react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import PageHeader from '../components/Layout/PageHeader';
import apiClient from '../lib/api';
import { PunchType, TodayStatus, PunchRecord } from '../types';

const Dashboard: React.FC = () => {
  const [todayStatus, setTodayStatus] = useState<TodayStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isPunching, setIsPunching] = useState(false);

  useEffect(() => {
    fetchTodayStatus();
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const fetchTodayStatus = async () => {
    try {
      setIsLoading(true);
      const today = format(new Date(), 'yyyy-MM-dd');
      const data = await apiClient.getDailyReport(today);
      setTodayStatus(data);
    } catch (error) {
      console.error('Failed to fetch today status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePunch = async (punchType: PunchType) => {
    setIsPunching(true);
    try {
      await apiClient.punch({
        card_idm: 'WEB_' + Date.now(),
        punch_type: punchType,
      });
      await fetchTodayStatus();
    } catch (error: any) {
      alert(error.response?.data?.detail || '打刻に失敗しました');
    } finally {
      setIsPunching(false);
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

  const getPunchTypeIcon = (type: PunchType) => {
    const icons: Record<PunchType, React.ReactNode> = {
      in: <LogIn size={16} />,
      out: <LogOut size={16} />,
      outside: <ArrowRight size={16} />,
      return: <ArrowRight size={16} className="rotate-180" />,
    };
    return icons[type];
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="ダッシュボード"
        description="今日の勤怠状況と打刻操作"
      />

      {/* 現在時刻と状態 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* 現在時刻カード */}
        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="text-blue-600" size={24} />
              <h2 className="text-lg font-semibold text-slate-900">現在時刻</h2>
            </div>
            <p className="text-4xl font-bold text-slate-900">
              {format(currentTime, 'HH:mm:ss')}
            </p>
            <p className="text-slate-600 mt-2">
              {format(currentTime, 'yyyy年M月d日 (E)', { locale: ja })}
            </p>
          </div>
        </div>

        {/* 今日の状態カード */}
        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-900">今日の状態</h2>
              {todayStatus && getStatusBadge(todayStatus.status)}
            </div>
            <div className="space-y-3">
              {todayStatus?.punch_in_time && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">出勤時刻</span>
                  <span className="font-medium text-slate-900">
                    {format(new Date(todayStatus.punch_in_time), 'HH:mm')}
                  </span>
                </div>
              )}
              {todayStatus?.working_hours !== undefined && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">勤務時間</span>
                  <span className="font-medium text-slate-900">
                    {(todayStatus.working_hours / 60).toFixed(1)} 時間
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 打刻ボタン */}
      <div className="card mb-8">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-slate-900">打刻操作</h2>
        </div>
        <div className="card-content p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              onClick={() => handlePunch('in')}
              disabled={isPunching}
              className="btn btn-success py-6 flex-col gap-2 hover:scale-105 transition-transform"
            >
              <LogIn size={24} />
              <span>出勤</span>
            </button>
            <button
              onClick={() => handlePunch('outside')}
              disabled={isPunching}
              className="btn btn-primary py-6 flex-col gap-2 hover:scale-105 transition-transform"
            >
              <ArrowRight size={24} />
              <span>外出</span>
            </button>
            <button
              onClick={() => handlePunch('return')}
              disabled={isPunching}
              className="btn btn-primary py-6 flex-col gap-2 hover:scale-105 transition-transform"
            >
              <ArrowRight size={24} className="rotate-180" />
              <span>戻り</span>
            </button>
            <button
              onClick={() => handlePunch('out')}
              disabled={isPunching}
              className="btn btn-danger py-6 flex-col gap-2 hover:scale-105 transition-transform"
            >
              <LogOut size={24} />
              <span>退勤</span>
            </button>
          </div>
        </div>
      </div>

      {/* 今日の打刻履歴 */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-slate-900">今日の打刻履歴</h2>
        </div>
        <div className="card-content p-0">
          {todayStatus?.records && todayStatus.records.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {todayStatus.records.map((record: PunchRecord, index: number) => (
                <div
                  key={record.id || index}
                  className="px-6 py-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50 text-blue-600">
                        {getPunchTypeIcon(record.punch_type)}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">
                          {getPunchTypeLabel(record.punch_type)}
                        </p>
                        <p className="text-sm text-slate-500">
                          {format(new Date(record.timestamp), 'HH:mm:ss')}
                        </p>
                      </div>
                    </div>
                    {record.note && (
                      <span className="text-sm text-slate-600">{record.note}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-slate-500">
              <Calendar size={48} className="mx-auto mb-3 opacity-30" />
              <p>今日の打刻履歴はまだありません</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
