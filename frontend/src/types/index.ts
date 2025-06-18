/**
 * Type definitions for the Drone Survey Management System frontend.
 * 
 * These types correspond to the backend API models and ensure
 * type safety across the frontend application.
 */

// Drone Types
export type DroneStatus = 'available' | 'in-mission' | 'maintenance' | 'charging' | 'offline';

export interface DroneLocation {
  lat: number;
  lng: number;
  altitude_m?: number;
}

export interface Drone {
  id: number;
  name: string;
  model: string;
  serial_number?: string;
  status: DroneStatus;
  battery_percentage: number;
  current_location?: DroneLocation;
  last_seen?: string;
  flight_hours_total: number;
  missions_completed: number;
  created_at: string;
  updated_at: string;
}

// Mission Types
export type MissionStatus = 'planned' | 'in-progress' | 'paused' | 'completed' | 'aborted' | 'failed';
export type SurveyPattern = 'crosshatch' | 'perimeter' | 'grid' | 'custom';

export interface GeoJSONCoordinates {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface Waypoint {
  id: number;
  mission_id: number;
  latitude: number;
  longitude: number;
  altitude_m: number;
  order: number;
  completed: boolean;
  completed_at?: string;
}

export interface Mission {
  id: number;
  name: string;
  description?: string;
  status: MissionStatus;
  drone_id?: number;
  survey_area_geojson: GeoJSONCoordinates;
  altitude_m: number;
  overlap_percentage: number;
  survey_pattern: SurveyPattern;
  estimated_duration_minutes?: number;
  actual_duration_minutes?: number;
  progress_percentage: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  waypoint_count?: number;
  waypoints?: Waypoint[];
  drone?: Pick<Drone, 'id' | 'name' | 'status'>;
}

// Mission Log Types
export type LogType = 'info' | 'warning' | 'error' | 'status_change' | 'waypoint_reached' | 'system_alert';

export interface MissionLog {
  id: number;
  mission_id: number;
  timestamp: string;
  log_type: LogType;
  message: string;
  details?: string;
  drone_id?: number;
}

// API Response Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// Mission Planning Types
export interface MissionPlanningData {
  name: string;
  description?: string;
  survey_area_geojson: GeoJSONCoordinates;
  altitude_m: number;
  overlap_percentage: number;
  survey_pattern: SurveyPattern;
  auto_assign_drone?: boolean;
}

export interface WaypointGenerationRequest {
  survey_area_geojson: GeoJSONCoordinates;
  altitude_m: number;
  overlap_percentage: number;
  survey_pattern: SurveyPattern;
}

export interface WaypointGenerationResponse {
  waypoints: Omit<Waypoint, 'id' | 'mission_id' | 'completed' | 'completed_at'>[];
  waypoint_count: number;
  estimated_duration_minutes: number;
  cost_estimate: {
    total_cost: number;
    duration_minutes: number;
    breakdown: Record<string, number>;
  };
  generated_at: string;
}

// Analytics Types
export interface FleetOverview {
  fleet: {
    total_drones: number;
    available: number;
    active: number;
    maintenance: number;
    average_battery: number;
  };
  missions: {
    total_missions: number;
    completed: number;
    active: number;
    planned: number;
    success_rate: number;
  };
  recent_activity: {
    missions_last_7_days: number;
    flight_hours_last_7_days: number;
  };
  generated_at: string;
}

export interface MissionAnalytics {
  date_range: {
    start_date: string;
    end_date: string;
  };
  status_breakdown: Record<MissionStatus, number>;
  efficiency_metrics: {
    total_completed: number;
    total_flight_hours: number;
    average_flight_time_minutes: number;
    missions_per_day: number;
  };
  survey_patterns: Record<SurveyPattern, number>;
  time_series: Array<{
    date: string;
    count: number;
  }>;
  generated_at: string;
}

// WebSocket Event Types
export interface SocketMissionUpdate {
  mission_id: number;
  timestamp: string;
  status?: MissionStatus;
  progress_percentage?: number;
  log?: MissionLog;
}

export interface SocketDroneUpdate {
  drone_id: number;
  timestamp: string;
  status?: DroneStatus;
  battery_percentage?: number;
  location?: DroneLocation;
}

export interface SocketFleetStatus {
  drones: Drone[];
  timestamp: string;
}

// UI State Types
export interface MapViewState {
  center: [number, number];
  zoom: number;
  selectedMission?: number;
  selectedDrone?: number;
  showWaypoints: boolean;
  showFleetPositions: boolean;
}

export interface FilterState {
  droneStatus?: DroneStatus[];
  missionStatus?: MissionStatus[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  searchQuery?: string;
}

// Form Types
export interface DroneFormData {
  name: string;
  model: string;
  serial_number?: string;
}

export interface MissionControlAction {
  type: 'start' | 'pause' | 'resume' | 'abort';
  reason?: string;
}

// Error Types
export interface ApiError {
  message: string;
  status?: number;
  details?: Record<string, unknown>;
}

// User Interface Types
export type UserRole = 'survey_planner' | 'operations_manager' | 'data_analyst';

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  defaultMapView: MapViewState;
  notifications: {
    lowBattery: boolean;
    missionComplete: boolean;
    emergencyAlerts: boolean;
  };
}

// Chart/Visualization Types
export interface ChartDataPoint {
  x: string | number;
  y: number;
  label?: string;
  color?: string;
}

export interface TimeSeriesData {
  date: string;
  value: number;
  category?: string;
}

export interface MetricCard {
  title: string;
  value: number | string;
  change?: number;
  trend?: 'up' | 'down' | 'stable';
  format?: 'number' | 'percentage' | 'currency' | 'duration';
}