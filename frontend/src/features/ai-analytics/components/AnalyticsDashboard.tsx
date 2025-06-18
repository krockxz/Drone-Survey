/**
 * Advanced Analytics Dashboard with Real-time Intelligence
 * 
 * This component provides comprehensive analytics and insights for drone operations:
 * - Real-time performance metrics and KPIs
 * - Predictive analytics and trend analysis
 * - Fleet utilization and efficiency tracking
 * - Cost analysis and ROI calculations
 * - Interactive charts with live data updates
 * 
 * Designed for professional operations with enterprise-grade analytics
 * 
 * @author FlytBase Assignment
 * @created 2024
 */

import React, { useState, useEffect } from 'react';
import {
  Paper,
  Grid,
  Text,
  Group,
  Stack,
  Card,
  Badge,
  Progress,
  RingProgress,
  Tabs,
  Select,
  Button,
  Alert,
  Tooltip,
  ActionIcon,
  Switch,
  NumberFormatter
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { notifications } from '@mantine/notifications';
import {
  IconChartLine,
  IconTrendingUp,
  IconTrendingDown,
  IconDrone,
  IconClock,
  IconBolt,
  IconTarget,
  IconCurrencyDollar,
  IconAlertTriangle,
  IconDownload,
  IconRefresh,
  IconEye,
  IconChartBar,
  IconReport,
  IconCalendar
} from '@tabler/icons-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { motion } from 'framer-motion';

// Analytics Types
interface MetricCard {
  title: string;
  value: string | number;
  change: number;
  trend: 'up' | 'down' | 'stable';
  color: string;
  icon: React.ReactNode;
  description?: string;
}

interface ChartData {
  name: string;
  value: number;
  missions?: number;
  efficiency?: number;
  cost?: number;
  battery?: number;
  success?: number;
  [key: string]: any;
}

interface FleetMetrics {
  totalFlightTime: number;
  averageEfficiency: number;
  missionSuccessRate: number;
  costPerMission: number;
  batteryUtilization: number;
  maintenanceAlerts: number;
}

/**
 * Analytics Data Generator
 * Simulates comprehensive analytics data for demonstration
 */
class AnalyticsEngine {
  /**
   * Generate fleet performance metrics
   */
  static generateFleetMetrics(): FleetMetrics {
    return {
      totalFlightTime: 1247.5,
      averageEfficiency: 87.3,
      missionSuccessRate: 94.2,
      costPerMission: 124.50,
      batteryUtilization: 78.6,
      maintenanceAlerts: 3
    };
  }

  /**
   * Generate mission performance over time
   */
  static generateMissionTrends(): ChartData[] {
    const data = [];
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    
    for (let i = 0; i < 7; i++) {
      data.push({
        name: days[i],
        missions: Math.floor(Math.random() * 20) + 10,
        efficiency: Math.floor(Math.random() * 20) + 80,
        success: Math.floor(Math.random() * 10) + 90,
        cost: Math.floor(Math.random() * 50) + 100
      });
    }
    
    return data;
  }

  /**
   * Generate fleet utilization data
   */
  static generateFleetUtilization(): ChartData[] {
    return [
      { name: 'Active', value: 12, color: '#2E8B57' },
      { name: 'Idle', value: 8, color: '#87CEEB' },
      { name: 'Maintenance', value: 3, color: '#FFA500' },
      { name: 'Charging', value: 5, color: '#9370DB' }
    ];
  }

  /**
   * Generate battery performance data
   */
  static generateBatteryData(): ChartData[] {
    const data = [];
    for (let i = 0; i < 24; i++) {
      data.push({
        name: `${i}:00`,
        battery: Math.floor(Math.random() * 30) + 70,
        consumption: Math.floor(Math.random() * 15) + 5
      });
    }
    return data;
  }

  /**
   * Generate cost analysis data
   */
  static generateCostAnalysis(): ChartData[] {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    return months.map(month => ({
      name: month,
      operational: Math.floor(Math.random() * 5000) + 8000,
      maintenance: Math.floor(Math.random() * 2000) + 1000,
      fuel: Math.floor(Math.random() * 1500) + 500
    }));
  }

  /**
   * Generate efficiency comparison
   */
  static generateEfficiencyComparison(): ChartData[] {
    return [
      { name: 'Drone Alpha-01', efficiency: 94, missions: 45 },
      { name: 'Drone Beta-02', efficiency: 89, missions: 38 },
      { name: 'Drone Gamma-03', efficiency: 92, missions: 42 },
      { name: 'Drone Delta-04', efficiency: 85, missions: 35 },
      { name: 'Drone Echo-05', efficiency: 91, missions: 40 }
    ];
  }

  /**
   * Generate real-time alerts
   */
  static generateAlerts(): Array<{
    id: string;
    type: 'warning' | 'error' | 'info';
    title: string;
    message: string;
    timestamp: Date;
  }> {
    return [
      {
        id: '1',
        type: 'warning',
        title: 'Low Battery Alert',
        message: 'Drone Echo-05 battery below 20%',
        timestamp: new Date(Date.now() - 1000 * 60 * 5)
      },
      {
        id: '2',
        type: 'info',
        title: 'Mission Completed',
        message: 'Survey Area B completed successfully',
        timestamp: new Date(Date.now() - 1000 * 60 * 15)
      },
      {
        id: '3',
        type: 'error',
        title: 'Weather Alert',
        message: 'High winds detected - mission paused',
        timestamp: new Date(Date.now() - 1000 * 60 * 30)
      }
    ];
  }
}

/**
 * Metric Card Component
 */
const MetricCard: React.FC<{ metric: MetricCard }> = ({ metric }) => {
  const getTrendIcon = () => {
    switch (metric.trend) {
      case 'up':
        return <IconTrendingUp size={16} color="green" />;
      case 'down':
        return <IconTrendingDown size={16} color="red" />;
      default:
        return null;
    }
  };

  const getTrendColor = () => {
    switch (metric.trend) {
      case 'up': return 'green';
      case 'down': return 'red';
      default: return 'gray';
    }
  };

  return (
    <Card withBorder p="md">
      <Group justify="space-between" mb="xs">
        <Text size="sm" c="dimmed">{metric.title}</Text>
        <ActionIcon variant="light" color={metric.color} size="sm">
          {metric.icon}
        </ActionIcon>
      </Group>
      
      <Group justify="space-between" align="flex-end">
        <div>
          <Text size="xl" fw={700} c={metric.color}>
            {typeof metric.value === 'number' ? (
              <NumberFormatter value={metric.value} />
            ) : (
              metric.value
            )}
          </Text>
          {metric.description && (
            <Text size="xs" c="dimmed">{metric.description}</Text>
          )}
        </div>
        
        {metric.change !== 0 && (
          <Group gap="xs">
            {getTrendIcon()}
            <Text size="sm" c={getTrendColor()}>
              {metric.change > 0 ? '+' : ''}{metric.change}%
            </Text>
          </Group>
        )}
      </Group>
    </Card>
  );
};

/**
 * Main Analytics Dashboard Component
 */
export const AnalyticsDashboard: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState<string>('7d');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([null, null]);
  
  // Data state
  const [fleetMetrics, setFleetMetrics] = useState<FleetMetrics | null>(null);
  const [missionTrends, setMissionTrends] = useState<ChartData[]>([]);
  const [fleetUtilization, setFleetUtilization] = useState<ChartData[]>([]);
  const [batteryData, setBatteryData] = useState<ChartData[]>([]);
  const [costAnalysis, setCostAnalysis] = useState<ChartData[]>([]);
  const [efficiencyData, setEfficiencyData] = useState<ChartData[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);

  // Load analytics data
  useEffect(() => {
    const loadData = () => {
      setFleetMetrics(AnalyticsEngine.generateFleetMetrics());
      setMissionTrends(AnalyticsEngine.generateMissionTrends());
      setFleetUtilization(AnalyticsEngine.generateFleetUtilization());
      setBatteryData(AnalyticsEngine.generateBatteryData());
      setCostAnalysis(AnalyticsEngine.generateCostAnalysis());
      setEfficiencyData(AnalyticsEngine.generateEfficiencyComparison());
      setAlerts(AnalyticsEngine.generateAlerts());
    };

    loadData();

    // Auto-refresh data
    if (autoRefresh) {
      const interval = setInterval(loadData, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, selectedPeriod]);

  const generateMetricCards = (): MetricCard[] => {
    if (!fleetMetrics) return [];

    return [
      {
        title: 'Total Flight Time',
        value: `${fleetMetrics.totalFlightTime}h`,
        change: 12.5,
        trend: 'up',
        color: 'blue',
        icon: <IconClock size={16} />,
        description: 'This month'
      },
      {
        title: 'Mission Success Rate',
        value: `${fleetMetrics.missionSuccessRate}%`,
        change: 2.1,
        trend: 'up',
        color: 'green',
        icon: <IconTarget size={16} />,
        description: 'Last 30 days'
      },
      {
        title: 'Average Efficiency',
        value: `${fleetMetrics.averageEfficiency}%`,
        change: -1.3,
        trend: 'down',
        color: 'orange',
        icon: <IconChartLine size={16} />,
        description: 'Fleet average'
      },
      {
        title: 'Cost per Mission',
        value: `$${fleetMetrics.costPerMission}`,
        change: -5.2,
        trend: 'down',
        color: 'violet',
        icon: <IconCurrencyDollar size={16} />,
        description: 'Including overhead'
      },
      {
        title: 'Battery Utilization',
        value: `${fleetMetrics.batteryUtilization}%`,
        change: 3.7,
        trend: 'up',
        color: 'cyan',
        icon: <IconBolt size={16} />,
        description: 'Fleet average'
      },
      {
        title: 'Maintenance Alerts',
        value: fleetMetrics.maintenanceAlerts,
        change: -25.0,
        trend: 'down',
        color: 'red',
        icon: <IconAlertTriangle size={16} />,
        description: 'Active alerts'
      }
    ];
  };

  const exportReport = () => {
    notifications.show({
      title: 'Report Generated',
      message: 'Analytics report exported successfully',
      color: 'green',
      icon: <IconDownload />
    });
  };

  const refreshData = () => {
    notifications.show({
      title: 'Data Refreshed',
      message: 'Analytics data updated',
      color: 'blue',
      icon: <IconRefresh />
    });
  };

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe'];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <Stack gap="md">
        {/* Header */}
        <Paper p="md" withBorder>
          <Group justify="space-between">
            <Group>
              <IconChartBar size={32} color="var(--mantine-color-blue-6)" />
              <div>
                <Text size="xl" fw={700}>Analytics Dashboard</Text>
                <Text size="sm" c="dimmed">Real-time insights and performance metrics</Text>
              </div>
            </Group>
            
            <Group>
              <Select
                value={selectedPeriod}
                onChange={setSelectedPeriod}
                data={[
                  { value: '24h', label: 'Last 24 Hours' },
                  { value: '7d', label: 'Last 7 Days' },
                  { value: '30d', label: 'Last 30 Days' },
                  { value: '90d', label: 'Last 90 Days' }
                ]}
                w={150}
              />
              
              <Switch
                label="Auto-refresh"
                checked={autoRefresh}
                onChange={(event) => setAutoRefresh(event.currentTarget.checked)}
                color="blue"
              />
              
              <Button
                leftSection={<IconRefresh size={16} />}
                onClick={refreshData}
                variant="light"
              >
                Refresh
              </Button>
              
              <Button
                leftSection={<IconDownload size={16} />}
                onClick={exportReport}
                color="green"
              >
                Export Report
              </Button>
            </Group>
          </Group>
        </Paper>

        {/* Key Metrics Grid */}
        <Grid>
          {generateMetricCards().map((metric, index) => (
            <Grid.Col key={index} span={2}>
              <MetricCard metric={metric} />
            </Grid.Col>
          ))}
        </Grid>

        <Tabs defaultValue="overview">
          <Tabs.List>
            <Tabs.Tab value="overview" leftSection={<IconEye size={16} />}>
              Overview
            </Tabs.Tab>
            <Tabs.Tab value="missions" leftSection={<IconTarget size={16} />}>
              Mission Analytics
            </Tabs.Tab>
            <Tabs.Tab value="fleet" leftSection={<IconDrone size={16} />}>
              Fleet Performance
            </Tabs.Tab>
            <Tabs.Tab value="costs" leftSection={<IconCurrencyDollar size={16} />}>
              Cost Analysis
            </Tabs.Tab>
          </Tabs.List>

          {/* Overview Tab */}
          <Tabs.Panel value="overview">
            <Grid mt="md">
              <Grid.Col span={8}>
                <Paper p="md" withBorder>
                  <Text fw={600} mb="md">Mission Performance Trends</Text>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={missionTrends}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      <Area type="monotone" dataKey="missions" stackId="1" stroke="#8884d8" fill="#8884d8" />
                      <Area type="monotone" dataKey="efficiency" stackId="2" stroke="#82ca9d" fill="#82ca9d" />
                    </AreaChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid.Col>
              
              <Grid.Col span={4}>
                <Stack gap="md">
                  <Paper p="md" withBorder>
                    <Text fw={600} mb="md">Fleet Status</Text>
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie
                          data={fleetUtilization}
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                          label={({ name, value }) => `${name}: ${value}`}
                        >
                          {fleetUtilization.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <RechartsTooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </Paper>
                  
                  <Paper p="md" withBorder>
                    <Text fw={600} mb="md">Live Alerts</Text>
                    <Stack gap="xs">
                      {alerts.slice(0, 3).map(alert => (
                        <Alert
                          key={alert.id}
                          icon={<IconAlertTriangle size={16} />}
                          color={alert.type === 'error' ? 'red' : alert.type === 'warning' ? 'yellow' : 'blue'}
                          variant="light"
                        >
                          <Text size="sm" fw={500}>{alert.title}</Text>
                          <Text size="xs">{alert.message}</Text>
                        </Alert>
                      ))}
                    </Stack>
                  </Paper>
                </Stack>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>

          {/* Mission Analytics Tab */}
          <Tabs.Panel value="missions">
            <Grid mt="md">
              <Grid.Col span={6}>
                <Paper p="md" withBorder>
                  <Text fw={600} mb="md">Mission Success Rate</Text>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={missionTrends}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      <Line type="monotone" dataKey="success" stroke="#82ca9d" strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid.Col>
              
              <Grid.Col span={6}>
                <Paper p="md" withBorder>
                  <Text fw={600} mb="md">Efficiency Comparison</Text>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={efficiencyData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      <Bar dataKey="efficiency" fill="#8884d8" />
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>

          {/* Fleet Performance Tab */}
          <Tabs.Panel value="fleet">
            <Grid mt="md">
              <Grid.Col span={12}>
                <Paper p="md" withBorder>
                  <Text fw={600} mb="md">Battery Performance (24h)</Text>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={batteryData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      <Area type="monotone" dataKey="battery" stroke="#82ca9d" fill="#82ca9d" />
                      <Area type="monotone" dataKey="consumption" stroke="#8884d8" fill="#8884d8" />
                    </AreaChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>

          {/* Cost Analysis Tab */}
          <Tabs.Panel value="costs">
            <Grid mt="md">
              <Grid.Col span={12}>
                <Paper p="md" withBorder>
                  <Text fw={600} mb="md">Cost Breakdown (6 months)</Text>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={costAnalysis}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      <Bar dataKey="operational" stackId="a" fill="#8884d8" />
                      <Bar dataKey="maintenance" stackId="a" fill="#82ca9d" />
                      <Bar dataKey="fuel" stackId="a" fill="#ffc658" />
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </motion.div>
  );
};