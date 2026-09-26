import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { hasRoleAccess, normalizeRole } from '../../utils/formatters';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRole?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRole }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-slate-500">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role authorization
  if (allowedRole && !hasRoleAccess(user.role, allowedRole)) {
    const userRoleNorm = normalizeRole(user.role);
    // Redirect to user's assigned portal
    let targetPath = '/student';
    if (userRoleNorm === 'employer') targetPath = '/employer';
    else if (userRoleNorm === 'institute') targetPath = '/institute';
    else if (userRoleNorm === 'trainer') targetPath = '/trainer';

    return <Navigate to={targetPath} replace />;
  }

  return <>{children}</>;
};
