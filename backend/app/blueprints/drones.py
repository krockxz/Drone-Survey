"""
Drones Blueprint for the Drone Survey Management System API.

This module provides RESTful API endpoints for drone fleet management including:
- CRUD operations for drone management
- Real-time status and location updates
- Battery monitoring and alerts
- Fleet statistics and analytics
- Mission assignment capabilities

All endpoints follow REST conventions and provide comprehensive error handling,
input validation, and JSON responses suitable for frontend integration.

Author: FlytBase Assignment
Created: 2024
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import json

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, or_

from app.models import db, Drone, DroneStatus, Mission, MissionStatus


# Create blueprint for drone management endpoints
drones_bp = Blueprint('drones', __name__, url_prefix='/api/v1/drones')


# Error handler decorator for consistent error responses
def handle_errors(func):
    """Decorator to handle common errors and return consistent JSON responses."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return jsonify({
                'error': 'Invalid input',
                'message': str(e),
                'status': 'error'
            }), 400
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({
                'error': 'Database constraint violation',
                'message': 'Drone name must be unique',
                'status': 'error'
            }), 409
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {str(e)}")
            return jsonify({
                'error': 'Database error',
                'message': 'Internal database error occurred',
                'status': 'error'
            }), 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error: {str(e)}")
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred',
                'status': 'error'
            }), 500
    
    wrapper.__name__ = func.__name__
    return wrapper


