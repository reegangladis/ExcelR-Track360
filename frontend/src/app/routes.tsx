import { RouteObject } from 'react-router-dom';
import { Layout } from './Layout';
import { DashboardPage } from '@/pages/DashboardPage';
import { LoginPage } from '@/pages/LoginPage';
import { CandidatesPage } from '@/pages/CandidatesPage';
import { AssignmentsPage } from '@/pages/AssignmentsPage';
import { ProjectsPage } from '@/pages/ProjectsPage';
import { InternshipsPage } from '@/pages/InternshipsPage';
import { CertificatesPage } from '@/pages/CertificatesPage';
import { PublicVerifyPage } from '@/pages/PublicVerifyPage';
import { ModulesPlaceholderPage } from '@/pages/ModulesPlaceholderPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export const routes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/verify',
    element: <PublicVerifyPage />,
  },
  {
    path: '/verify/:identifier',
    element: <PublicVerifyPage />,
  },
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'candidates',
        element: (
          <ProtectedRoute>
            <CandidatesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'assignments',
        element: (
          <ProtectedRoute>
            <AssignmentsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'projects',
        element: (
          <ProtectedRoute>
            <ProjectsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'internships',
        element: (
          <ProtectedRoute>
            <InternshipsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'certificates',
        element: (
          <ProtectedRoute>
            <CertificatesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'audit',
        element: <ModulesPlaceholderPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
];
