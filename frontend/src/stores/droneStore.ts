/**
 * Zustand store for drone fleet management.
 * 
 * Manages drone data, real-time updates, and fleet operations
 * with integration to WebSocket events for live status updates.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Drone, DroneStatus, DroneLocation, ApiError } from '@/types';
import { droneApi } from '@/utils/api';
import { webSocketClient } from '@/utils/websocket';

interface DroneStore {
  // State
  drones: Drone[];
  selectedDrone: Drone | null;
  loading: boolean;
  error: string | null;
  filters: {
    status?: DroneStatus[];
    availableOnly: boolean;
    searchQuery: string;
  };
  lastUpdated: string | null;

  // Actions
  fetchDrones: () => Promise<void>;
  fetchDroneById: (id: number) => Promise<void>;
  createDrone: (data: { name: string; model: string; serial_number?: string }) => Promise<void>;
  updateDrone: (id: number, data: Partial<Drone>) => Promise<void>;
  updateDroneLocation: (id: number, location: { latitude: number; longitude: number; altitude_m?: number }) => Promise<void>;
  updateDroneBattery: (id: number, batteryPercentage: number) => Promise<void>;
  setSelectedDrone: (drone: Drone | null) => void;
  setFilters: (filters: Partial<DroneStore['filters']>) => void;
  clearError: () => void;

  // Real-time updates
  handleDroneStatusUpdate: (update: { drone_id: number; status?: DroneStatus; battery_percentage?: number; location?: DroneLocation }) => void;
  subscribeToFleetUpdates: () => void;
  unsubscribeFromFleetUpdates: () => void;

  // Computed getters
  getAvailableDrones: () => Drone[];
  getActiveDrones: () => Drone[];
  getDronesByStatus: (status: DroneStatus) => Drone[];
  getFilteredDrones: () => Drone[];
  getFleetStats: () => {
    total: number;
    available: number;
    active: number;
    maintenance: number;
    averageBattery: number;
    lowBatteryCount: number;
  };
}

export const useDroneStore = create<DroneStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      drones: [],
      selectedDrone: null,
      loading: false,
      error: null,
      filters: {
        availableOnly: false,
        searchQuery: '',
      },
      lastUpdated: null,

      // Actions
      fetchDrones: async () => {
        set({ loading: true, error: null });
        try {
          const { filters } = get();
          const params: any = {};
          
          if (filters.status && filters.status.length > 0) {
            params.status = filters.status[0]; // API supports single status filter
          }
          
          if (filters.availableOnly) {
            params.available_only = true;
          }

          const response = await droneApi.getAll(params);
          set({
            drones: response.drones,
            loading: false,
            lastUpdated: response.timestamp,
          });
        } catch (error: any) {
          set({
            loading: false,
            error: error.message || 'Failed to fetch drones',
          });
        }
      },

      fetchDroneById: async (id: number) => {
        set({ loading: true, error: null });
        try {
          const drone = await droneApi.getById(id);
          set({ selectedDrone: drone, loading: false });
        } catch (error: any) {
          set({
            loading: false,
            error: error.message || 'Failed to fetch drone',
          });
        }
      },

      createDrone: async (data) => {
        set({ loading: true, error: null });
        try {
          const newDrone = await droneApi.create(data);
          set((state) => ({
            drones: [...state.drones, newDrone],
            loading: false,
          }));
        } catch (error: any) {
          set({
            loading: false,
            error: error.message || 'Failed to create drone',
          });
          throw error;
        }
      },

      updateDrone: async (id, data) => {
        set({ loading: true, error: null });
        try {
          const updatedDrone = await droneApi.update(id, data);
          set((state) => ({
            drones: state.drones.map((drone) =>
              drone.id === id ? updatedDrone : drone
            ),
            selectedDrone: state.selectedDrone?.id === id ? updatedDrone : state.selectedDrone,
            loading: false,
          }));
        } catch (error: any) {
          set({
            loading: false,
            error: error.message || 'Failed to update drone',
          });
          throw error;
        }
      },

      updateDroneLocation: async (id, location) => {
        try {
          await droneApi.updateLocation(id, location);
          // Update will be reflected via WebSocket, no need to update state here
        } catch (error: any) {
          set({ error: error.message || 'Failed to update drone location' });
          throw error;
        }
      },

      updateDroneBattery: async (id, batteryPercentage) => {
        try {
          const response = await droneApi.updateBattery(id, batteryPercentage);
          
          // Update local state immediately
          set((state) => ({
            drones: state.drones.map((drone) =>
              drone.id === id
                ? { ...drone, battery_percentage: response.battery_percentage, status: response.status as DroneStatus }
                : drone
            ),
            selectedDrone: state.selectedDrone?.id === id
              ? { ...state.selectedDrone, battery_percentage: response.battery_percentage, status: response.status as DroneStatus }
              : state.selectedDrone,
          }));
        } catch (error: any) {
          set({ error: error.message || 'Failed to update drone battery' });
          throw error;
        }
      },

      setSelectedDrone: (drone) => {
        set({ selectedDrone: drone });
      },

      setFilters: (newFilters) => {
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
        }));
      },

      clearError: () => {
        set({ error: null });
      },

      // Real-time updates
      handleDroneStatusUpdate: (update) => {
        set((state) => ({
          drones: state.drones.map((drone) => {
            if (drone.id === update.drone_id) {
              const updatedDrone = { ...drone };
              
              if (update.status) {
                updatedDrone.status = update.status;
              }
              
              if (update.battery_percentage !== undefined) {
                updatedDrone.battery_percentage = update.battery_percentage;
              }
              
              if (update.location) {
                updatedDrone.current_location = {
                  lat: update.location.lat,
                  lng: update.location.lng,
                  altitude_m: update.location.altitude_m,
                };
                updatedDrone.last_seen = new Date().toISOString();
              }
              
              return updatedDrone;
            }
            return drone;
          }),
          selectedDrone: state.selectedDrone?.id === update.drone_id
            ? (() => {
                const updated = { ...state.selectedDrone };
                if (update.status) updated.status = update.status;
                if (update.battery_percentage !== undefined) updated.battery_percentage = update.battery_percentage;
                if (update.location) {
                  updated.current_location = {
                    lat: update.location.lat,
                    lng: update.location.lng,
                    altitude_m: update.location.altitude_m,
                  };
                  updated.last_seen = new Date().toISOString();
                }
                return updated;
              })()
            : state.selectedDrone,
        }));
      },

      subscribeToFleetUpdates: () => {
        webSocketClient.subscribeFleetUpdates();
        
        // Set up event listeners
        webSocketClient.onDroneStatus((data) => {
          get().handleDroneStatusUpdate(data);
        });

        webSocketClient.onFleetStatus((data) => {
          set({ drones: data.drones, lastUpdated: data.timestamp });
        });
      },

      unsubscribeFromFleetUpdates: () => {
        webSocketClient.unsubscribeFleetUpdates();
        webSocketClient.removeListener('drone_status_update');
        webSocketClient.removeListener('fleet_status');
      },

      // Computed getters
      getAvailableDrones: () => {
        return get().drones.filter((drone) => drone.status === 'available');
      },

      getActiveDrones: () => {
        return get().drones.filter((drone) => drone.status === 'in-mission');
      },

      getDronesByStatus: (status) => {
        return get().drones.filter((drone) => drone.status === status);
      },

      getFilteredDrones: () => {
        const { drones, filters } = get();
        let filtered = [...drones];

        // Filter by status
        if (filters.status && filters.status.length > 0) {
          filtered = filtered.filter((drone) => filters.status!.includes(drone.status));
        }

        // Filter by availability
        if (filters.availableOnly) {
          filtered = filtered.filter((drone) => drone.status === 'available');
        }

        // Filter by search query
        if (filters.searchQuery.trim()) {
          const query = filters.searchQuery.toLowerCase().trim();
          filtered = filtered.filter((drone) =>
            drone.name.toLowerCase().includes(query) ||
            drone.model.toLowerCase().includes(query) ||
            (drone.serial_number && drone.serial_number.toLowerCase().includes(query))
          );
        }

        return filtered;
      },

      getFleetStats: () => {
        const { drones } = get();
        const total = drones.length;
        const available = drones.filter((d) => d.status === 'available').length;
        const active = drones.filter((d) => d.status === 'in-mission').length;
        const maintenance = drones.filter((d) => d.status === 'maintenance').length;
        
        const totalBattery = drones.reduce((sum, drone) => sum + drone.battery_percentage, 0);
        const averageBattery = total > 0 ? totalBattery / total : 0;
        
        const lowBatteryCount = drones.filter((d) => d.battery_percentage < 20).length;

        return {
          total,
          available,
          active,
          maintenance,
          averageBattery: Math.round(averageBattery * 10) / 10,
          lowBatteryCount,
        };
      },
    }),
    {
      name: 'drone-store',
    }
  )
);