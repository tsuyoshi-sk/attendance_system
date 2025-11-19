import React, { useState } from 'react';
import { Users, UserPlus, Settings as SettingsIcon } from 'lucide-react';
import EmployeeManagement from '../components/Admin/EmployeeManagement';
import UserManagement from '../components/Admin/UserManagement';

type TabType = 'employees' | 'users';

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('employees');

  const tabs = [
    { id: 'employees' as TabType, label: '従業員管理', icon: Users },
    { id: 'users' as TabType, label: 'ユーザー管理', icon: UserPlus },
  ];

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">管理画面</h1>
          <p className="text-sm text-slate-600 mt-1">
            従業員とユーザーアカウントの管理
          </p>
        </div>
        <SettingsIcon className="text-slate-400" size={28} />
      </div>

      {/* タブナビゲーション */}
      <div className="card">
        <div className="border-b border-slate-200">
          <nav className="flex -mb-px">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-6 py-4 border-b-2 font-medium text-sm transition-colors
                    ${
                      isActive
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                    }
                  `}
                >
                  <Icon size={18} />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* タブコンテンツ */}
        <div className="p-6">
          {activeTab === 'employees' && <EmployeeManagement />}
          {activeTab === 'users' && <UserManagement />}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
