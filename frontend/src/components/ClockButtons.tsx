import { CheckCircle2, LogOut } from 'lucide-react';

interface ClockButtonsProps {
  record: any;
  loading: boolean;
  workPattern: any;
  onClockIn: () => void;
  onClockOut: () => void;
}

export default function ClockButtons({
  record,
  loading,
  workPattern,
  onClockIn,
  onClockOut,
}: ClockButtonsProps) {
  const isClockedIn = record && record.check_in_time && !record.check_out_time;
  const isClockInDisabled = record && record.check_in_time;

  const checkIfLate = () => {
    if (!workPattern || workPattern.is_flexible) return false;
    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    const [startHour, startMin] = workPattern.start_time.split(':').map(Number);
    const startTimeMin = startHour * 60 + startMin;
    return currentTime > startTimeMin + 15;
  };

  const isLate = checkIfLate();

  return (
    <div className="space-y-3">
      <button
        onClick={onClockIn}
        disabled={isClockInDisabled || loading}
        className={`w-full py-4 px-6 rounded-xl font-semibold text-white text-lg transition-all flex items-center justify-center gap-3 ${
          isClockInDisabled
            ? 'bg-gray-400 cursor-not-allowed opacity-60'
            : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 active:scale-95'
        } ${loading ? 'opacity-50' : ''}`}
      >
        <CheckCircle2 className="w-6 h-6" />
        {loading && !isClockedIn ? '処理中...' : '出勤'}
      </button>
      {isLate && !isClockInDisabled && (
        <p className="text-sm text-amber-600 font-medium text-center">遅刻になります</p>
      )}

      <button
        onClick={onClockOut}
        disabled={!isClockedIn || loading}
        className={`w-full py-4 px-6 rounded-xl font-semibold text-white text-lg transition-all flex items-center justify-center gap-3 ${
          isClockedIn
            ? 'bg-gradient-to-r from-red-500 to-orange-600 hover:from-red-600 hover:to-orange-700 active:scale-95'
            : 'bg-gray-400 cursor-not-allowed opacity-60'
        } ${loading ? 'opacity-50' : ''}`}
      >
        <LogOut className="w-6 h-6" />
        {loading && isClockedIn ? '処理中...' : '退勤'}
      </button>
    </div>
  );
}
