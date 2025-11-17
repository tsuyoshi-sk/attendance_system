import { useEffect, useState } from 'react';
import { Clock, LogOut, ChevronRight, Coffee, User, Shield, Calendar, FileText, Bell } from 'lucide-react';
import { supabase } from '../lib/supabase';
import TodayStatus from '../components/TodayStatus';
import ClockButtons from '../components/ClockButtons';
import NotificationBanner from '../components/NotificationBanner';

interface ClockInScreenProps {
  session: any;
  isAdmin: boolean;
  onViewDashboard: () => void;
  onViewProfile: () => void;
  onViewAdmin: () => void;
  onViewLeave: () => void;
  onViewShift: () => void;
  onViewReport: () => void;
  onViewNotifications: () => void;
}

export default function ClockInScreen({ session, isAdmin, onViewDashboard, onViewProfile, onViewAdmin, onViewLeave, onViewShift, onViewReport, onViewNotifications }: ClockInScreenProps) {
  const [userName, setUserName] = useState('');
  const [todayRecord, setTodayRecord] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [onBreak, setOnBreak] = useState(false);
  const [workPattern, setWorkPattern] = useState<any>(null);
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    loadUserName();
    loadTodayRecord();
    loadWorkPattern();
    getLocation();

    const interval = setInterval(loadTodayRecord, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadUserName = async () => {
    const { data } = await supabase
      .from('profiles')
      .select('name')
      .eq('id', session.user.id)
      .maybeSingle();

    if (data) {
      setUserName(data.name);
    }
  };

  const loadWorkPattern = async () => {
    const { data: profile } = await supabase
      .from('profiles')
      .select('work_pattern_id')
      .eq('id', session.user.id)
      .maybeSingle();

    if (profile?.work_pattern_id) {
      const { data: pattern } = await supabase
        .from('work_patterns')
        .select('*')
        .eq('id', profile.work_pattern_id)
        .maybeSingle();

      setWorkPattern(pattern);
    }
  };

  const getLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        () => {
          console.log('Location access denied');
        }
      );
    }
  };

  const loadTodayRecord = async () => {
    const today = new Date().toISOString().split('T')[0];

    const { data } = await supabase
      .from('attendance_records')
      .select('*')
      .eq('user_id', session.user.id)
      .eq('date', today)
      .maybeSingle();

    setTodayRecord(data);
    setOnBreak(data?.break_start_time && !data?.break_end_time);
  };

  const handleClockIn = async () => {
    setLoading(true);
    const today = new Date().toISOString().split('T')[0];
    const now = new Date();

    let isLate = false;
    if (workPattern && !workPattern.is_flexible) {
      const currentTime = now.getHours() * 60 + now.getMinutes();
      const [startHour, startMin] = workPattern.start_time.split(':').map(Number);
      const startTimeMin = startHour * 60 + startMin;
      isLate = currentTime > startTimeMin + 15;
    }

    try {
      const recordData: any = {
        user_id: session.user.id,
        date: today,
        check_in_time: now.toISOString(),
        is_late: isLate,
      };

      if (location) {
        recordData.location_lat = location.lat;
        recordData.location_lng = location.lng;
      }

      const { error } = await supabase.from('attendance_records').insert([recordData]);

      if (error) throw error;
      await loadTodayRecord();
    } finally {
      setLoading(false);
    }
  };

  const handleClockOut = async () => {
    setLoading(true);
    const now = new Date();

    try {
      const checkIn = new Date(todayRecord.check_in_time);
      const totalHours = (now.getTime() - checkIn.getTime()) / (1000 * 60 * 60);

      let overtimeHours = 0;
      let isEarlyLeave = false;

      if (workPattern && !workPattern.is_flexible) {
        const expectedHours =
          ((new Date(`2000-01-01T${workPattern.end_time}`).getTime() -
            new Date(`2000-01-01T${workPattern.start_time}`).getTime()) /
            (1000 * 60 * 60)) - (workPattern.break_duration / 60);

        const workHours = totalHours - (todayRecord.break_start_time && todayRecord.break_end_time ?
          (new Date(todayRecord.break_end_time).getTime() - new Date(todayRecord.break_start_time).getTime()) / (1000 * 60 * 60) :
          workPattern.break_duration / 60);

        overtimeHours = Math.max(0, workHours - expectedHours);

        const currentTime = now.getHours() * 60 + now.getMinutes();
        const [endHour, endMin] = workPattern.end_time.split(':').map(Number);
        const endTimeMin = endHour * 60 + endMin;
        isEarlyLeave = currentTime < endTimeMin - 15;
      }

      const { error } = await supabase
        .from('attendance_records')
        .update({
          check_out_time: now.toISOString(),
          overtime_hours: overtimeHours,
          is_early_leave: isEarlyLeave,
        })
        .eq('id', todayRecord.id);

      if (error) throw error;
      await loadTodayRecord();
    } finally {
      setLoading(false);
    }
  };

  const handleBreakStart = async () => {
    setLoading(true);
    try {
      const { error } = await supabase
        .from('attendance_records')
        .update({
          break_start_time: new Date().toISOString(),
        })
        .eq('id', todayRecord.id);

      if (error) throw error;
      await loadTodayRecord();
    } finally {
      setLoading(false);
    }
  };

  const handleBreakEnd = async () => {
    setLoading(true);
    try {
      const breakStart = new Date(todayRecord.break_start_time);
      const breakEnd = new Date();
      const breakMinutes = Math.round((breakEnd.getTime() - breakStart.getTime()) / (1000 * 60));

      const { error } = await supabase
        .from('attendance_records')
        .update({
          break_end_time: breakEnd.toISOString(),
          break_duration_minutes: (todayRecord.break_duration_minutes || 0) + breakMinutes,
        })
        .eq('id', todayRecord.id);

      if (error) throw error;
      await loadTodayRecord();
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-md mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-6 h-6 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">勤務管理</h1>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin && (
              <button
                onClick={onViewAdmin}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-amber-600"
                title="管理者画面"
              >
                <Shield className="w-5 h-5" />
              </button>
            )}
            <button
              onClick={onViewProfile}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="プロフィール"
            >
              <User className="w-5 h-5" />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="ログアウト"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-md mx-auto px-4 py-6 sm:py-8">
        <NotificationBanner session={session} />

        <div className="bg-white rounded-2xl shadow-md p-6 mb-6">
          <p className="text-gray-600 text-sm mb-1">ようこそ</p>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">{userName || '従業員'}</h2>
          <p className="text-gray-500 text-xs">{session.user.email}</p>
        </div>

        <TodayStatus record={todayRecord} />

        <ClockButtons
          record={todayRecord}
          loading={loading}
          workPattern={workPattern}
          onClockIn={handleClockIn}
          onClockOut={handleClockOut}
        />

        {todayRecord && !todayRecord.check_out_time && (
          <div className="mt-4">
            {onBreak ? (
              <button
                onClick={handleBreakEnd}
                disabled={loading}
                className="w-full py-3 px-4 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Coffee className="w-5 h-5" />
                休憩終了
              </button>
            ) : (
              <button
                onClick={handleBreakStart}
                disabled={loading}
                className="w-full py-3 px-4 bg-amber-100 text-amber-700 border border-amber-300 rounded-lg font-medium hover:bg-amber-200 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Coffee className="w-5 h-5" />
                休憩開始
              </button>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 mt-8">
          <button
            onClick={onViewDashboard}
            className="py-3 px-4 bg-white rounded-lg shadow-sm text-indigo-600 font-medium flex items-center justify-center gap-2 hover:bg-gray-50 transition-colors"
          >
            <Clock className="w-4 h-4" />
            <span>勤務履歴</span>
          </button>

          <button
            onClick={onViewLeave}
            className="py-3 px-4 bg-white rounded-lg shadow-sm text-blue-600 font-medium flex items-center justify-center gap-2 hover:bg-gray-50 transition-colors"
          >
            <Calendar className="w-4 h-4" />
            <span>有給申請</span>
          </button>

          <button
            onClick={onViewShift}
            className="py-3 px-4 bg-white rounded-lg shadow-sm text-indigo-600 font-medium flex items-center justify-center gap-2 hover:bg-gray-50 transition-colors"
          >
            <Clock className="w-4 h-4" />
            <span>シフト</span>
          </button>

          <button
            onClick={onViewReport}
            className="py-3 px-4 bg-white rounded-lg shadow-sm text-green-600 font-medium flex items-center justify-center gap-2 hover:bg-gray-50 transition-colors"
          >
            <FileText className="w-4 h-4" />
            <span>月次レポート</span>
          </button>
        </div>

        <button
          onClick={onViewNotifications}
          className="w-full mt-3 py-3 px-4 bg-white rounded-lg shadow-sm text-gray-600 font-medium flex items-center justify-center gap-2 hover:bg-gray-50 transition-colors"
        >
          <Bell className="w-4 h-4" />
          <span>通知設定</span>
        </button>
      </main>
    </div>
  );
}
