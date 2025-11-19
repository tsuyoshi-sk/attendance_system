import React, { useState, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import axios from 'axios';

interface CalendarDay {
  date: string;
  workHours?: number;
  status?: 'present' | 'absent' | 'holiday';
  punchIn?: string;
  punchOut?: string;
}

export const CalendarPage: React.FC = () => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendarData, setCalendarData] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCalendarData();
  }, [currentDate]);

  const fetchCalendarData = async () => {
    try {
      setLoading(true);
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;

      // カレンダーデータを取得（仮実装）
      const response = await axios.get(`/api/v1/calendar/${year}/${month}`);
      setCalendarData(response.data || []);
    } catch (err) {
      console.error('Failed to fetch calendar data:', err);
      setCalendarData([]);
    } finally {
      setLoading(false);
    }
  };

  const getDaysInMonth = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const days: Date[] = [];

    // 月の最初の日の曜日を取得（0: 日曜日）
    const firstDayOfWeek = firstDay.getDay();

    // 前月の日付を追加
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      const prevDate = new Date(year, month, -i);
      days.push(prevDate);
    }

    // 当月の日付を追加
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push(new Date(year, month, i));
    }

    // 次月の日付を追加（6週分埋める）
    const remainingDays = 42 - days.length;
    for (let i = 1; i <= remainingDays; i++) {
      days.push(new Date(year, month + 1, i));
    }

    return days;
  };

  const getDateStatus = (date: Date) => {
    const dateStr = date.toISOString().split('T')[0];
    return calendarData.find(d => d.date === dateStr);
  };

  const isCurrentMonth = (date: Date) => {
    return date.getMonth() === currentDate.getMonth();
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1));
  };

  const formatMonth = () => {
    return currentDate.toLocaleDateString('ja-JP', { year: 'numeric', month: 'long' });
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'present':
        return 'bg-green-100 border-green-300';
      case 'absent':
        return 'bg-red-100 border-red-300';
      case 'holiday':
        return 'bg-blue-100 border-blue-300';
      default:
        return 'bg-white border-slate-200';
    }
  };

  const weekDays = ['日', '月', '火', '水', '木', '金', '土'];
  const days = getDaysInMonth();

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">カレンダー</h1>
          <p className="text-sm text-slate-600 mt-1">
            月次の勤怠状況を確認できます
          </p>
        </div>
      </div>

      {/* カレンダー */}
      <div className="card">
        <div className="card-content p-6">
          {/* 月選択 */}
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={prevMonth}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <ChevronLeft size={20} />
            </button>
            <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
              <Calendar size={24} />
              {formatMonth()}
            </h2>
            <button
              onClick={nextMonth}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <ChevronRight size={20} />
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-slate-600 mt-4">読み込み中...</p>
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-2">
              {/* 曜日ヘッダー */}
              {weekDays.map((day, index) => (
                <div
                  key={day}
                  className={`text-center font-semibold py-2 ${
                    index === 0 ? 'text-red-600' : index === 6 ? 'text-blue-600' : 'text-slate-700'
                  }`}
                >
                  {day}
                </div>
              ))}

              {/* 日付 */}
              {days.map((date, index) => {
                const dayData = getDateStatus(date);
                const isCurrent = isCurrentMonth(date);
                const isTodayDate = isToday(date);

                return (
                  <div
                    key={index}
                    className={`
                      border rounded-lg p-2 min-h-[80px]
                      ${getStatusColor(dayData?.status)}
                      ${!isCurrent ? 'opacity-30' : ''}
                      ${isTodayDate ? 'ring-2 ring-blue-500' : ''}
                      transition-all hover:shadow-md
                    `}
                  >
                    <div className="flex justify-between items-start">
                      <span
                        className={`text-sm font-medium ${
                          isTodayDate
                            ? 'text-blue-600 font-bold'
                            : index % 7 === 0
                            ? 'text-red-600'
                            : index % 7 === 6
                            ? 'text-blue-600'
                            : 'text-slate-700'
                        }`}
                      >
                        {date.getDate()}
                      </span>
                    </div>
                    {dayData && isCurrent && (
                      <div className="mt-1 text-xs space-y-1">
                        {dayData.punchIn && (
                          <div className="text-green-700">
                            出: {dayData.punchIn}
                          </div>
                        )}
                        {dayData.punchOut && (
                          <div className="text-blue-700">
                            退: {dayData.punchOut}
                          </div>
                        )}
                        {dayData.workHours !== undefined && (
                          <div className="font-semibold text-slate-900">
                            {dayData.workHours.toFixed(1)}h
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* 凡例 */}
          <div className="mt-6 flex items-center justify-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-100 border border-green-300 rounded"></div>
              <span className="text-slate-600">出勤</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-100 border border-red-300 rounded"></div>
              <span className="text-slate-600">欠勤</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-100 border border-blue-300 rounded"></div>
              <span className="text-slate-600">休日</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarPage;
