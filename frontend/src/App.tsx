import { useEffect, useState } from 'react';
import MainLayout from './components/Layout/MainLayout';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import AttendancePage from './pages/AttendancePage';
import ReportsPage from './pages/ReportsPage';
import CalendarPage from './pages/CalendarPage';
import SettingsPage from './pages/SettingsPage';
import apiClient from './lib/api';
import { User } from './types';

type PageType = 'dashboard' | 'attendance' | 'reports' | 'calendar' | 'admin' | 'settings';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState<PageType>('dashboard');
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem('access_token');
      if (token) {
        const user = await apiClient.getCurrentUser();
        setCurrentUser(user);
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
    } catch (error) {
      setIsAuthenticated(false);
      apiClient.clearToken();
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSuccess = async () => {
    try {
      const user = await apiClient.getCurrentUser();
      setCurrentUser(user);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await apiClient.logout();
    } finally {
      setIsAuthenticated(false);
      setCurrentUser(null);
      setCurrentPage('dashboard');
    }
  };

  const handleNavigate = (page: string) => {
    setCurrentPage(page as PageType);
  };

  // ローディング画面
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">読み込み中...</p>
        </div>
      </div>
    );
  }

  // 未認証の場合はログインページ
  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  // 現在のページコンテンツをレンダリング
  const renderPageContent = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'attendance':
        return <AttendancePage />;
      case 'reports':
        return <ReportsPage />;
      case 'calendar':
        return <CalendarPage />;
      case 'settings':
        return <SettingsPage />;
      case 'admin':
        return (
          <div className="card">
            <div className="card-content py-24 text-center text-slate-500">
              <h3 className="text-lg font-medium text-slate-700 mb-2">管理者機能</h3>
              <p>管理者画面は現在開発中です</p>
            </div>
          </div>
        );
      default:
        return <Dashboard />;
    }
  };

  // メインレイアウト
  return (
    <MainLayout
      currentPage={currentPage}
      onNavigate={handleNavigate}
      onLogout={handleLogout}
      isAdmin={currentUser?.is_admin || false}
      userName={currentUser?.name || 'ユーザー'}
    >
      {renderPageContent()}
    </MainLayout>
  );
}

export default App;
