import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Layers, Activity, Users, FileText, FolderGit2, Award, Briefcase, LogOut, LogIn, History } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { NotificationBell } from '@/components/NotificationBell';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();

  const isSuperAdminOrOps = user?.roles.some((r) =>
    ['ROLE_SUPER_ADMIN', 'ROLE_OPS_ADMIN', 'ROLE_READ_ONLY'].includes(r)
  );

  const navItems = [
    { name: 'Dashboard', path: '/', icon: Activity },
    { name: 'Candidates', path: '/candidates', icon: Users },
    { name: 'Assignments', path: '/assignments', icon: FileText },
    { name: 'Projects', path: '/projects', icon: FolderGit2 },
    { name: 'Internships', path: '/internships', icon: Briefcase },
    { name: 'Certificates', path: '/certificates', icon: Award },
    ...(isSuperAdminOrOps ? [{ name: 'Audit Trail', path: '/audit', icon: History }] : []),
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const formatRole = (role: string) => {
    return role.replace('ROLE_', '').replace('_', ' ');
  };

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo & Name */}
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2.5 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-700 to-brand-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20 group-hover:scale-105 transition-transform">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xl font-bold tracking-tight text-slate-900 group-hover:text-brand-600 transition-colors">
                  ExcelR <span className="text-brand-600">Track360</span>
                </span>
                <span className="hidden sm:block text-[11px] font-medium text-slate-500 tracking-wide uppercase">
                  Student Lifecycle & Operations
                </span>
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* User Profile / Auth State & Status Badge */}
          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Phase 13: Live Alerts Active</span>
            </div>

            {isAuthenticated && user ? (
              <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
                <NotificationBell />
                <div className="hidden lg:flex flex-col text-right">
                  <span className="text-xs font-semibold text-slate-800 leading-tight">
                    {user.full_name}
                  </span>
                  <div className="flex items-center gap-1 justify-end">
                    <span className="text-[10px] font-medium text-slate-500 truncate max-w-[120px]">
                      {user.email}
                    </span>
                    {user.roles[0] && (
                      <span className="bg-slate-100 text-slate-700 px-1.5 py-0.2 rounded text-[9px] font-bold">
                        {formatRole(user.roles[0])}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
