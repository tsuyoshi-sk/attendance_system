import { Clock, CheckCircle2, XCircle } from 'lucide-react';

interface TodayStatusProps {
  record: any;
}

export default function TodayStatus({ record }: TodayStatusProps) {
  const formatTime = (timeString: string) => {
    if (!timeString) return '--:--';
    return new Date(timeString).toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const calculateWorkHours = () => {
    if (!record || !record.check_in_time) return null;

    const checkIn = new Date(record.check_in_time);
    const checkOut = record.check_out_time ? new Date(record.check_out_time) : new Date();

    const diffMs = checkOut.getTime() - checkIn.getTime();
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    return `${hours}時間${minutes}分`;
  };

  const isClockedIn = record && record.check_in_time && !record.check_out_time;
  const isClockedOut = record && record.check_in_time && record.check_out_time;

  return (
    <div className="grid grid-cols-2 gap-4 mb-6">
      <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center gap-2 mb-2">
          <Clock className="w-4 h-4 text-blue-600" />
          <span className="text-xs font-medium text-blue-700">出勤時刻</span>
        </div>
        <p className="text-2xl font-bold text-blue-900">
          {record ? formatTime(record.check_in_time) : '--:--'}
        </p>
        {record && (
          <p className="text-xs text-blue-600 mt-1">
            {record.check_in_time
              ? new Date(record.check_in_time).toLocaleDateString('ja-JP')
              : '本日'}
          </p>
        )}
      </div>

      <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg p-4 border border-amber-200">
        <div className="flex items-center gap-2 mb-2">
          <Clock className="w-4 h-4 text-amber-600" />
          <span className="text-xs font-medium text-amber-700">退勤時刻</span>
        </div>
        <p className="text-2xl font-bold text-amber-900">
          {record && record.check_out_time ? formatTime(record.check_out_time) : '--:--'}
        </p>
        {record && record.check_out_time && (
          <p className="text-xs text-amber-600 mt-1">
            {new Date(record.check_out_time).toLocaleDateString('ja-JP')}
          </p>
        )}
      </div>

      {isClockedIn && (
        <div className="col-span-2 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200 flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0" />
          <div>
            <p className="font-semibold text-green-900">出勤中</p>
            <p className="text-sm text-green-700">
              {calculateWorkHours()} 経過
            </p>
          </div>
        </div>
      )}

      {isClockedOut && (
        <div className="col-span-2 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg p-4 border border-gray-300 flex items-center gap-3">
          <XCircle className="w-6 h-6 text-gray-600 flex-shrink-0" />
          <div>
            <p className="font-semibold text-gray-900">退勤済み</p>
            <p className="text-sm text-gray-700">
              本日の勤務時間：{calculateWorkHours()}
            </p>
          </div>
        </div>
      )}

      {!record && (
        <div className="col-span-2 bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg p-4 border border-indigo-200">
          <p className="text-center text-indigo-700 font-medium">
            出勤ボタンを押して開始してください
          </p>
        </div>
      )}
    </div>
  );
}
