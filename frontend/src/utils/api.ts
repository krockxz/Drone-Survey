/**
 * API client utilities for the Drone Survey Management System.
 * 
 * Provides centralized HTTP client configuration and request functions
 * for communicating with the Flask backend API.
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import type {
  Drone,
  Mission,
  MissionLog,
  MissionPlanningData,
  WaypointGenerationRequest,
  WaypointGenerationResponse,
  FleetOverview,
  MissionAnalytics,
  ApiResponse,
  PaginatedResponse,
  DroneFormData,
  MissionControlAction
} from '@/types';

/**
 * Base API configuration
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Create configured axios instance
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000, // 30 seconds
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor for logging and auth
  client.interceptors.request.use(
    (config) => {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
      return config;
    },
    (error) => {
      console.error('API Request Error:', error);
      return Promise.reject(error);
    }
  );

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      console.log(`API Response: ${response.status} ${response.config.url}`);
      return response;
    },
    (error: AxiosError) => {
      console.error('API Response Error:', error.response?.status, error.message);
      
      // Handle common error cases
      if (error.response?.status === 401) {
        // Handle unauthorized access
        console.warn('Unauthorized access - consider implementing auth redirect');
      } else if (error.response?.status >= 500) {
        // Handle server errors
        console.error('Server error - consider showing user notification');
      }
      
      return Promise.reject(error);
    }
  );

  return client;
};

export const apiClient = createApiClient();

/**
 * Generic API request wrapper with error handling
 */
const apiRequest = async <T>(
  request: () => Promise<AxiosResponse<T>>
): Promise<T> => {
  try {
    const response = await request();
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const apiError = {
        message: error.response?.data?.error || error.message || 'Unknown API error',
        status: error.response?.status,
        details: error.response?.data
      };
      throw apiError;
    }
    throw new Error('Unexpected error occurred');
  }
};

/**
 * Drone API functions
 */
export const droneApi = {
  /**
   * Get all drones with optional filtering
   */
  getAll: async (params?: {
    status?: string;
    available_only?: boolean;
  }): Promise<{ drones: Drone[]; total_count: number; timestamp: string }> => {
    return apiRequest(() => apiClient.get('/drones', { params }));
  },

  /**
   * Get specific drone by ID
   */
  getById: async (id: number): Promise<Drone> => {
    return apiRequest(() => apiClient.get(`/drones/${id}`));
  },

  /**
   * Create new drone
   */
  create: async (data: DroneFormData): Promise<Drone> => {
    return apiRequest(() => apiClient.post('/drones', data));
  },

  /**
   * Update drone information
   */
  update: async (id: number, data: Partial<DroneFormData & {
    status?: string;
    battery_percentage?: number;
    current_location_lat?: number;
    current_location_lng?: number;
    current_altitude_m?: number;
  }>): Promise<Drone> => {
    return apiRequest(() => apiClient.put(`/drones/${id}`, data));
  },

  /**
   * Update drone location
   */
  updateLocation: async (id: number, location: {
    latitude: number;
    longitude: number;
    altitude_m?: number;
  }): Promise<{ message: string; location: any }> => {
    return apiRequest(() => apiClient.put(`/drones/${id}/location`, location));
  },

  /**
   * Update drone battery level
   */
  updateBattery: async (id: number, battery_percentage: number): Promise<{
    message: string;
    battery_percentage: number;
    status: string;
    status_changed: boolean;
  }> => {
    return apiRequest(() => apiClient.put(`/drones/${id}/battery`, { battery_percentage }));
  }
};

/**
 * Mission API functions
 */
