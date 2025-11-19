import React from 'react';
import Sidebar from './Sidebar';

interface MainLayoutProps {
  children: React.ReactNode;
  onLogout: () => void;
  isAdmin?: boolean;
  userName?: string;
}

const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  onLogout,
  isAdmin,
  userName,
}) => {
  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar
        onLogout={onLogout}
        isAdmin={isAdmin}
        userName={userName}
      />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {children}
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
