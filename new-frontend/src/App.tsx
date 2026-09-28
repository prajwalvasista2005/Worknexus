import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { StudentPortal } from './pages/StudentPortal';
import { EmployerPortal } from './pages/EmployerPortal';
import { InstitutePortal } from './pages/InstitutePortal';
import { TrainerHub } from './pages/TrainerHub';
import { AdminPortal } from './pages/AdminPortal';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { normalizeRole } from './utils/formatters';

const RootRedirect: React.FC = () => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-500">Loading WorkNexus...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  const role = normalizeRole(user.role);
  if (role === 'employer') {
    return <Navigate to="/employer" replace />;
  }
  if (role === 'institute') {
    return <Navigate to="/institute" replace />;
  }
  if (role === 'trainer') {
    return <Navigate to="/trainer" replace />;
  }
  if (role === 'admin') {
    return <Navigate to="/admin" replace />;
  }
  return <Navigate to="/student" replace />;
};

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Routes>
            {/* Root Dispatcher */}
            <Route path="/" element={<RootRedirect />} />

            {/* Public Authentication Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Portal Routes */}
            <Route
              path="/student"
              element={
                <ProtectedRoute allowedRole="Student">
                  <StudentPortal />
                </ProtectedRoute>
              }
            />

            <Route
              path="/employer"
              element={
                <ProtectedRoute allowedRole="Employer">
                  <EmployerPortal />
                </ProtectedRoute>
              }
            />

            <Route
              path="/institute"
              element={
                <ProtectedRoute allowedRole="Institute">
                  <InstitutePortal />
                </ProtectedRoute>
              }
            />

            <Route
              path="/trainer"
              element={
                <ProtectedRoute allowedRole="Trainer">
                  <TrainerHub />
                </ProtectedRoute>
              }
            />

            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRole="Admin">
                  <AdminPortal />
                </ProtectedRoute>
              }
            />

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