@drones_bp.route('', methods=['GET'])
@handle_errors
def get_drones() -> Tuple[Dict[str, Any], int]:
    """Get list of all drones with optional filtering and pagination.
    
    Query Parameters:
        status (str): Filter by drone status (available, in-mission, maintenance)
        battery_min (float): Minimum battery percentage filter
        battery_max (float): Maximum battery percentage filter
        page (int): Page number for pagination (default: 1)
        per_page (int): Items per page (default: 20, max: 100)
        include_mission (bool): Include current mission data
        
    Returns:
        JSON response with drone list and metadata
    """
    # Parse query parameters
    status_filter = request.args.get('status')
    battery_min = request.args.get('battery_min', type=float)
    battery_max = request.args.get('battery_max', type=float)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    include_mission = request.args.get('include_mission', 'false').lower() == 'true'
    
    # Build query with filters
    query = Drone.query
    
    if status_filter:
        try:
            status_enum = DroneStatus(status_filter)
            query = query.filter(Drone.status == status_enum)
        except ValueError:
            return jsonify({
                'error': 'Invalid status filter',
                'message': f'Status must be one of: {[s.value for s in DroneStatus]}',
                'status': 'error'
            }), 400
    
    if battery_min is not None:
        query = query.filter(Drone.battery_percentage >= battery_min)
    
    if battery_max is not None:
        query = query.filter(Drone.battery_percentage <= battery_max)
    
    # Execute paginated query
    try:
        pagination = query.order_by(Drone.name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        drones = pagination.items
        
        # Serialize drones
        drones_data = [drone.to_dict(include_relations=include_mission) for drone in drones]
        
        return jsonify({
            'drones': drones_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            },
            'status': 'success'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching drones: {str(e)}")
        return jsonify({
            'error': 'Query failed',
            'message': 'Failed to retrieve drones',
            'status': 'error'
        }), 500


@drones_bp.route('', methods=['POST'])
@handle_errors
def create_drone() -> Tuple[Dict[str, Any], int]:
    """Create a new drone.
    
    Request Body:
        name (str): Unique drone name (required)
        model (str): Drone model/type (required)
        battery_percentage (float): Initial battery level (default: 100.0)
        latitude (float): Initial GPS latitude (optional)
        longitude (float): Initial GPS longitude (optional)
        altitude (float): Initial altitude (default: 0.0)
        notes (str): Optional notes
        
    Returns:
        JSON response with created drone data
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Request body must contain JSON data',
            'status': 'error'
        }), 400
    
    # Validate required fields
    required_fields = ['name', 'model']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'error': 'Missing required field',
                'message': f'Field "{field}" is required',
                'status': 'error'
            }), 400
    
    # Create new drone
    drone = Drone(
        name=data['name'],
        model=data['model'],
        battery_percentage=data.get('battery_percentage', 100.0),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        altitude=data.get('altitude', 0.0),
        notes=data.get('notes')
    )
    
    # Save to database
    db.session.add(drone)
    db.session.commit()
    
    current_app.logger.info(f"Created new drone: {drone.name} ({drone.model})")
    
    return jsonify({
        'drone': drone.to_dict(),
        'message': f'Drone "{drone.name}" created successfully',
        'status': 'success'
    }), 201


@drones_bp.route('/<int:drone_id>', methods=['GET'])
@handle_errors
def get_drone(drone_id: int) -> Tuple[Dict[str, Any], int]:
    """Get detailed information about a specific drone.
    
    Path Parameters:
        drone_id (int): Unique drone identifier
        
    Query Parameters:
        include_mission (bool): Include current mission data
        include_history (bool): Include mission history
        
    Returns:
        JSON response with drone details
    """
    include_mission = request.args.get('include_mission', 'false').lower() == 'true'
    include_history = request.args.get('include_history', 'false').lower() == 'true'
    
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({
            'error': 'Drone not found',
            'message': f'No drone found with ID {drone_id}',
            'status': 'error'
        }), 404
    
    # Prepare response data
    drone_data = drone.to_dict(include_relations=include_mission)
    
    if include_history:
        mission_history = drone.get_mission_history(limit=10)
        drone_data['mission_history'] = [
            {
                'id': mission.id,
                'name': mission.name,
                'status': mission.status.value,
                'created_at': mission.created_at.isoformat(),
                'completed_at': mission.completed_at.isoformat() if mission.completed_at else None,
                'progress_percentage': mission.progress_percentage
            } for mission in mission_history
        ]
    
    return jsonify({
        'drone': drone_data,
        'status': 'success'
    }), 200


@drones_bp.route('/<int:drone_id>', methods=['PUT'])
@handle_errors
def update_drone(drone_id: int) -> Tuple[Dict[str, Any], int]:
    """Update drone information.
    
    Path Parameters:
        drone_id (int): Unique drone identifier
        
    Request Body:
        name (str): Drone name (optional)
        model (str): Drone model (optional)
        notes (str): Operational notes (optional)
        
    Returns:
        JSON response with updated drone data
    """
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({
            'error': 'Drone not found',
            'message': f'No drone found with ID {drone_id}',
            'status': 'error'
        }), 404
    
    data = request.get_json()
    if not data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Request body must contain JSON data',
            'status': 'error'
        }), 400
    
    # Update allowed fields
    updateable_fields = ['name', 'model', 'notes']
    updated_fields = []
    
    for field in updateable_fields:
        if field in data:
            setattr(drone, field, data[field])
            updated_fields.append(field)
    
    if not updated_fields:
        return jsonify({
            'error': 'No updates provided',
            'message': 'Request must contain at least one updateable field',
            'status': 'error'
        }), 400
    
    # Save changes
    drone.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    current_app.logger.info(f"Updated drone {drone.name}: {updated_fields}")
    
    return jsonify({
        'drone': drone.to_dict(),
        'updated_fields': updated_fields,
        'message': f'Drone "{drone.name}" updated successfully',
        'status': 'success'
    }), 200


@drones_bp.route('/<int:drone_id>', methods=['DELETE'])
@handle_errors
def delete_drone(drone_id: int) -> Tuple[Dict[str, Any], int]:
    """Delete a drone from the fleet.
    
    Path Parameters:
        drone_id (int): Unique drone identifier
        
    Returns:
        JSON response confirming deletion
    """
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({
            'error': 'Drone not found',
            'message': f'No drone found with ID {drone_id}',
            'status': 'error'
        }), 404
    
    # Check if drone is currently in a mission
    if drone.status == DroneStatus.IN_MISSION:
        return jsonify({
            'error': 'Cannot delete drone',
            'message': 'Cannot delete drone that is currently in a mission',
            'status': 'error'
        }), 409
    
    drone_name = drone.name
    db.session.delete(drone)
    db.session.commit()
    
    current_app.logger.info(f"Deleted drone: {drone_name}")
    
    return jsonify({
        'message': f'Drone "{drone_name}" deleted successfully',
        'status': 'success'
    }), 200


@drones_bp.route('/<int:drone_id>/status', methods=['PUT'])
@handle_errors
def update_drone_status(drone_id: int) -> Tuple[Dict[str, Any], int]:
    """Update drone operational status.
    
    Path Parameters:
        drone_id (int): Unique drone identifier
        
    Request Body:
        status (str): New status (available, in-mission, maintenance)
        notes (str): Optional status change notes
        
    Returns:
        JSON response with updated drone status
    """
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({
            'error': 'Drone not found',
            'message': f'No drone found with ID {drone_id}',
            'status': 'error'
        }), 404
    
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Request must contain "status" field',
            'status': 'error'
        }), 400
    
    # Validate new status
    try:
        new_status = DroneStatus(data['status'])
    except ValueError:
        return jsonify({
            'error': 'Invalid status',
            'message': f'Status must be one of: {[s.value for s in DroneStatus]}',
            'status': 'error'
        }), 400
    
    # Validate status transition
    old_status = drone.status
    
    # Check if drone can be set to maintenance while in mission
    if new_status == DroneStatus.MAINTENANCE and old_status == DroneStatus.IN_MISSION:
        # This would require aborting the current mission
        current_mission = drone.get_current_mission()
        if current_mission:
            return jsonify({
                'error': 'Cannot set maintenance status',
                'message': 'Drone is currently in a mission. Abort mission first.',
                'current_mission': {
                    'id': current_mission.id,
                    'name': current_mission.name
                },
                'status': 'error'
            }), 409
    
    # Update status
    drone.set_status(new_status, data.get('notes'))
    db.session.commit()
    
    current_app.logger.info(f"Updated drone {drone.name} status: {old_status.value} -> {new_status.value}")
    
    return jsonify({
        'drone': drone.to_dict(),
        'previous_status': old_status.value,
        'message': f'Drone "{drone.name}" status updated to {new_status.value}',
        'status': 'success'
    }), 200


@drones_bp.route('/<int:drone_id>/location', methods=['PUT'])
@handle_errors
def update_drone_location(drone_id: int) -> Tuple[Dict[str, Any], int]:
    """Update drone GPS location and altitude.
    
    Path Parameters:
        drone_id (int): Unique drone identifier
        
    Request Body:
        latitude (float): GPS latitude coordinate (required)
        longitude (float): GPS longitude coordinate (required)
        altitude (float): Altitude in meters (optional)
        
    Returns:
        JSON response with updated location
    """
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({
            'error': 'Drone not found',
            'message': f'No drone found with ID {drone_id}',
            'status': 'error'
        }), 404
    
    data = request.get_json()
    if not data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Request body must contain JSON data',
            'status': 'error'
        }), 400
    
    # Validate required coordinates
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if latitude is None or longitude is None:
        return jsonify({
            'error': 'Missing coordinates',
            'message': 'Both latitude and longitude are required',
            'status': 'error'
        }), 400
    
    # Update location
    altitude = data.get('altitude', drone.altitude)
    drone.update_location(latitude, longitude, altitude)
    db.session.commit()
    
    return jsonify({
        'drone': {
            'id': drone.id,
            'name': drone.name,
            'latitude': drone.latitude,
            'longitude': drone.longitude,
            'altitude': drone.altitude,
            'last_seen': drone.last_seen.isoformat()
        },
        'message': f'Location updated for drone "{drone.name}"',
        'status': 'success'
    }), 200


@drones_bp.route('/<int:drone_id>/battery', methods=['PUT'])
@handle_errors
def update_drone_battery(drone_id: int) -> Tuple[Dict[str, Any], int]:
    """Update drone battery level.
    
    Path Parameters:
        drone_id (int): Unique drone identifier
        
    Request Body:
        battery_percentage (float): Battery level 0-100 (required)
        
    Returns:
        JSON response with updated battery level and alerts
    """
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({
            'error': 'Drone not found',
            'message': f'No drone found with ID {drone_id}',
            'status': 'error'
        }), 404
    
    data = request.get_json()
    if not data or 'battery_percentage' not in data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Request must contain "battery_percentage" field',
            'status': 'error'
        }), 400
    
    battery_percentage = data['battery_percentage']
    
    # Update battery
    old_battery = drone.battery_percentage
    drone.update_battery(battery_percentage)
    
    # Check for battery alerts
    alerts = []
    if drone.is_battery_critical():
        alerts.append({
            'level': 'critical',
            'message': f'CRITICAL: Battery at {battery_percentage}% - Immediate landing required'
        })
    elif drone.is_battery_low():
        alerts.append({
            'level': 'warning', 
            'message': f'WARNING: Battery at {battery_percentage}% - Consider returning to base'
        })
    
    # If drone is in mission and battery is critically low, add abort recommendation
    if alerts and drone.status == DroneStatus.IN_MISSION:
        current_mission = drone.get_current_mission()
        if current_mission:
            alerts.append({
                'level': 'warning',
                'message': f'Consider aborting mission "{current_mission.name}" due to low battery'
            })
    
    db.session.commit()
    
    current_app.logger.info(f"Updated drone {drone.name} battery: {old_battery}% -> {battery_percentage}%")
    
    return jsonify({
        'drone': {
            'id': drone.id,
            'name': drone.name,
            'battery_percentage': drone.battery_percentage,
            'is_battery_low': drone.is_battery_low(),
            'is_battery_critical': drone.is_battery_critical(),
            'estimated_flight_time_minutes': drone.calculate_flight_time_remaining(),
            'last_seen': drone.last_seen.isoformat()
        },
        'alerts': alerts,
        'message': f'Battery updated for drone "{drone.name}"',
        'status': 'success'
    }), 200


@drones_bp.route('/available', methods=['GET'])
@handle_errors
def get_available_drones() -> Tuple[Dict[str, Any], int]:
    """Get all drones available for mission assignment.
    
    Query Parameters:
        min_battery (float): Minimum battery percentage required (default: 20.0)
        
    Returns:
        JSON response with list of available drones
    """
    min_battery = request.args.get('min_battery', 20.0, type=float)
    
    available_drones = Drone.get_available_drones(min_battery=min_battery)
    
    return jsonify({
        'drones': [drone.to_dict() for drone in available_drones],
        'count': len(available_drones),
        'criteria': {
            'status': 'available',
            'min_battery_percentage': min_battery
        },
        'status': 'success'
    }), 200


@drones_bp.route('/fleet-summary', methods=['GET'])
@handle_errors
def get_fleet_summary() -> Tuple[Dict[str, Any], int]:
    """Get comprehensive fleet statistics and summary.
    
    Returns:
        JSON response with fleet analytics and metrics
    """
    summary = Drone.get_fleet_summary()
    
    # Add additional fleet insights
    all_drones = Drone.query.all()
    
    # Calculate fleet health metrics
    if all_drones:
        # Find drones that haven't been seen recently (more than 1 hour)
        one_hour_ago = datetime.now(timezone.utc).replace(microsecond=0) - \
                      datetime.timedelta(hours=1)
        
        offline_drones = [d for d in all_drones if d.last_seen and d.last_seen < one_hour_ago]
        
        # Group drones by model
        model_distribution = {}
        for drone in all_drones:
            model_distribution[drone.model] = model_distribution.get(drone.model, 0) + 1
        
        summary.update({
            'offline_count': len(offline_drones),
            'online_count': len(all_drones) - len(offline_drones),
            'model_distribution': model_distribution,
            'fleet_health_score': calculate_fleet_health_score(all_drones)
        })
    
    return jsonify({
        'fleet_summary': summary,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'status': 'success'
    }), 200


def calculate_fleet_health_score(drones: List[Drone]) -> float:
    """Calculate overall fleet health score (0-100).
    
    Args:
        drones: List of all drones in fleet
        
    Returns:
        float: Health score percentage
    """
    if not drones:
        return 0.0
    
    total_score = 0.0
    
    for drone in drones:
        drone_score = 100.0
        
        # Deduct points for low battery
        if drone.is_battery_critical():
            drone_score -= 30.0
        elif drone.is_battery_low():
            drone_score -= 15.0
        
        # Deduct points for maintenance status
        if drone.status == DroneStatus.MAINTENANCE:
            drone_score -= 20.0
        
        # Deduct points if not seen recently
        if drone.last_seen:
            hours_since_seen = (datetime.now(timezone.utc) - drone.last_seen).total_seconds() / 3600
            if hours_since_seen > 24:
                drone_score -= 25.0
            elif hours_since_seen > 1:
                drone_score -= 10.0
        
        total_score += max(0.0, drone_score)
    
    return round(total_score / len(drones), 1)


# Error handlers for the blueprint
@drones_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found',
        'status': 'error'
    }), 404


@drones_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed', 
        'message': 'The requested method is not allowed for this endpoint',
        'status': 'error'
    }), 405