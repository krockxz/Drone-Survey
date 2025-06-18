/**
 * Main App component for the Drone Survey Management System.
 * 
 * Provides routing, layout, and global state management initialization.
 */

import React, { useEffect } from 'react';
import { Routes, Route, Navigate, Link } from 'react-router-dom';
import { AppShell, Burger, Group, Text, NavLink, rem, Grid, Card, Button, Alert } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import {
  IconDrone,
  IconMap,
  IconChartBar,
  IconSettings,
  IconActivity,
  IconList,
} from '@tabler/icons-react';

import { useWebSocket } from '@/utils/websocket';
import { useDroneStore } from '@/stores/droneStore';
import { useMissionStore } from '@/stores/missionStore';

// Import enhanced components
import { AnalyticsDashboard } from '@/features/ai-analytics/components/AnalyticsDashboard';
import { AIMissionPlanner } from '@/features/ai-analytics/components/AIMissionPlanner';
import { MissionControlCenter } from '@/features/mission-control/components/MissionControlCenter';

// Enhanced Dashboard with AI insights
const Dashboard = () => (
  <div style={{ padding: 20 }}>
    <Text size="xl" fw={700}>AI-Powered Drone Operations Center</Text>
    <Text c="dimmed" mb="xl">Advanced autonomous drone survey management with intelligent optimization</Text>
    
    <Grid>
      <Grid.Col span={12}>
        <Alert
          icon={<IconActivity size={16} />}
          title="Welcome to the Future of Drone Operations"
          color="blue"
          variant="light"
          mb="md"
        >
          Experience next-generation drone management with AI-powered mission planning, 
          real-time 3D visualization, predictive analytics, and intelligent fleet optimization.
        </Alert>
      </Grid.Col>
      
      <Grid.Col span={6}>
        <Card withBorder p="md">
          <Text fw={600} mb="sm">🤖 AI Mission Planner</Text>
          <Text size="sm" c="dimmed" mb="md">
            Intelligent mission optimization with terrain analysis, weather integration, 
            and predictive success modeling.
          </Text>
          <Button variant="light" fullWidth component={Link} to="/planning">
            Launch AI Planner
          </Button>
        </Card>
      </Grid.Col>
      
      <Grid.Col span={6}>
        <Card withBorder p="md">
          <Text fw={600} mb="sm">🎯 3D Mission Control</Text>
          <Text size="sm" c="dimmed" mb="md">
            Real-time 3D visualization with animated drone tracking, 
            interactive flight paths, and emergency controls.
          </Text>
          <Button variant="light" fullWidth component={Link} to="/monitoring">
            Open Control Center
          </Button>
        </Card>
      </Grid.Col>
      
      <Grid.Col span={6}>
        <Card withBorder p="md">
          <Text fw={600} mb="sm">📊 Advanced Analytics</Text>
          <Text size="sm" c="dimmed" mb="md">
            Comprehensive performance insights, predictive maintenance, 
            and ROI optimization with real-time dashboards.
          </Text>
          <Button variant="light" fullWidth component={Link} to="/analytics">
            View Analytics
          </Button>
        </Card>
      </Grid.Col>
      
      <Grid.Col span={6}>
        <Card withBorder p="md">
          <Text fw={600} mb="sm">🚁 Fleet Management</Text>
          <Text size="sm" c="dimmed" mb="md">
            Smart drone assignment, battery optimization, 
            and predictive maintenance scheduling.
          </Text>
          <Button variant="light" fullWidth component={Link} to="/fleet">
            Manage Fleet
          </Button>
        </Card>
      </Grid.Col>
    </Grid>
    
    <Text mt="xl" size="sm" c="dimmed" ta="center">
      🏆 Built for the FlytBase Assignment - Showcasing AI-powered drone operations
    </Text>
  </div>
);

const FleetManagement = () => (
  <div style={{ padding: 20 }}>
    <Text size="xl" fw={700}>Smart Fleet Management</Text>
    <Text c="dimmed" mb="md">AI-powered drone fleet optimization and monitoring</Text>
    
    <Alert icon={<IconDrone size={16} />} color="blue" variant="light" mb="xl">
      This section would contain advanced fleet management features including 
      predictive maintenance, smart scheduling, and performance optimization.
    </Alert>
    
    <Text>Key Features:</Text>
    <ul>
      <li>🤖 AI-powered drone assignment and scheduling</li>
      <li>🔋 Smart battery management and charging optimization</li>
      <li>🔧 Predictive maintenance with ML-based failure prediction</li>
      <li>📈 Real-time performance monitoring and efficiency tracking</li>
      <li>⚡ Emergency response and automatic failover systems</li>
    </ul>
  </div>
);

const MissionPlanning = () => <AIMissionPlanner />;

const MissionMonitoring = () => <MissionControlCenter />;

const Analytics = () => <AnalyticsDashboard />;

function App() {
  const [opened, { toggle }] = useDisclosure();
  const { connect, disconnect, isConnected } = useWebSocket();
  const fetchDrones = useDroneStore((state) => state.fetchDrones);
  const fetchMissions = useMissionStore((state) => state.fetchMissions);
  const subscribeToFleetUpdates = useDroneStore((state) => state.subscribeToFleetUpdates);

  // Initialize app data and WebSocket connection
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Fetch initial data
        await Promise.all([
          fetchDrones(),
          fetchMissions(),
        ]);

        // Connect WebSocket for real-time updates
        const connected = await connect();
        if (connected) {
          subscribeToFleetUpdates();
          notifications.show({
            title: 'Connected',
            message: 'Real-time updates enabled',
            color: 'green',
          });
        }
      } catch (error) {
        console.error('Failed to initialize app:', error);
        notifications.show({
          title: 'Initialization Error',
          message: 'Failed to load initial data',
          color: 'red',
        });
      }
    };

    initializeApp();

    // Cleanup WebSocket on unmount
    return () => {
      disconnect();
    };
  }, [connect, disconnect, fetchDrones, fetchMissions, subscribeToFleetUpdates]);

  const navLinks = [
    { icon: IconActivity, label: 'Dashboard', path: '/' },
    { icon: IconDrone, label: 'Fleet Management', path: '/fleet' },
    { icon: IconMap, label: 'Mission Planning', path: '/planning' },
    { icon: IconList, label: 'Mission Monitoring', path: '/monitoring' },
    { icon: IconChartBar, label: 'Analytics', path: '/analytics' },
  ];

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 300,
        breakpoint: 'sm',
        collapsed: { mobile: !opened },
      }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md">
          <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
          <Group>
            <IconDrone size={32} color="var(--mantine-color-blue-6)" />
            <Text size="lg" fw={700}>
              Drone Survey System
            </Text>
          </Group>
          <Group ml="auto">
            <Text size="sm" c="dimmed">
              {isConnected() ? '🟢 Connected' : '🔴 Disconnected'}
            </Text>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Text size="sm" c="dimmed" mb="md">
          Navigation
        </Text>
        {navLinks.map((link) => (
          <NavLink
            key={link.path}
            href={link.path}
            label={link.label}
            leftSection={<link.icon size={rem(16)} />}
            mb="xs"
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/fleet" element={<FleetManagement />} />
          <Route path="/planning" element={<MissionPlanning />} />
          <Route path="/monitoring" element={<MissionMonitoring />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}

export default App;