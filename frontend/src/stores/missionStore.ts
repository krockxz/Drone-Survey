/**
 * Zustand store for mission management.
 * 
 * Manages mission data, real-time progress updates, and mission operations
 * with integration to WebSocket events for live mission monitoring.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Mission, MissionStatus, MissionLog, Waypoint, MissionPlanningData } from '@/types';
import { missionApi } from '@/utils/api';
import { webSocketClient } from '@/utils/websocket';

interface MissionStore {
  // State
  missions: Mission[];
  selectedMission: Mission | null;
  activeMissions: Mission[];
  missionLogs: Record<number, MissionLog[]>;
  loading: boolean;
  error: string | null;
  filters: {
    status?: MissionStatus[];
    droneId?: number;
    searchQuery: string;
  };

  // Actions
  fetchMissions: () => Promise<void>;
  fetchMissionById: (id: number) => Promise<void>;
  createMission: (data: MissionPlanningData) => Promise<Mission>;
  startMission: (id: number) => Promise<void>;
  pauseMission: (id: number) => Promise<void>;
  resumeMission: (id: number) => Promise<void>;
  abortMission: (id: number, reason?: string) => Promise<void>;
  setSelectedMission: (mission: Mission | null) => void;
  setFilters: (filters: Partial<MissionStore['filters']>) => void;
  clearError: () => void;

  // Real-time updates
  handleMissionUpdate: (update: { mission_id: number; status?: MissionStatus; progress_percentage?: number }) => void;
  handleMissionLog: (data: { mission_id: number; log: MissionLog }) => void;
  subscribeMissionUpdates: (missionId: number) => void;
  unsubscribeMissionUpdates: (missionId: number) => void;

  // Computed getters
  getActiveMissions: () => Mission[];
  getCompletedMissions: () => Mission[];
  getMissionsByStatus: (status: MissionStatus) => Mission[];
  getFilteredMissions: () => Mission[];
}

export const useMissionStore = create<MissionStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      missions: [],
      selectedMission: null,
      activeMissions: [],
      missionLogs: {},
      loading: false,
      error: null,
      filters: {
        searchQuery: '',
      },

      // Actions
      fetchMissions: async () => {
        set({ loading: true, error: null });
        try {
          const response = await missionApi.getAll();
          set({
            missions: response.missions,
            activeMissions: response.missions.filter(m => m.status === 'in-progress'),
            loading: false,
          });
        } catch (error: any) {
          set({
            loading: false,
            error: error.message || 'Failed to fetch missions',
          });
        }
      },

      fetchMissionById: async (id: number) => {
        set({ loading: true, error: null });
        try {
          const mission = await missionApi.getById(id);
          set({ selectedMission: mission, loading: false });
        } catch (error: any) {
          set({
            loading: false,
            error: error.message || 'Failed to fetch mission',
          });
        }
      },

      createMission: async (data: MissionPlanningData) => {
        set({ loading: true, error: null });
        try {
          const newMission = await missionApi.create(data);
          set((state) => ({
            missions: [...state.missions, newMission],
            loading: false,
          }));
          return newMission;
        } catch (error: any) {
          set({
            loading: false,
            error: error.message || 'Failed to create mission',
          });
          throw error;
        }
      },

      startMission: async (id: number) => {
        try {
          await missionApi.start(id);
          // Mission update will come via WebSocket
        } catch (error: any) {
          set({ error: error.message || 'Failed to start mission' });
          throw error;
        }
      },

      pauseMission: async (id: number) => {
        try {
          await missionApi.pause(id);
          // Mission update will come via WebSocket
        } catch (error: any) {
          set({ error: error.message || 'Failed to pause mission' });
          throw error;
        }
      },

      resumeMission: async (id: number) => {
        try {
          await missionApi.resume(id);
          // Mission update will come via WebSocket
        } catch (error: any) {
          set({ error: error.message || 'Failed to resume mission' });
          throw error;
        }
      },

      abortMission: async (id: number, reason?: string) => {
        try {
          await missionApi.abort(id, reason);
          // Mission update will come via WebSocket
        } catch (error: any) {
          set({ error: error.message || 'Failed to abort mission' });
          throw error;
        }
      },

      setSelectedMission: (mission) => {
        set({ selectedMission: mission });
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
      handleMissionUpdate: (update) => {
        set((state) => ({
          missions: state.missions.map((mission) =>
            mission.id === update.mission_id
              ? {
                  ...mission,
                  status: update.status || mission.status,
                  progress_percentage: update.progress_percentage ?? mission.progress_percentage,
                }
              : mission
          ),
          selectedMission: state.selectedMission?.id === update.mission_id
            ? {
                ...state.selectedMission,
                status: update.status || state.selectedMission.status,
                progress_percentage: update.progress_percentage ?? state.selectedMission.progress_percentage,
              }
            : state.selectedMission,
          activeMissions: state.missions
            .map((mission) =>
              mission.id === update.mission_id
                ? {
                    ...mission,
                    status: update.status || mission.status,
                    progress_percentage: update.progress_percentage ?? mission.progress_percentage,
                  }
                : mission
            )
            .filter((m) => m.status === 'in-progress'),
        }));
      },

      handleMissionLog: (data) => {
        set((state) => ({
          missionLogs: {
            ...state.missionLogs,
            [data.mission_id]: [
              data.log,
              ...(state.missionLogs[data.mission_id] || []),
            ].slice(0, 100), // Keep only last 100 logs
          },
        }));
      },

      subscribeMissionUpdates: (missionId) => {
        webSocketClient.subscribeMissionUpdates(missionId);
        
        webSocketClient.onMissionProgress((data) => {
          if (data.mission_id === missionId) {
            get().handleMissionUpdate(data);
          }
        });

        webSocketClient.onMissionLog((data) => {
          if (data.mission_id === missionId) {
            get().handleMissionLog(data);
          }
        });
      },

      unsubscribeMissionUpdates: (missionId) => {
        webSocketClient.unsubscribeMissionUpdates(missionId);
      },

      // Computed getters
      getActiveMissions: () => {
        return get().missions.filter((mission) => mission.status === 'in-progress');
      },

      getCompletedMissions: () => {
        return get().missions.filter((mission) => mission.status === 'completed');
      },

      getMissionsByStatus: (status) => {
        return get().missions.filter((mission) => mission.status === status);
      },

      getFilteredMissions: () => {
        const { missions, filters } = get();
        let filtered = [...missions];

        // Filter by status
        if (filters.status && filters.status.length > 0) {
          filtered = filtered.filter((mission) => filters.status!.includes(mission.status));
        }

        // Filter by drone
        if (filters.droneId) {
          filtered = filtered.filter((mission) => mission.drone_id === filters.droneId);
        }

        // Filter by search query
        if (filters.searchQuery.trim()) {
          const query = filters.searchQuery.toLowerCase().trim();
          filtered = filtered.filter((mission) =>
            mission.name.toLowerCase().includes(query) ||
            (mission.description && mission.description.toLowerCase().includes(query))
          );
        }

        return filtered;
      },
    }),
    {
      name: 'mission-store',
    }
  )
);