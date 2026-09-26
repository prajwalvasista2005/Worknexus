import React, { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import {
  GraduationCap,
  Building2,
  BookOpen,
  LineChart,
  LogOut,
  Menu,
  X,
  Target,
  User as UserIcon,
  ShieldCheck,
} from 'lucide-react';
import { getRoleDisplayName, normalizeRole } from '../../utils/formatters';

interface PortalLayoutProps {
  children: React.ReactNode;
  activeRole: 'Student' | 'Employer' | 'Institute' | 'Trainer' | 'Admin';
  targetCareer?: string | null;
}

export const PortalLayout: React.FC<PortalLayoutProps> = ({
  children,
  activeRole,
  targetCareer,
}) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const isAdmin = normalizeRole(user?.role) === 'admin';

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/login');
    } catch {
      navigate('/login');
    } finally {
      setIsLoggingOut(false);
    }
  };

  const navItems = [
    {
      name: 'Student Portal',
      path: '/student',
      role: 'Student',
      icon: GraduationCap,
      description: 'Career Readiness & Gap Analysis',
    },
    {
      name: 'Employer Portal',
      path: '/employer',
      role: 'Employer',
      icon: Building2,
      description: 'Requisition & Skill Demand',
    },
    {
      name: 'Institute Portal',
      path: '/institute',
      role: 'Institute',
      icon: BookOpen,
      description: 'Curriculum & Market Alignment',
    },
    {
      name: 'Trainer Hub',
      path: '/trainer',
      role: 'Trainer',
      icon: LineChart,
      description: 'Labour Market Intelligence',
    },
    {
      name: 'Admin Console',
      path: '/admin',
      role: 'Admin',
      icon: ShieldCheck,
      description: 'Career Roles & Skills Governance',
    },
  ];

  // If normal user, filter visible nav items, or if admin show all portals
  const visibleNavItems = isAdmin
    ? navItems
    : navItems.filter((item) => normalizeRole(item.role) === normalizeRole(user?.role));

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Header conforming to 3-zone contract */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Zone 1: Brand wordmark */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-slate-500 hover:text-slate-700"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-slate-900 font-sans">
                WorkNexus
              </span>
              <span className="hidden sm:inline-block text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-100 rounded px-2 py-0.5">
                SkillMesh
              </span>
            </div>
          </div>

          {/* Zone 2: Navigation Links / Portal Switcher */}
          <nav className="hidden md:flex items-center gap-1">
            {isAdmin ? (
              <div className="flex items-center p-1 bg-slate-100 rounded-lg border border-slate-200">
                {navItems.map((item) => {
                  const isActive = location.pathname.startsWith(item.path);
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap ${
                        isActive
                          ? 'bg-white text-indigo-700 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {item.name}
                    </NavLink>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center gap-4 text-xs text-slate-500 font-medium">
                <span>{getRoleDisplayName(user?.role)} Workspace</span>
                {targetCareer && (
                  <>
                    <span aria-hidden="true" className="text-slate-300">·</span>
                    <span className="inline-flex items-center gap-1.5 text-slate-700">
                      <Target className="w-3.5 h-3.5 text-indigo-600" />
                      Target: <strong className="font-semibold text-slate-900">{targetCareer}</strong>
                    </span>
                  </>
                )}
              </div>
            )}
          </nav>

          {/* Zone 3: User info and Logout */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-xs font-semibold text-slate-900 truncate max-w-[160px]">
                {user?.full_name || user?.email || 'User'}
              </span>
              <span className="text-[11px] text-slate-500 flex items-center justify-end gap-1">
                {isAdmin && <ShieldCheck className="w-3 h-3 text-indigo-600" />}
                {getRoleDisplayName(user?.role)}
              </span>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
              title="Logout"
            >
              <LogOut className="w-3.5 h-3.5 text-slate-500" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>

        {/* Mobile dropdown menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-2">
            <div className="pb-2 border-b border-slate-100">
              <p className="text-xs font-semibold text-slate-900">{user?.full_name || 'User'}</p>
              <p className="text-xs text-slate-500">{user?.email}</p>
              <span className="inline-block mt-1 text-[11px] font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                {getRoleDisplayName(user?.role)}
              </span>
            </div>

            <div className="space-y-1">
              {visibleNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.path);
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium ${
                      isActive
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Quiet Footer */}
      <footer className="border-t border-slate-200 bg-white py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <p>© {new Date().getFullYear()} WorkNexus (SkillMesh) · Labour-Market Intelligence Platform</p>
          <div className="flex items-center gap-4">
            <span>Portal: {activeRole}</span>
            <span aria-hidden="true">·</span>
            <span>FastAPI JWT Protected</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
