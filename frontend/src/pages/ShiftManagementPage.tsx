import { useEffect, useState } from 'react';
import { ArrowLeft, Clock, ChevronLeft, ChevronRight } from 'lucide-react';
import { supabase } from '../lib/supabase';

interface ShiftManagementPageProps {
  session: any;
  onBack: () => void;
}

interface Shift {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  notes: string;
}

export default function ShiftManagementPage({ session, onBack }: ShiftManagementPageProps) {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadShifts();
  }, [currentMonth]);

  const loadShifts = async () => {
    setLoading(true);
    const year = currentMonth.getFullYear();
    const month = String(currentMonth.getMonth() + 1).padStart(2, '0');
    const startDate = `${year}-${month}-01`;
    const endDate = `${year}-${month}-31`;

    const { data } = await supabase
      .from('shifts')
      .select('*')
      .eq('user_id', session.user.id)
      .gte('date', startDate)
      .lte('date', endDate)
      .order('date', { ascending: true });

    if (data) {
      setShifts(data);
    }
    setLoading(false);
  };

  const handlePreviousMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  const getDaysInMonth = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDay = new Date(year, month, 1).getDay();

    const days = [];
    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }
    return days;
  };

  const getShiftForDay = (day: number) => {
    const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(
      2,
      '0'
    )}-${String(day).padStart(2, '0')}`;
    return shifts.find((shift) => shift.date === dateStr);
  };

  const monthString = currentMonth.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
  });

  const weekDays = ['日', '月', '火', '水', '木', '金', '土'];
  const days = getDaysInMonth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Clock className="w-6 h-6 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">シフト管理</h1>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
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
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : (
            <div className="p-6">
              <div className="grid grid-cols-7 gap-2 mb-2">
                {weekDays.map((day, index) => (
                  <div
                    key={index}
                    className={`text-center text-sm font-medium py-2 ${
                      index === 0 ? 'text-red-600' : index === 6 ? 'text-blue-600' : 'text-gray-700'
                    }`}
                  >
                    {day}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-7 gap-2">
                {days.map((day, index) => {
                  if (day === null) {
                    return <div key={`empty-${index}`} className="aspect-square" />;
                  }

                  const shift = getShiftForDay(day);
                  const isToday =
                    day === new Date().getDate() &&
                    currentMonth.getMonth() === new Date().getMonth() &&
                    currentMonth.getFullYear() === new Date().getFullYear();

                  return (
                    <div
                      key={day}
                      className={`aspect-square border rounded-lg p-2 ${
                        isToday ? 'bg-indigo-50 border-indigo-300' : 'bg-white border-gray-200'
                      } ${shift ? 'hover:shadow-md transition-shadow' : ''}`}
                    >
                      <div className="text-sm font-semibold text-gray-900 mb-1">{day}</div>
                      {shift && (
                        <div className="text-xs">
                          <div className="bg-indigo-100 text-indigo-700 rounded px-1 py-0.5 mb-1 font-medium">
                            {shift.start_time.slice(0, 5)} - {shift.end_time.slice(0, 5)}
                          </div>
                          {shift.notes && (
                            <div className="text-gray-600 text-xs line-clamp-1">{shift.notes}</div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">今月のシフト一覧</h3>
          {shifts.length === 0 ? (
            <p className="text-gray-500 text-center py-4">シフトがありません</p>
          ) : (
            <div className="space-y-3">
              {shifts.map((shift) => (
                <div
                  key={shift.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div>
                    <h4 className="font-semibold text-gray-900">
                      {new Date(shift.date + 'T00:00:00').toLocaleDateString('ja-JP', {
                        month: 'long',
                        day: 'numeric',
                        weekday: 'short',
                      })}
                    </h4>
                    {shift.notes && <p className="text-sm text-gray-600 mt-1">{shift.notes}</p>}
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-indigo-600">
                      {shift.start_time.slice(0, 5)} - {shift.end_time.slice(0, 5)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
