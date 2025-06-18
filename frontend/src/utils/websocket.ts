/**
 * WebSocket client utilities for real-time communication.
 * 
 * Provides Socket.IO client management for receiving live updates
 * about mission progress, drone status, and fleet operations.
 */

import { io, Socket } from 'socket.io-client';
import type {
  SocketMissionUpdate,
  SocketDroneUpdate,
  SocketFleetStatus,
  MissionLog,
  Mission,
  Drone
} from '@/types';

/**
 * WebSocket event types from server
 */
export interface ServerToClientEvents {
  connection_status: (data: { status: string; message: string; timestamp: string }) => void;
  mission_status: (data: { mission_id: number; status: string; progress_percentage: number; drone_id?: number; timestamp: string }) => void;
  mission_progress_update: (data: SocketMissionUpdate) => void;
  mission_log_entry: (data: { mission_id: number; log: MissionLog; timestamp: string }) => void;
  drone_status_update: (data: SocketDroneUpdate) => void;
  fleet_status: (data: SocketFleetStatus) => void;
  fleet_summary: (data: { fleet_stats: any; mission_stats: any; timestamp: string }) => void;
  error: (data: { message: string }) => void;
  mission_logs: (data: { mission_id: number; logs: MissionLog[]; timestamp: string }) => void;
}

/**
 * WebSocket event types to server
 */
export interface ClientToServerEvents {
  subscribe_mission_updates: (data: { mission_id: number }) => void;
  unsubscribe_mission_updates: (data: { mission_id: number }) => void;
  subscribe_fleet_updates: () => void;
  unsubscribe_fleet_updates: () => void;
  request_mission_logs: (data: { mission_id: number; limit?: number }) => void;
}

/**
 * WebSocket client class for managing Socket.IO connection
 */
export class WebSocketClient {
  private socket: Socket<ServerToClientEvents, ClientToServerEvents> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private isIntentionalDisconnect = false;

  /**
   * Initialize WebSocket connection
   */
  connect(): Promise<Socket<ServerToClientEvents, ClientToServerEvents>> {
    return new Promise((resolve, reject) => {
      const WEBSOCKET_URL = import.meta.env.VITE_WS_URL || 'http://localhost:5000';
      
      this.socket = io(WEBSOCKET_URL, {
        transports: ['websocket', 'polling'],
        timeout: 10000,
        forceNew: true,
      });

      // Connection successful
      this.socket.on('connect', () => {
        console.log('WebSocket connected:', this.socket?.id);
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        resolve(this.socket!);
      });

      // Connection error
      this.socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        this.handleReconnect();
        reject(error);
      });

      // Disconnection handling
      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        
        if (!this.isIntentionalDisconnect && reason !== 'io client disconnect') {
          this.handleReconnect();
        }
      });

      // Handle connection status updates
      this.socket.on('connection_status', (data) => {
        console.log('Connection status:', data);
      });

      // Handle errors from server
      this.socket.on('error', (data) => {
        console.error('WebSocket server error:', data.message);
      });
    });
  }

  /**
   * Handle reconnection logic
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    setTimeout(() => {
      if (this.socket && !this.socket.connected) {
        this.socket.connect();
      }
    }, this.reconnectDelay);

    // Exponential backoff
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max 30 seconds
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    if (this.socket) {
      this.isIntentionalDisconnect = true;
      this.socket.disconnect();
      this.socket = null;
      console.log('WebSocket disconnected intentionally');
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  /**
   * Get the socket instance
   */
  getSocket(): Socket<ServerToClientEvents, ClientToServerEvents> | null {
    return this.socket;
  }

  /**
   * Subscribe to mission updates
   */
  subscribeMissionUpdates(missionId: number): void {
    if (this.socket) {
      this.socket.emit('subscribe_mission_updates', { mission_id: missionId });
      console.log(`Subscribed to mission ${missionId} updates`);
    }
  }

  /**
   * Unsubscribe from mission updates
   */
  unsubscribeMissionUpdates(missionId: number): void {
    if (this.socket) {
      this.socket.emit('unsubscribe_mission_updates', { mission_id: missionId });
      console.log(`Unsubscribed from mission ${missionId} updates`);
    }
  }

  /**
   * Subscribe to fleet updates
   */
  subscribeFleetUpdates(): void {
    if (this.socket) {
      this.socket.emit('subscribe_fleet_updates');
      console.log('Subscribed to fleet updates');
    }
  }

  /**
   * Unsubscribe from fleet updates
   */
  unsubscribeFleetUpdates(): void {
    if (this.socket) {
      this.socket.emit('unsubscribe_fleet_updates');
      console.log('Unsubscribed from fleet updates');
    }
  }

  /**
   * Request mission logs
   */
  requestMissionLogs(missionId: number, limit?: number): void {
    if (this.socket) {
      this.socket.emit('request_mission_logs', { mission_id: missionId, limit });
    }
  }

  /**
   * Add event listener for mission status updates
   */
  onMissionStatus(callback: (data: { mission_id: number; status: string; progress_percentage: number; drone_id?: number; timestamp: string }) => void): void {
    this.socket?.on('mission_status', callback);
  }

  /**
   * Add event listener for mission progress updates
   */
  onMissionProgress(callback: (data: SocketMissionUpdate) => void): void {
    this.socket?.on('mission_progress_update', callback);
  }

  /**
   * Add event listener for mission log entries
   */
  onMissionLog(callback: (data: { mission_id: number; log: MissionLog; timestamp: string }) => void): void {
    this.socket?.on('mission_log_entry', callback);
  }

  /**
   * Add event listener for drone status updates
   */
  onDroneStatus(callback: (data: SocketDroneUpdate) => void): void {
    this.socket?.on('drone_status_update', callback);
  }

  /**
   * Add event listener for fleet status updates
   */
  onFleetStatus(callback: (data: SocketFleetStatus) => void): void {
    this.socket?.on('fleet_status', callback);
  }

  /**
   * Add event listener for fleet summary
   */
  onFleetSummary(callback: (data: { fleet_stats: any; mission_stats: any; timestamp: string }) => void): void {
    this.socket?.on('fleet_summary', callback);
  }

  /**
   * Add event listener for mission logs response
   */
  onMissionLogs(callback: (data: { mission_id: number; logs: MissionLog[]; timestamp: string }) => void): void {
    this.socket?.on('mission_logs', callback);
  }

  /**
   * Remove all event listeners
   */
  removeAllListeners(): void {
    this.socket?.removeAllListeners();
  }

  /**
   * Remove specific event listener
   */
  removeListener(event: keyof ServerToClientEvents, callback?: (...args: any[]) => void): void {
    if (callback) {
      this.socket?.off(event, callback);
    } else {
      this.socket?.removeAllListeners(event);
    }
  }
}

/**
 * Singleton WebSocket client instance
 */
export const webSocketClient = new WebSocketClient();

/**
 * Hook-like function to manage WebSocket connection lifecycle
 */
export const useWebSocket = () => {
  const connect = async () => {
    try {
      await webSocketClient.connect();
      return true;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      return false;
    }
  };

  const disconnect = () => {
    webSocketClient.disconnect();
  };

  const isConnected = () => {
    return webSocketClient.isConnected();
  };

  return {
    connect,
    disconnect,
    isConnected,
    client: webSocketClient
  };
};