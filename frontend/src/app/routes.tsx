import { RouteObject } from 'react-router-dom';
import { Layout } from './Layout';
import { DashboardPage } from '@/pages/DashboardPage';
import { LoginPage } from '@/pages/LoginPage';
import { CandidatesPage } from '@/pages/CandidatesPage';
import { ModulesPlaceholderPage } from '@/pages/ModulesPlaceholderPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export const routes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
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
        element: <ModulesPlaceholderPage />,
      },
      {
        path: 'projects',
        element: <ModulesPlaceholderPage />,
      },
      {
        path: 'internships',
        element: <ModulesPlaceholderPage />,
      },
      {
        path: 'certificates',
        element: <ModulesPlaceholderPage />,
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
