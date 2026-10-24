import { RouteObject } from 'react-router-dom';
import { Layout } from './Layout';
import { DashboardPage } from '@/pages/DashboardPage';
import { ModulesPlaceholderPage } from '@/pages/ModulesPlaceholderPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

export const routes: RouteObject[] = [
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
        element: <ModulesPlaceholderPage />,
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
