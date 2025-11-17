import { useEffect, useState } from 'react';
import { Bell, X } from 'lucide-react';

interface NotificationBannerProps {
  session: any;
}

export default function NotificationBanner({ session }: NotificationBannerProps) {
  const [show, setShow] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    checkClockInReminder();

    const interval = setInterval(checkClockInReminder, 60000);
    return () => clearInterval(interval);
  }, []);

  const checkClockInReminder = () => {
    const now = new Date();
    const hour = now.getHours();
    const minute = now.getMinutes();
    const dayOfWeek = now.getDay();

    if (dayOfWeek === 0 || dayOfWeek === 6) {
      setShow(false);
      return;
    }

    const lastDismissed = localStorage.getItem('notificationDismissed');
    const today = now.toISOString().split('T')[0];

    if (lastDismissed === today) {
      setShow(false);
      return;
    }

    if (hour === 9 && minute < 30) {
      setMessage('出勤の打刻をお忘れなく！');
      setShow(true);
    } else if (hour === 18 && minute < 30) {
      setMessage('退勤の打刻をお忘れなく！');
      setShow(true);
    } else {
      setShow(false);
    }
  };

  const handleDismiss = () => {
    const today = new Date().toISOString().split('T')[0];
    localStorage.setItem('notificationDismissed', today);
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-4 rounded-r-lg shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell className="w-5 h-5 text-amber-600" />
          <p className="text-sm font-medium text-amber-800">{message}</p>
        </div>
        <button
          onClick={handleDismiss}
          className="p-1 hover:bg-amber-100 rounded transition-colors text-amber-600"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
