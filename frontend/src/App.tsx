import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import LoginPage from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EmployeesPage } from "./pages/EmployeesPage";
import { EmployeeDetailPage } from "./pages/EmployeeDetailPage";
import { AttendancePage } from "./pages/AttendancePage";
import { ReportsPage } from "./pages/ReportsPage";
import CalendarPage from "./pages/CalendarPage";
import SettingsPage from "./pages/SettingsPage";
import AdminPage from "./pages/AdminPage";
import apiClient from "./lib/api";
import { User } from "./types";

// A wrapper for authenticated routes
function ProtectedRoute({ isAuthenticated, children }: { isAuthenticated: boolean, children: JSX.Element }) {
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem("access_token"));
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  useEffect(() => {
    // Only check auth status if a token exists, to avoid unnecessary API calls on first visit.
    if (isAuthenticated) {
      checkAuthStatus();
    } else {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const checkAuthStatus = async () => {
    try {
      setIsLoading(true);
      const user = await apiClient.getCurrentUser();
      setCurrentUser(user);
      setIsAuthenticated(true);
    } catch (error) {
      setIsAuthenticated(false);
      apiClient.clearToken();
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = async () => {
    try {
      await apiClient.logout();
    } finally {
      setIsAuthenticated(false);
      setCurrentUser(null);
    }
  };

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

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <LoginPage onLoginSuccess={handleLoginSuccess} />
            )
          }
        />
        <Route
          path="/*"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <MainLayout
                onLogout={handleLogout}
                isAdmin={currentUser?.role === "admin" || false}
                userName={currentUser?.username || "ユーザー"}
              >
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/attendance" element={<AttendancePage />} />
                  <Route path="/reports" element={<ReportsPage />} />
                  <Route path="/employees" element={<EmployeesPage />} />
                  <Route path="/employees/:id" element={<EmployeeDetailPage />} />
                  <Route path="/calendar" element={<CalendarPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  {currentUser?.role === "admin" && (
                    <Route path="/admin" element={<AdminPage />} />
                  )}
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </MainLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