export const missionApi = {
  /**
   * Get all missions with pagination and filtering
   */
  getAll: async (params?: {
    status?: string;
    drone_id?: number;
    page?: number;
    per_page?: number;
  }): Promise<{
    missions: Mission[];
    pagination: any;
    timestamp: string;
  }> => {
    return apiRequest(() => apiClient.get('/missions', { params }));
  },

  /**
   * Get specific mission by ID
   */
  getById: async (id: number): Promise<Mission> => {
    return apiRequest(() => apiClient.get(`/missions/${id}`));
  },

  /**
   * Create new mission
   */
  create: async (data: MissionPlanningData): Promise<Mission> => {
    return apiRequest(() => apiClient.post('/missions', data));
  },

  /**
   * Generate waypoints for mission planning
   */
  generateWaypoints: async (data: WaypointGenerationRequest): Promise<WaypointGenerationResponse> => {
    return apiRequest(() => apiClient.post('/missions/generate-waypoints', data));
  },

  /**
   * Start mission
   */
  start: async (id: number): Promise<{ message: string; mission: Mission; drone: Drone }> => {
    return apiRequest(() => apiClient.post(`/missions/${id}/start`));
  },

  /**
   * Pause mission
   */
  pause: async (id: number): Promise<{ message: string; mission: Mission }> => {
    return apiRequest(() => apiClient.post(`/missions/${id}/pause`));
  },

  /**
   * Resume mission
   */
  resume: async (id: number): Promise<{ message: string; mission: Mission }> => {
    return apiRequest(() => apiClient.post(`/missions/${id}/resume`));
  },

  /**
   * Abort mission
   */
  abort: async (id: number, reason?: string): Promise<{ 
    message: string; 
    mission: Mission; 
    reason: string 
  }> => {
    return apiRequest(() => apiClient.post(`/missions/${id}/abort`, { reason }));
  },

  /**
   * Update mission progress
   */
  updateProgress: async (id: number, data: {
    progress_percentage?: number;
    current_waypoint_id?: number;
    completed_waypoint_ids?: number[];
  }): Promise<{ message: string; mission: Mission }> => {
    return apiRequest(() => apiClient.put(`/missions/${id}/progress`, data));
  },

  /**
   * Get mission logs
   */
  getLogs: async (id: number, params?: {
    page?: number;
    per_page?: number;
    log_type?: string;
  }): Promise<{
    logs: MissionLog[];
    pagination: any;
  }> => {
    return apiRequest(() => apiClient.get(`/missions/${id}/logs`, { params }));
  },

  /**
   * Delete mission
   */
  delete: async (id: number): Promise<{ message: string }> => {
    return apiRequest(() => apiClient.delete(`/missions/${id}`));
  }
};

/**
 * Reports/Analytics API functions
 */
export const reportsApi = {
  /**
   * Get system overview
   */
  getOverview: async (): Promise<FleetOverview> => {
    return apiRequest(() => apiClient.get('/reports/overview'));
  },

  /**
   * Get mission analytics
   */
  getMissionAnalytics: async (params?: {
    start_date?: string;
    end_date?: string;
    groupby?: 'day' | 'week' | 'month';
  }): Promise<MissionAnalytics> => {
    return apiRequest(() => apiClient.get('/reports/missions', { params }));
  },

  /**
   * Get drone analytics
   */
  getDroneAnalytics: async (): Promise<{
    fleet_status: Record<string, number>;
    battery_stats: any;
    flight_hours: any;
    top_performers: any[];
    utilization_details: any[];
    low_battery_alerts: any[];
    generated_at: string;
  }> => {
    return apiRequest(() => apiClient.get('/reports/drones'));
  },

  /**
   * Get operational metrics
   */
  getOperationalMetrics: async (params?: {
    period?: 'week' | 'month' | 'quarter';
  }): Promise<{
    analysis_period: any;
    mission_metrics: any;
    fleet_metrics: any;
    safety_metrics: any;
    recommendations: string[];
    generated_at: string;
  }> => {
    return apiRequest(() => apiClient.get('/reports/operational', { params }));
  },

  /**
   * Export mission data
   */
  exportData: async (params?: {
    format?: 'json' | 'csv';
    start_date?: string;
    end_date?: string;
    status?: string;
  }): Promise<any> => {
    return apiRequest(() => apiClient.get('/reports/export', { params }));
  }
};

/**
 * Health check
 */
export const healthApi = {
  check: async (): Promise<{ status: string; service: string }> => {
    return apiRequest(() => apiClient.get('/health'));
  }
};