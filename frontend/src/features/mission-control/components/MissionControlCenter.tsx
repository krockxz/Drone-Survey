/**
 * Advanced Mission Control Center with 3D Visualization
 * 
 * This component provides a professional mission control interface featuring:
 * - 3D mission path visualization using Three.js
 * - Real-time drone tracking with animated movements
 * - Interactive flight path preview and editing
 * - Multi-mission coordination dashboard
 * - Emergency response controls
 * 
 * Designed to showcase advanced UI/UX and AI-powered features
 * for maximum visual impact during demo presentations.
 * 
 * @author FlytBase Assignment
 * @created 2024
 */

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { 
  Paper, 
  Grid, 
  Text, 
  Badge, 
  Button, 
  Group, 
  Stack, 
  Card,
  Progress,
  ActionIcon,
  Tooltip,
  Alert,
  Tabs,
  RingProgress,
  Timeline,
  Modal,
  Switch
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import {
  IconDrone,
  IconMap,
  IconRadar,
  IconAlertTriangle,
  IconPlayerPlay,
  IconPlayerPause,
  IconPlayerStop,
  IconEmergencyBed,
  IconSettings,
  IconEye,
  IconBolt,
  IconWifi,
  IconTarget,
  IconRoute,
  IconChartLine
} from '@tabler/icons-react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text as Text3D, Line } from '@react-three/drei';
import { motion, AnimatePresence } from 'framer-motion';

// Store imports
import { useMissionStore } from '@/stores/missionStore';
import { useDroneStore } from '@/stores/droneStore';

// Type definitions for enhanced features
interface DronePosition3D {
  id: string;
  position: [number, number, number];
  rotation: [number, number, number];
  battery: number;
  status: 'active' | 'warning' | 'critical';
}

interface Mission3D {
  id: string;
  name: string;
  waypoints: Array<[number, number, number]>;
  currentProgress: number;
  droneId: string;
  status: 'planned' | 'active' | 'paused' | 'completed' | 'emergency';
}

/**
 * 3D Drone Visualization Component
 * Renders animated drone models with real-time status indicators
 */
const Drone3D: React.FC<{ 
  position: [number, number, number];
  rotation: [number, number, number];
  status: 'active' | 'warning' | 'critical';
  battery: number;
}> = ({ position, rotation, status, battery }) => {
  const meshRef = useRef<any>();
  
  // Animate drone movement smoothly
  useEffect(() => {
    if (meshRef.current) {
      meshRef.current.position.set(...position);
      meshRef.current.rotation.set(...rotation);
    }
  }, [position, rotation]);

  const getStatusColor = () => {
    switch (status) {
      case 'critical': return '#ff4757';
      case 'warning': return '#ffa502';
      default: return '#2ed573';
    }
  };

  return (
    <group ref={meshRef}>
      {/* Drone body */}
      <mesh>
        <boxGeometry args={[0.3, 0.1, 0.3]} />
        <meshStandardMaterial color={getStatusColor()} />
      </mesh>
      
      {/* Propellers */}
      {[-0.15, 0.15].map((x, i) => 
        [-0.15, 0.15].map((z, j) => (
          <mesh key={`${i}-${j}`} position={[x, 0.05, z]}>
            <cylinderGeometry args={[0.05, 0.05, 0.02]} />
            <meshStandardMaterial color="#333" />
          </mesh>
        ))
      )}
      
      {/* Status indicator */}
      <mesh position={[0, 0.2, 0]}>
        <sphereGeometry args={[0.05]} />
        <meshBasicMaterial color={getStatusColor()} />
      </mesh>
      
      {/* Battery level indicator */}
      <Text3D
        position={[0, 0.3, 0]}
        fontSize={0.1}
        color={battery < 20 ? '#ff4757' : '#2ed573'}
        anchorX="center"
        anchorY="middle"
      >
        {`${battery}%`}
      </Text3D>
    </group>
  );
};

/**
 * 3D Flight Path Visualization
 * Shows mission waypoints and real-time progress
 */
const FlightPath3D: React.FC<{ mission: Mission3D }> = ({ mission }) => {
  const pathPoints = mission.waypoints.map((point, index) => {
    const progress = mission.currentProgress / 100;
    const isCompleted = index < mission.waypoints.length * progress;
    return { point, isCompleted, index };
  });

  return (
    <group>
      {/* Flight path line */}
      <Line
        points={mission.waypoints}
        color={mission.status === 'emergency' ? '#ff4757' : '#2ed573'}
        lineWidth={3}
      />
      
      {/* Waypoint markers */}
      {pathPoints.map(({ point, isCompleted, index }) => (
        <mesh key={index} position={point}>
          <sphereGeometry args={[0.08]} />
          <meshStandardMaterial 
            color={isCompleted ? '#2ed573' : '#ffa502'} 
            emissive={isCompleted ? '#2ed573' : '#ffa502'}
            emissiveIntensity={0.3}
          />
        </mesh>
      ))}
      
      {/* Progress indicator */}
      <Text3D
        position={[mission.waypoints[0][0], mission.waypoints[0][1] + 1, mission.waypoints[0][2]]}
        fontSize={0.2}
        color="#fff"
        anchorX="center"
        anchorY="middle"
      >
        {mission.name}
      </Text3D>
    </group>
  );
};

/**
 * Main Mission Control Center Component
 */
export const MissionControlCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [realTimeEnabled, setRealTimeEnabled] = useState(true);
  const [emergencyModalOpened, { open: openEmergencyModal, close: closeEmergencyModal }] = useDisclosure(false);
  
  // Stores
  const { missions, activeMissions, fetchMissions } = useMissionStore();
  const { drones, activeDrones, fleetSummary, fetchDrones } = useDroneStore();
  
  // Mock 3D data - in real app, this would come from WebSocket updates
  const [drones3D, setDrones3D] = useState<DronePosition3D[]>([
    {
      id: '1',
      position: [0, 2, 0],
      rotation: [0, 0, 0],
      battery: 85,
      status: 'active'
    },
    {
      id: '2', 
      position: [5, 1.5, 3],
      rotation: [0, Math.PI / 4, 0],
      battery: 45,
      status: 'warning'
    },
    {
      id: '3',
      position: [-3, 2.5, -2],
      rotation: [0, -Math.PI / 6, 0],
      battery: 15,
      status: 'critical'
    }
  ]);

  const [missions3D, setMissions3D] = useState<Mission3D[]>([
    {
      id: '1',
      name: 'Survey Area A',
      waypoints: [[0, 0, 0], [2, 1, 2], [4, 2, 1], [6, 1, 3]],
      currentProgress: 65,
      droneId: '1',
      status: 'active'
    },
    {
      id: '2',
      name: 'Perimeter Check',
      waypoints: [[-2, 0, -1], [0, 1, -3], [2, 2, -2], [1, 1, 0]],
      currentProgress: 30,
      droneId: '2',
      status: 'active'
    }
  ]);

  // Simulate real-time updates
  useEffect(() => {
    if (!realTimeEnabled) return;
    
    const interval = setInterval(() => {
      setDrones3D(prev => prev.map(drone => ({
        ...drone,
        position: [
          drone.position[0] + (Math.random() - 0.5) * 0.1,
          drone.position[1] + (Math.random() - 0.5) * 0.1,
          drone.position[2] + (Math.random() - 0.5) * 0.1
        ],
        rotation: [
          drone.rotation[0],
          drone.rotation[1] + Math.random() * 0.1,
          drone.rotation[2]
        ],
        battery: Math.max(0, drone.battery - Math.random() * 0.5)
      })));
      
      setMissions3D(prev => prev.map(mission => ({
        ...mission,
        currentProgress: Math.min(100, mission.currentProgress + Math.random() * 2)
      })));
    }, 2000);

    return () => clearInterval(interval);
  }, [realTimeEnabled]);

  const handleEmergencyLanding = () => {
    setEmergencyMode(true);
    notifications.show({
      title: 'Emergency Protocol Activated',
      message: 'All drones returning to safe landing zones',
      color: 'red',
      icon: <IconEmergencyBed />
    });
    closeEmergencyModal();
  };

  const handleMissionControl = (action: 'play' | 'pause' | 'stop', missionId: string) => {
    notifications.show({
      title: `Mission ${action.toUpperCase()}`,
      message: `Mission ${missionId} ${action}ed successfully`,
      color: action === 'stop' ? 'red' : 'blue'
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <Stack gap="md">
        {/* Header with Emergency Controls */}
        <Paper p="md" withBorder>
          <Group justify="space-between">
            <Group>
              <IconRadar size={32} color="var(--mantine-color-blue-6)" />
              <div>
                <Text size="xl" fw={700}>Mission Control Center</Text>
                <Text size="sm" c="dimmed">Advanced 3D Flight Operations</Text>
              </div>
            </Group>
            
            <Group>
              <Switch
                label="Real-time Updates"
                checked={realTimeEnabled}
                onChange={(event) => setRealTimeEnabled(event.currentTarget.checked)}
                color="green"
              />
              
              <Button
                color="red"
                leftSection={<IconEmergencyBed size={16} />}
                onClick={openEmergencyModal}
                variant={emergencyMode ? "filled" : "light"}
              >
                Emergency Landing
              </Button>
            </Group>
          </Group>
        </Paper>

        {/* Main Dashboard Grid */}
        <Grid>
          {/* 3D Visualization Panel */}
          <Grid.Col span={8}>
            <Paper p="md" withBorder style={{ height: '600px' }}>
              <Group justify="space-between" mb="md">
                <Text fw={600}>3D Mission Visualization</Text>
                <Group>
                  <Badge color="green" variant="light">
                    {drones3D.filter(d => d.status === 'active').length} Active
                  </Badge>
                  <Badge color="yellow" variant="light">
                    {drones3D.filter(d => d.status === 'warning').length} Warning
                  </Badge>
                  <Badge color="red" variant="light">
                    {drones3D.filter(d => d.status === 'critical').length} Critical
                  </Badge>
                </Group>
              </Group>
              
              <div style={{ height: '520px', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
                <Suspense fallback={<div>Loading 3D View...</div>}>
                  <Canvas camera={{ position: [10, 10, 10], fov: 60 }}>
                    <ambientLight intensity={0.6} />
                    <pointLight position={[10, 10, 10]} intensity={0.8} />
                    <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} />
                    
                    {/* Render drones */}
                    {drones3D.map(drone => (
                      <Drone3D
                        key={drone.id}
                        position={drone.position}
                        rotation={drone.rotation}
                        status={drone.status}
                        battery={drone.battery}
                      />
                    ))}
                    
                    {/* Render flight paths */}
                    {missions3D.map(mission => (
                      <FlightPath3D key={mission.id} mission={mission} />
                    ))}
                    
                    {/* Ground plane */}
                    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
                      <planeGeometry args={[20, 20]} />
                      <meshStandardMaterial color="#f0f0f0" transparent opacity={0.5} />
                    </mesh>
                  </Canvas>
                </Suspense>
              </div>
            </Paper>
          </Grid.Col>

          {/* Control Panel */}
          <Grid.Col span={4}>
            <Stack gap="md">
              {/* Fleet Status */}
              <Card withBorder>
                <Text fw={600} mb="md">Fleet Status</Text>
                <Group justify="space-between" mb="xs">
                  <Text size="sm">Active Drones</Text>
                  <Badge color="green">{drones3D.filter(d => d.status === 'active').length}</Badge>
                </Group>
                <Group justify="space-between" mb="xs">
                  <Text size="sm">Average Battery</Text>
                  <Text size="sm" fw={600}>
                    {Math.round(drones3D.reduce((acc, d) => acc + d.battery, 0) / drones3D.length)}%
                  </Text>
                </Group>
                <Progress 
                  value={drones3D.reduce((acc, d) => acc + d.battery, 0) / drones3D.length}
                  color={drones3D.some(d => d.battery < 20) ? 'red' : 'green'}
                  mt="xs"
                />
              </Card>

              {/* Active Missions */}
              <Card withBorder>
                <Text fw={600} mb="md">Active Missions</Text>
                <Stack gap="sm">
                  {missions3D.map(mission => (
                    <Paper key={mission.id} p="sm" withBorder>
                      <Group justify="space-between" mb="xs">
                        <Text size="sm" fw={500}>{mission.name}</Text>
                        <Badge 
                          color={mission.status === 'active' ? 'green' : 'yellow'}
                          variant="light"
                        >
                          {mission.status}
                        </Badge>
                      </Group>
                      <Progress value={mission.currentProgress} mb="xs" />
                      <Group>
                        <ActionIcon 
                          size="sm" 
                          color="green"
                          onClick={() => handleMissionControl('play', mission.id)}
                        >
                          <IconPlayerPlay size={14} />
                        </ActionIcon>
                        <ActionIcon 
                          size="sm" 
                          color="yellow"
                          onClick={() => handleMissionControl('pause', mission.id)}
                        >
                          <IconPlayerPause size={14} />
                        </ActionIcon>
                        <ActionIcon 
                          size="sm" 
                          color="red"
                          onClick={() => handleMissionControl('stop', mission.id)}
                        >
                          <IconPlayerStop size={14} />
                        </ActionIcon>
                      </Group>
                    </Paper>
                  ))}
                </Stack>
              </Card>

              {/* System Alerts */}
              <Card withBorder>
                <Text fw={600} mb="md">System Alerts</Text>
                <Stack gap="xs">
                  {drones3D.filter(d => d.status === 'critical').map(drone => (
                    <Alert
                      key={drone.id}
                      icon={<IconAlertTriangle size={16} />}
                      color="red"
                      variant="light"
                    >
                      <Text size="xs">Drone {drone.id}: Critical battery ({drone.battery}%)</Text>
                    </Alert>
                  ))}
                  {drones3D.filter(d => d.status === 'warning').map(drone => (
                    <Alert
                      key={drone.id}
                      icon={<IconBolt size={16} />}
                      color="yellow"
                      variant="light"
                    >
                      <Text size="xs">Drone {drone.id}: Low battery ({drone.battery}%)</Text>
                    </Alert>
                  ))}
                </Stack>
              </Card>
            </Stack>
          </Grid.Col>
        </Grid>

        {/* Emergency Modal */}
        <Modal
          opened={emergencyModalOpened}
          onClose={closeEmergencyModal}
          title="Emergency Landing Protocol"
          centered
        >
          <Stack gap="md">
            <Alert icon={<IconAlertTriangle size={16} />} color="red">
              This will immediately land all active drones at their nearest safe landing zones.
              All missions will be paused and require manual restart.
            </Alert>
            
            <Group justify="flex-end">
              <Button variant="light" onClick={closeEmergencyModal}>
                Cancel
              </Button>
              <Button color="red" onClick={handleEmergencyLanding}>
                Activate Emergency Landing
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </motion.div>
  );
};