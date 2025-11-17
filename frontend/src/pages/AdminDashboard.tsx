import { useEffect, useState } from 'react';
import { ArrowLeft, Users, TrendingUp, Calendar, Edit2, Download, Check, X, UserPlus } from 'lucide-react';
import { supabase } from '../lib/supabase';
import EditRecordModal from '../components/EditRecordModal';

interface AdminDashboardProps {
  session: any;
  onBack: () => void;
}

interface EmployeeRecord {
  id: string;
  name: string;
  email: string;
  totalHours: number;
  workDays: number;
  lastCheckIn: string;
}

interface AttendanceRecord {
  id: string;
  date: string;
  userName: string;
  userEmail: string;
  checkIn: string;
  checkOut: string;
  hours: number;
  notes: string;
  rawRecord: any;
}

export default function AdminDashboard({ session, onBack }: AdminDashboardProps) {
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [recentRecords, setRecentRecords] = useState<AttendanceRecord[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date());
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalEmployees: 0,
    activeToday: 0,
    totalHoursThisMonth: 0,
  });
  const [showLeaveRequests, setShowLeaveRequests] = useState(false);
  const [leaveRequests, setLeaveRequests] = useState<any[]>([]);

  useEffect(() => {
    loadAdminData();
    loadLeaveRequests();
  }, [selectedMonth]);

  const loadAdminData = async () => {
    setLoading(true);

    const year = selectedMonth.getFullYear();
    const month = String(selectedMonth.getMonth() + 1).padStart(2, '0');
    const startDate = `${year}-${month}-01`;
    const endDate = `${year}-${month}-31`;
    const today = new Date().toISOString().split('T')[0];

    const [profilesRes, recordsRes, todayRecordsRes] = await Promise.all([
      supabase.from('profiles').select('*'),
      supabase
        .from('attendance_records')
        .select('*')
        .gte('date', startDate)
        .lte('date', endDate)
        .order('date', { ascending: false })
        .limit(50),
      supabase.from('attendance_records').select('*').eq('date', today),
    ]);

    if (profilesRes.data && recordsRes.data) {
      const employeeMap = new Map<string, EmployeeRecord>();
      let totalMonthHours = 0;

      profilesRes.data.forEach((profile) => {
        employeeMap.set(profile.id, {
          id: profile.id,
          name: profile.name || 'Unknown',
          email: profile.id,
          totalHours: 0,
          workDays: 0,
          lastCheckIn: '-',
        });
      });

      recordsRes.data.forEach((record) => {
        const employee = employeeMap.get(record.user_id);
        if (employee && record.check_out_time) {
          const checkIn = new Date(record.check_in_time);
          const checkOut = new Date(record.check_out_time);
          const hours = (checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60);
          employee.totalHours += hours;
          employee.workDays += 1;
          totalMonthHours += hours;

          if (!employee.lastCheckIn || employee.lastCheckIn === '-') {
            employee.lastCheckIn = record.date;
          }
        }
      });

      const employeesList = Array.from(employeeMap.values())
        .map((emp) => ({
          ...emp,
          totalHours: Math.round(emp.totalHours * 10) / 10,
        }))
        .sort((a, b) => b.totalHours - a.totalHours);

      setEmployees(employeesList);

      const recentList: AttendanceRecord[] = await Promise.all(
        recordsRes.data.slice(0, 20).map(async (record) => {
          const { data: profile } = await supabase
            .from('profiles')
            .select('name')
            .eq('id', record.user_id)
            .maybeSingle();

          const checkIn = new Date(record.check_in_time);
          const checkOut = record.check_out_time ? new Date(record.check_out_time) : new Date();
          const hours = Math.round(((checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60)) * 10) / 10;

          return {
            id: record.id,
            date: record.date,
            userName: profile?.name || 'Unknown',
            userEmail: record.user_id,
            checkIn: checkIn.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }),
            checkOut: record.check_out_time
              ? checkOut.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
              : '退勤なし',
            hours,
            notes: record.notes || '',
            rawRecord: record,
          };
        })
      );

      setRecentRecords(recentList);

      setStats({
        totalEmployees: profilesRes.data.length,
        activeToday: todayRecordsRes.data?.length || 0,
        totalHoursThisMonth: Math.round(totalMonthHours * 10) / 10,
      });
    }

    setLoading(false);
  };

  const loadLeaveRequests = async () => {
    const { data } = await supabase
      .from('paid_leaves')
      .select('*, profiles(name)')
      .eq('status', 'pending')
      .order('created_at', { ascending: false });

    if (data) {
      setLeaveRequests(data);
    }
  };

  const handleApproveLeave = async (leaveId: string) => {
    await supabase
      .from('paid_leaves')
      .update({ status: 'approved', approved_by: session.user.id })
      .eq('id', leaveId);

    await loadLeaveRequests();
  };

  const handleRejectLeave = async (leaveId: string) => {
    await supabase
      .from('paid_leaves')
      .update({ status: 'rejected', approved_by: session.user.id })
      .eq('id', leaveId);

    await loadLeaveRequests();
  };

  const handleEditRecord = async (id: string, updates: any) => {
    await supabase
      .from('attendance_records')
      .update({
        ...updates,
        last_modified_by: session.user.id,
      })
      .eq('id', id);

    await loadAdminData();
  };

  const handleExportCSV = () => {
    const csvRows = [
      ['従業員名', '日付', '出勤', '退勤', '勤務時間', 'メモ'],
      ...recentRecords.map((r) => [
        r.userName,
        r.date,
        r.checkIn,
        r.checkOut,
        `${r.hours}h`,
        r.notes,
      ]),
    ];

    const csvContent = csvRows.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `全社勤務記録_${monthString}.csv`;
    link.click();
  };

  const handlePreviousMonth = () => {
    setSelectedMonth(new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() - 1));
  };

  const handleNextMonth = () => {
    setSelectedMonth(new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() + 1));
  };

  const monthString = selectedMonth.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Users className="w-6 h-6 text-slate-700" />
            <h1 className="text-xl font-bold text-gray-900">管理者ダッシュボード</h1>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setShowLeaveRequests(!showLeaveRequests)}
              className="relative p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="有給申請"
            >
              <Calendar className="w-5 h-5" />
              {leaveRequests.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {leaveRequests.length}
                </span>
              )}
            </button>
            <button
              onClick={handleExportCSV}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="CSVエクスポート"
            >
              <Download className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-700"></div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-blue-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">総従業員数</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.totalEmployees}</p>
                  </div>
                  <Users className="w-10 h-10 text-blue-500" />
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-green-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">本日の出勤者</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.activeToday}</p>
                  </div>
                  <Calendar className="w-10 h-10 text-green-500" />
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-amber-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">今月の総勤務時間</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.totalHoursThisMonth}h</p>
                  </div>
                  <TrendingUp className="w-10 h-10 text-amber-500" />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-bold text-gray-900">従業員別統計（{monthString}）</h2>
                </div>
                <div className="overflow-y-auto max-h-96">
                  {employees.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">データがありません</div>
                  ) : (
                    <div className="divide-y divide-gray-200">
                      {employees.map((emp) => (
                        <div key={emp.id} className="p-4 hover:bg-gray-50 transition-colors">
                          <div className="flex items-center justify-between mb-2">
                            <h3 className="font-semibold text-gray-900">{emp.name}</h3>
                            <span className="text-lg font-bold text-indigo-600">{emp.totalHours}h</span>
                          </div>
                          <div className="flex gap-4 text-sm text-gray-600">
                            <span>勤務日数: {emp.workDays}日</span>
                            <span>最終出勤: {emp.lastCheckIn}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                  <h2 className="text-lg font-bold text-gray-900">最近の勤務記録</h2>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handlePreviousMonth}
                      className="px-2 py-1 text-sm hover:bg-gray-100 rounded transition-colors text-gray-600"
                    >
                      ← 前月
                    </button>
                    <span className="text-sm font-medium text-gray-700">{monthString}</span>
                    <button
                      onClick={handleNextMonth}
                      className="px-2 py-1 text-sm hover:bg-gray-100 rounded transition-colors text-gray-600"
                    >
                      翌月 →
                    </button>
                  </div>
                </div>
                <div className="overflow-y-auto max-h-96">
                  {recentRecords.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">記録がありません</div>
                  ) : (
                    <div className="divide-y divide-gray-200">
                      {recentRecords.map((record) => (
                        <div key={record.id} className="p-4 hover:bg-gray-50 transition-colors">
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <h3 className="font-semibold text-gray-900">{record.userName}</h3>
                              <p className="text-xs text-gray-500">
                                {new Date(record.date + 'T00:00:00').toLocaleDateString('ja-JP')}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-indigo-600">{record.hours}h</span>
                              <button
                                onClick={() => setEditingRecord(record.rawRecord)}
                                className="p-1.5 hover:bg-indigo-50 rounded transition-colors text-indigo-600"
                                title="編集"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                          <div className="flex gap-4 text-sm text-gray-600">
                            <span>出勤: {record.checkIn}</span>
                            <span>退勤: {record.checkOut}</span>
                          </div>
                          {record.notes && (
                            <p className="mt-2 text-xs text-gray-500 italic">メモ: {record.notes}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </main>

      {editingRecord && (
        <EditRecordModal
          record={editingRecord}
          onClose={() => setEditingRecord(null)}
          onSave={handleEditRecord}
        />
      )}

      {showLeaveRequests && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">有給申請一覧</h2>
              <button
                onClick={() => setShowLeaveRequests(false)}
                className="p-1 hover:bg-gray-100 rounded transition-colors text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="overflow-y-auto max-h-[calc(80vh-80px)]">
              {leaveRequests.length === 0 ? (
                <div className="p-8 text-center text-gray-500">承認待ちの申請はありません</div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {leaveRequests.map((request) => (
                    <div key={request.id} className="p-6 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-semibold text-gray-900">
                            {request.profiles?.name || 'Unknown'}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {new Date(request.leave_date + 'T00:00:00').toLocaleDateString('ja-JP', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric',
                            })}
                          </p>
                        </div>
                        <span className="px-3 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
                          承認待ち
                        </span>
                      </div>
                      {request.reason && (
                        <p className="text-sm text-gray-600 mb-3">理由: {request.reason}</p>
                      )}
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApproveLeave(request.id)}
                          className="flex-1 py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
                        >
                          <Check className="w-4 h-4" />
                          承認
                        </button>
                        <button
                          onClick={() => handleRejectLeave(request.id)}
                          className="flex-1 py-2 px-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                        >
                          <X className="w-4 h-4" />
                          却下
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
