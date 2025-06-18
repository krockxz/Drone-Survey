"""
Simulator API Blueprint for WebSocket Event Emission.

This blueprint provides API endpoints for the drone simulator to emit
WebSocket events and interact with the main application.

Author: FlytBase Assignment
Created: 2024
"""

from typing import Dict, Any, Tuple
import json

from flask import Blueprint, request, jsonify, current_app
from flask_socketio import SocketIO

from app.websockets.mission_updates import (
    emit_drone_update, emit_mission_update, emit_emergency_alert,
    emit_mission_completed, emit_battery_warning, get_websocket_manager
)


# Create blueprint for simulator endpoints
simulator_bp = Blueprint('simulator', __name__, url_prefix='/api/v1/simulator')


@simulator_bp.route('/emit', methods=['POST'])
def emit_websocket_event() -> Tuple[Dict[str, Any], int]:
    """Emit a WebSocket event from the simulator.
    
    Request Body:
        event (str): Event name to emit
        data (dict): Event data payload
        
    Returns:
        JSON response confirming event emission
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must contain JSON data',
                'status': 'error'
            }), 400
        
        event_name = data.get('event')
        event_data = data.get('data', {})
        
        if not event_name:
            return jsonify({
                'error': 'Missing event name',
                'message': 'Event name is required',
                'status': 'error'
            }), 400
        
        # Emit appropriate WebSocket event based on event name
        if event_name == 'drone_status_update':
            emit_drone_update(event_data)
        elif event_name == 'mission_progress_update':
            emit_mission_update(event_data)
        elif event_name == 'emergency_alert':
            emit_emergency_alert(event_data)
        elif event_name == 'mission_completed':
            emit_mission_completed(event_data)
        elif event_name == 'battery_warning':
            emit_battery_warning(event_data)
        else:
            # Generic event emission
            try:
                websocket_manager = get_websocket_manager()
                websocket_manager.socketio.emit(event_name, event_data)
            except RuntimeError:
                # WebSocket manager not initialized
                current_app.logger.warning("WebSocket manager not initialized")
        
        return jsonify({
            'message': f'Event "{event_name}" emitted successfully',
            'event': event_name,
            'status': 'success'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error emitting WebSocket event: {e}")
        return jsonify({
            'error': 'Event emission failed',
            'message': str(e),
            'status': 'error'
        }), 500


@simulator_bp.route('/status', methods=['GET'])
def get_simulator_status() -> Tuple[Dict[str, Any], int]:
    """Get current simulator and WebSocket status.
    
    Returns:
        JSON response with status information
    """
    try:
        # Get WebSocket connection stats
        try:
            websocket_manager = get_websocket_manager()
            connection_stats = websocket_manager.get_connection_stats()
        except RuntimeError:
            connection_stats = {
                'connected_clients': 0,
                'total_subscriptions': 0,
                'clients': []
            }
        
        return jsonify({
            'websocket_status': {
                'manager_initialized': connection_stats['connected_clients'] >= 0,
                'connections': connection_stats
            },
            'api_status': 'operational',
            'status': 'success'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting simulator status: {e}")
        return jsonify({
            'error': 'Status check failed',
            'message': str(e),
            'status': 'error'
        }), 500


@simulator_bp.route('/test-events', methods=['POST'])
def test_websocket_events() -> Tuple[Dict[str, Any], int]:
    """Test WebSocket event emission with sample data.
    
    Useful for testing WebSocket connectivity and frontend integration.
    
    Returns:
        JSON response with test results
    """
    try:
        # Test drone status update
        test_drone_data = {
            'drone_id': 999,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'altitude': 100.0,
            'battery_percentage': 85.0,
            'status': 'in-mission',
            'last_seen': '2024-01-01T12:00:00Z'
        }
        
        # Test mission progress update
        test_mission_data = {
            'mission_id': 999,
            'progress_percentage': 45.0,
            'current_waypoint': 5,
            'total_waypoints': 12,
            'drone_location': {
                'latitude': 37.7749,
                'longitude': -122.4194,
                'altitude': 100.0
            }
        }
        
        # Emit test events
        emit_drone_update(test_drone_data)
        emit_mission_update(test_mission_data)
        
        return jsonify({
            'message': 'Test events emitted successfully',
            'events_sent': ['drone_status_update', 'mission_progress_update'],
            'test_data': {
                'drone_update': test_drone_data,
                'mission_update': test_mission_data
            },
            'status': 'success'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error testing WebSocket events: {e}")
        return jsonify({
            'error': 'Test event emission failed',
            'message': str(e),
            'status': 'error'
        }), 500