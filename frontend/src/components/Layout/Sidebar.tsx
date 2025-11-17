import React from 'react';
import {
  Home,
  Clock,
  BarChart3,
  Settings,
  LogOut,
  Users,
  Calendar,
} from 'lucide-react';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  onLogout: () => void;
  isAdmin?: boolean;
  userName?: string;
}

const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  onLogout,
  isAdmin = false,
  userName = 'ユーザー',
}) => {
  const menuItems = [
    { id: 'dashboard', label: 'ダッシュボード', icon: Home },
    { id: 'attendance', label: '打刻履歴', icon: Clock },
    { id: 'reports', label: 'レポート', icon: BarChart3 },
    { id: 'calendar', label: 'カレンダー', icon: Calendar },
    ...(isAdmin ? [{ id: 'admin', label: '管理者画面', icon: Users }] : []),
    { id: 'settings', label: '設定', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen">
      {/* ロゴ・ヘッダー */}
      <div className="px-6 py-5 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900">勤怠管理</h1>
        <p className="text-sm text-slate-500 mt-1">Attendance System</p>
      </div>

      {/* ユーザー情報 */}
      <div className="px-6 py-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-semibold">
            {userName.charAt(0)}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-900">{userName}</p>
            <p className="text-xs text-slate-500">
              {isAdmin ? '管理者' : '一般ユーザー'}
            </p>
          </div>
        </div>
      </div>

      {/* ナビゲーションメニュー */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`nav-item w-full ${isActive ? 'nav-item-active' : ''}`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* ログアウトボタン */}
      <div className="px-3 py-4 border-t border-slate-200">
        <button
          onClick={onLogout}
          className="nav-item w-full text-red-600 hover:bg-red-50"
        >
          <LogOut size={20} />
          <span>ログアウト</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
