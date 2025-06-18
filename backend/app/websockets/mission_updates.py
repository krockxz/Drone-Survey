"""
WebSocket handlers for real-time mission and drone updates.

This module provides WebSocket communication for the Drone Survey Management System,
enabling real-time updates for mission progress, drone status, fleet monitoring,
and emergency alerts.

Author: FlytBase Assignment
Created: 2024
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
import json

from flask import request, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from sqlalchemy.exc import SQLAlchemyError

from app.models import db, Drone, Mission, MissionStatus, DroneStatus


class WebSocketManager:
    """Manages WebSocket connections and real-time event broadcasting."""
    
    def __init__(self, socketio: SocketIO):
        """Initialize WebSocket manager with SocketIO instance.
        
        Args:
            socketio: Flask-SocketIO instance
        """
        self.socketio = socketio
        self.connected_clients = {}  # Track connected clients
        
        # Register event handlers
        self.register_handlers()
    
    def register_handlers(self) -> None:
        """Register all WebSocket event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            client_id = request.sid
            self.connected_clients[client_id] = {
                'connected_at': datetime.now(timezone.utc),
                'subscriptions': []
            }
            
            current_app.logger.info(f"🔌 Client connected: {client_id}")
            
            # Send initial fleet summary
            try:
                fleet_summary = self.get_fleet_summary()
                emit('fleet_summary', fleet_summary)
                
                active_missions = self.get_active_missions_summary()
                emit('active_missions_update', active_missions)
                
            except Exception as e:
                current_app.logger.error(f"Error sending initial data: {e}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            client_id = request.sid
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            
            current_app.logger.info(f"🔌 Client disconnected: {client_id}")
        
        @self.socketio.on('subscribe_to_mission')
        def handle_mission_subscription(data):
            """Handle subscription to specific mission updates.
            
            Args:
                data: Dict containing mission_id
            """
            try:
                mission_id = data.get('mission_id')
                if not mission_id:
                    emit('error', {'message': 'Mission ID required'})
                    return
                
                room = f"mission_{mission_id}"
                join_room(room)
                
                client_id = request.sid
                if client_id in self.connected_clients:
                    self.connected_clients[client_id]['subscriptions'].append(room)
                
                current_app.logger.info(f"📡 Client {client_id} subscribed to mission {mission_id}")
                
                # Send current mission status
                mission_status = self.get_mission_status(mission_id)
                if mission_status:
                    emit('mission_status_update', mission_status)
                
            except Exception as e:
                current_app.logger.error(f"Error subscribing to mission: {e}")
                emit('error', {'message': 'Subscription failed'})
        
        @self.socketio.on('unsubscribe_from_mission')
        def handle_mission_unsubscription(data):
            """Handle unsubscription from mission updates.
            
            Args:
                data: Dict containing mission_id
            """
            try:
                mission_id = data.get('mission_id')
                if not mission_id:
                    return
                
                room = f"mission_{mission_id}"
                leave_room(room)
                
                client_id = request.sid
                if client_id in self.connected_clients:
                    subscriptions = self.connected_clients[client_id]['subscriptions']
                    if room in subscriptions:
                        subscriptions.remove(room)
                
                current_app.logger.info(f"📡 Client {client_id} unsubscribed from mission {mission_id}")
                
            except Exception as e:
                current_app.logger.error(f"Error unsubscribing from mission: {e}")
        
        @self.socketio.on('subscribe_to_drone')
        def handle_drone_subscription(data):
            """Handle subscription to specific drone updates.
            
            Args:
                data: Dict containing drone_id
            """
            try:
                drone_id = data.get('drone_id')
                if not drone_id:
                    emit('error', {'message': 'Drone ID required'})
                    return
                
                room = f"drone_{drone_id}"
                join_room(room)
                
                client_id = request.sid
                if client_id in self.connected_clients:
                    self.connected_clients[client_id]['subscriptions'].append(room)
                
                current_app.logger.info(f"📡 Client {client_id} subscribed to drone {drone_id}")
                
                # Send current drone status
                drone_status = self.get_drone_status(drone_id)
                if drone_status:
                    emit('drone_status_update', drone_status)
                
            except Exception as e:
                current_app.logger.error(f"Error subscribing to drone: {e}")
                emit('error', {'message': 'Subscription failed'})
        
        @self.socketio.on('request_fleet_summary')
        def handle_fleet_summary_request():
            """Handle request for current fleet summary."""
            try:
                fleet_summary = self.get_fleet_summary()
                emit('fleet_summary', fleet_summary)
                
            except Exception as e:
                current_app.logger.error(f"Error getting fleet summary: {e}")
                emit('error', {'message': 'Failed to get fleet summary'})
    
    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get comprehensive fleet summary for dashboard.
        
        Returns:
            Dict: Fleet statistics and summary data
        """
        try:
            fleet_summary = Drone.get_fleet_summary()
            
            # Add real-time drone locations
            all_drones = Drone.query.all()
            drone_locations = []
            
            for drone in all_drones:
                if drone.latitude is not None and drone.longitude is not None:
                    drone_locations.append({
                        'id': drone.id,
                        'name': drone.name,
                        'latitude': drone.latitude,
                        'longitude': drone.longitude,
                        'altitude': drone.altitude,
                        'status': drone.status.value,
                        'battery_percentage': drone.battery_percentage
                    })
            
            fleet_summary['drone_locations'] = drone_locations
            fleet_summary['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            return fleet_summary
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error getting fleet summary: {e}")
            raise
    
    def get_active_missions_summary(self) -> Dict[str, Any]:
        """Get summary of all active missions.
        
        Returns:
            Dict: Active missions data
        """
        try:
            active_missions = Mission.query.filter_by(
                status=MissionStatus.IN_PROGRESS
            ).all()
            
            missions_data = []
            for mission in active_missions:
                mission_data = mission.to_dict(include_relations=True)
                missions_data.append(mission_data)
            
            return {
                'active_missions': missions_data,
                'count': len(missions_data),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error getting active missions: {e}")
            raise
    
    def get_mission_status(self, mission_id: int) -> Dict[str, Any]:
        """Get detailed status for a specific mission.
        
        Args:
            mission_id: Mission ID to get status for
            
        Returns:
            Dict: Mission status data or None if not found
        """
        try:
            mission = Mission.query.get(mission_id)
            if not mission:
                return None
            
            return mission.to_dict(include_relations=True)
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error getting mission status: {e}")
            raise
    
    def get_drone_status(self, drone_id: int) -> Dict[str, Any]:
        """Get detailed status for a specific drone.
        
        Args:
            drone_id: Drone ID to get status for
            
        Returns:
            Dict: Drone status data or None if not found
        """
        try:
            drone = Drone.query.get(drone_id)
            if not drone:
                return None
            
            return drone.to_dict(include_relations=True)
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error getting drone status: {e}")
            raise
    
    def broadcast_drone_update(self, drone_data: Dict[str, Any]) -> None:
        """Broadcast drone status update to all subscribers.
        
        Args:
            drone_data: Drone status data to broadcast
        """
        try:
            drone_id = drone_data.get('drone_id')
            if not drone_id:
                return
            
            # Emit to drone-specific room
            self.socketio.emit(
                'drone_status_update',
                drone_data,
                room=f"drone_{drone_id}"
            )
            
            # Emit to global fleet monitoring
            self.socketio.emit('fleet_drone_update', drone_data)
            
            current_app.logger.debug(f"📡 Broadcasted drone update: {drone_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error broadcasting drone update: {e}")
    
    def broadcast_mission_update(self, mission_data: Dict[str, Any]) -> None:
        """Broadcast mission progress update to all subscribers.
        
        Args:
            mission_data: Mission data to broadcast
        """
        try:
            mission_id = mission_data.get('mission_id')
            if not mission_id:
                return
            
            # Emit to mission-specific room
            self.socketio.emit(
                'mission_progress_update',
                mission_data,
                room=f"mission_{mission_id}"
            )
            
            # Emit to global mission monitoring
            self.socketio.emit('global_mission_update', mission_data)
            
            current_app.logger.debug(f"📡 Broadcasted mission update: {mission_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error broadcasting mission update: {e}")
    
    def broadcast_emergency_alert(self, alert_data: Dict[str, Any]) -> None:
        """Broadcast emergency alert to all connected clients.
        
        Args:
            alert_data: Emergency alert data
        """
        try:
            # Add timestamp
            alert_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Broadcast to all clients
            self.socketio.emit('emergency_alert', alert_data)
            
            current_app.logger.warning(f"🚨 Emergency alert broadcasted: {alert_data.get('message', 'Unknown')}")
            
        except Exception as e:
            current_app.logger.error(f"Error broadcasting emergency alert: {e}")
    
    def broadcast_mission_completed(self, completion_data: Dict[str, Any]) -> None:
        """Broadcast mission completion to relevant subscribers.
        
        Args:
            completion_data: Mission completion data
        """
        try:
            mission_id = completion_data.get('mission_id')
            
            # Emit to mission-specific room
            if mission_id:
                self.socketio.emit(
                    'mission_completed',
                    completion_data,
                    room=f"mission_{mission_id}"
                )
            
            # Emit to global monitoring
            self.socketio.emit('global_mission_completed', completion_data)
            
            current_app.logger.info(f"🎯 Mission completion broadcasted: {mission_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error broadcasting mission completion: {e}")
    
    def broadcast_battery_warning(self, warning_data: Dict[str, Any]) -> None:
        """Broadcast battery warning to relevant subscribers.
        
        Args:
            warning_data: Battery warning data
        """
        try:
            drone_id = warning_data.get('drone_id')
            
            # Emit to drone-specific room
            if drone_id:
                self.socketio.emit(
                    'battery_warning',
                    warning_data,
                    room=f"drone_{drone_id}"
                )
            
            # Emit to fleet monitoring
            self.socketio.emit('fleet_battery_warning', warning_data)
            
            warning_level = warning_data.get('warning_level', 'unknown')
            current_app.logger.warning(f"🔋 Battery warning broadcasted: Drone {drone_id} - {warning_level}")
            
        except Exception as e:
            current_app.logger.error(f"Error broadcasting battery warning: {e}")
    
    def send_periodic_updates(self) -> None:
        """Send periodic updates to all connected clients.
        
        This method should be called periodically (e.g., every 30 seconds)
        to send fleet summaries and system status updates.
        """
        try:
            if not self.connected_clients:
                return  # No clients connected
            
            # Send fleet summary
            fleet_summary = self.get_fleet_summary()
            self.socketio.emit('fleet_summary', fleet_summary)
            
            # Send active missions update
            active_missions = self.get_active_missions_summary()
            self.socketio.emit('active_missions_update', active_missions)
            
            current_app.logger.debug(f"📡 Sent periodic updates to {len(self.connected_clients)} clients")
            
        except Exception as e:
            current_app.logger.error(f"Error sending periodic updates: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics.
        
        Returns:
            Dict: Connection statistics
        """
        total_subscriptions = sum(
            len(client_data.get('subscriptions', []))
            for client_data in self.connected_clients.values()
        )
        
        return {
            'connected_clients': len(self.connected_clients),
            'total_subscriptions': total_subscriptions,
            'clients': [
                {
                    'id': client_id,
                    'connected_at': client_data['connected_at'].isoformat(),
                    'subscriptions': len(client_data.get('subscriptions', []))
                }
                for client_id, client_data in self.connected_clients.items()
            ]
        }


# Global WebSocket manager instance
websocket_manager = None


def init_websockets(socketio: SocketIO) -> WebSocketManager:
    """Initialize WebSocket manager with Flask-SocketIO.
    
    Args:
        socketio: Flask-SocketIO instance
        
    Returns:
        WebSocketManager: Initialized WebSocket manager
    """
    global websocket_manager
    websocket_manager = WebSocketManager(socketio)
    return websocket_manager


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance.
    
    Returns:
        WebSocketManager: WebSocket manager instance
        
    Raises:
        RuntimeError: If WebSocket manager not initialized
    """
    if websocket_manager is None:
        raise RuntimeError("WebSocket manager not initialized. Call init_websockets() first.")
    
    return websocket_manager


# Convenience functions for external use
def emit_drone_update(drone_data: Dict[str, Any]) -> None:
    """Emit drone status update via WebSocket.
    
    Args:
        drone_data: Drone status data
    """
    manager = get_websocket_manager()
    manager.broadcast_drone_update(drone_data)


def emit_mission_update(mission_data: Dict[str, Any]) -> None:
    """Emit mission progress update via WebSocket.
    
    Args:
        mission_data: Mission progress data
    """
    manager = get_websocket_manager()
    manager.broadcast_mission_update(mission_data)


def emit_emergency_alert(alert_data: Dict[str, Any]) -> None:
    """Emit emergency alert via WebSocket.
    
    Args:
        alert_data: Emergency alert data
    """
    manager = get_websocket_manager()
    manager.broadcast_emergency_alert(alert_data)


def emit_mission_completed(completion_data: Dict[str, Any]) -> None:
    """Emit mission completion via WebSocket.
    
    Args:
        completion_data: Mission completion data
    """
    manager = get_websocket_manager()
    manager.broadcast_mission_completed(completion_data)


def emit_battery_warning(warning_data: Dict[str, Any]) -> None:
    """Emit battery warning via WebSocket.
    
    Args:
        warning_data: Battery warning data
    """
    manager = get_websocket_manager()
    manager.broadcast_battery_warning(warning_data)