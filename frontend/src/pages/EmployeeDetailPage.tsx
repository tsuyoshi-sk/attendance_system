import { useParams } from 'react-router-dom';
import { User, Calendar, Clock, Edit, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getEmployeeMonthlyAttendance, getEmployeeDailyAttendance, EmployeeMonthlySummary, EmployeeDailyTimeline } from '../lib/api';
import { format, startOfMonth, getDaysInMonth, getDay, addMonths, subMonths } from 'date-fns';

const dayStatusColors = {
  normal: "bg-green-100 text-green-800",
  need_fix: "bg-yellow-100 text-yellow-800",
  absence: "bg-red-100 text-red-800",
  holiday: "bg-gray-100 text-gray-500",
  default: "bg-gray-50 text-gray-400"
};

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [employeeId, setEmployeeId] = useState<number | null>(null);

  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<string>(format(new Date(), "yyyy-MM-dd"));

  const [monthlySummary, setMonthlySummary] = useState<EmployeeMonthlySummary | null>(null);
  const [dailyTimeline, setDailyTimeline] = useState<EmployeeDailyTimeline | null>(null);
  
  const [loadingMonthly, setLoadingMonthly] = useState(true);
  const [loadingDaily, setLoadingDaily] = useState(false);

  useEffect(() => {
    if (id) {
      setEmployeeId(parseInt(id, 10));
    }
  }, [id]);

  // Fetch monthly summary when employeeId or currentMonth changes
  useEffect(() => {
    if (!employeeId) return;

    const monthStr = format(currentMonth, 'yyyy-MM');
    setLoadingMonthly(true);
    getEmployeeMonthlyAttendance(employeeId, monthStr)
      .then(data => setMonthlySummary(data))
      .catch(err => console.error("Failed to fetch monthly summary:", err))
      .finally(() => setLoadingMonthly(false));

  }, [employeeId, currentMonth]);

  // Fetch daily timeline when selectedDate changes
  useEffect(() => {
    if (!employeeId || !selectedDate) return;

    setLoadingDaily(true);
    getEmployeeDailyAttendance(employeeId, selectedDate)
      .then(data => setDailyTimeline(data))
      .catch(err => console.error("Failed to fetch daily timeline:", err))
      .finally(() => setLoadingDaily(false));

  }, [employeeId, selectedDate]);
  
  const renderCalendar = () => {
    const monthStart = startOfMonth(currentMonth);
    const daysInMonth = getDaysInMonth(currentMonth);
    const startDayOfWeek = getDay(monthStart); // 0 (Sun) - 6 (Sat), we need to adjust for Monday start
    const adjustedStartDay = startDayOfWeek === 0 ? 6 : startDayOfWeek -1;

    const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
    const emptyDays = Array.from({ length: adjustedStartDay });

    const summaryMap = new Map(monthlySummary?.days.map(d => [d.date, d]));

    return (
        <div>
            <div className="grid grid-cols-7 gap-px text-center text-xs font-semibold text-gray-500 bg-gray-200 border-l border-t border-gray-200">
                {['月', '火', '水', '木', '金', '土', '日'].map(day => (
                    <div key={day} className="py-2 bg-gray-50 border-r border-b border-gray-200">{day}</div>
                ))}
            </div>
            <div className="grid grid-cols-7 gap-px bg-gray-200 border-l border-gray-200">
                {emptyDays.map((_, i) => <div key={`empty-${i}`} className="bg-gray-50 border-r border-b border-gray-200"></div>)}
                {days.map(day => {
                    const dateStr = `${format(currentMonth, 'yyyy-MM')}-${String(day).padStart(2, '0')}`;
                    const summary = summaryMap.get(dateStr);
                    const statusColor = summary ? dayStatusColors[summary.status] : dayStatusColors.default;
                    const isSelected = dateStr === selectedDate;

                    return (
                        <div key={day} onClick={() => setSelectedDate(dateStr)} 
                             className={`p-2 h-24 flex flex-col items-start cursor-pointer border-r border-b border-gray-200 ${isSelected ? 'bg-blue-100' : 'bg-white hover:bg-gray-50'}`}>
                            <div className={`font-medium ${isSelected ? 'text-blue-600' : 'text-gray-800'}`}>{day}</div>
                            {summary && (
                                <div className="mt-auto w-full text-center">
                                    <span className={`px-1.5 py-0.5 text-xs rounded-full ${statusColor}`}>
                                        {Math.floor(summary.totalWorkMinutes / 60)}h {summary.totalWorkMinutes % 60}m
                                    </span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
  };


  if (!monthlySummary || loadingMonthly) {
    return <div className="p-6">従業員データを読み込み中...</div>;
  }

  const { employee } = monthlySummary;

  return (
    <div className="p-6 space-y-6">
      {/* 上：基本情報 */}
      <div className="bg-white rounded-xl shadow p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-gray-500">{employee.employeeCode}</p>
            <h1 className="text-2xl font-semibold text-slate-800 mt-1">{employee.name}</h1>
            <div className="flex items-center gap-2 mt-2 text-sm text-gray-600">
              <User size={16} />
              <span>{employee.departmentName || '未所属'}</span>
            </div>
          </div>
          <div>
            <button className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-4 py-2 rounded-lg">
                <Edit size={14} />
                <span>打刻を修正</span>
            </button>
          </div>
        </div>
      </div>

      {/* 中：月間カレンダー */}
      <div className="bg-white rounded-xl shadow p-5">
        <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-700 flex items-center gap-2">
                <Calendar size={18} />
                月間勤怠カレンダー
            </h2>
            <div className="flex items-center gap-2">
                <button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} className="p-1 rounded-md hover:bg-gray-100"><ChevronLeft size={20} /></button>
                <span className="font-semibold w-28 text-center">{format(currentMonth, 'yyyy年 M月')}</span>
                <button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} className="p-1 rounded-md hover:bg-gray-100"><ChevronRight size={20} /></button>
            </div>
        </div>
        {renderCalendar()}
      </div>
      
      {/* 下：選択日付のタイムライン */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-base font-semibold mb-4 text-slate-700 flex items-center gap-2">
            <Clock size={18} />
            打刻タイムライン ({format(new Date(selectedDate), 'yyyy/MM/dd')})
        </h2>
        {loadingDaily ? (
            <div className="text-center py-16 text-gray-400">タイムラインを読み込み中...</div>
        ) : dailyTimeline && dailyTimeline.punches.length > 0 ? (
            <ul className="space-y-3">
                {dailyTimeline.punches.map(punch => (
                    <li key={punch.id} className="flex items-center gap-4 text-sm">
                        <span className="font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded-md">{punch.time}</span>
                        <span className={`capitalize font-medium ${punch.type === 'in' || punch.type === 'return' ? 'text-green-600' : 'text-red-600'}`}>
                            {punch.type === 'in' ? '出勤' : punch.type === 'out' ? '退勤' : punch.type === 'outside' ? '外出' : '戻り'}
                        </span>
                        <span className="text-xs text-gray-400 ml-auto">{punch.source}</span>
                    </li>
                ))}
            </ul>
        ) : (
            <div className="text-center py-16 text-gray-400">
                <p>この日の打刻記録はありません。</p>
            </div>
        )}
      </div>
    </div>
  );
}
