/**
 * Main entry point for the Drone Survey Management System frontend.
 * 
 * Sets up React app with Mantine UI, React Query, and routing.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { ModalsProvider } from '@mantine/modals';

import App from './App';

// Import Mantine styles
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/charts/styles.css';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.status >= 400 && error?.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
    },
    mutations: {
      retry: false,
    },
  },
});

// Mantine theme configuration
const theme = {
  primaryColor: 'blue',
  colors: {
    blue: [
      '#e3f2fd',
      '#bbdefb', 
      '#90caf9',
      '#64b5f6',
      '#42a5f5',
      '#2196f3',
      '#1e88e5',
      '#1976d2',
      '#1565c0',
      '#0d47a1'
    ],
  },
  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
  headings: {
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
  },
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme}>
        <Notifications position="top-right" />
        <ModalsProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ModalsProvider>
      </MantineProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);