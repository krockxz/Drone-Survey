"""
Mission management API endpoints.

This blueprint handles mission planning, execution control,
and monitoring for autonomous drone surveys.
"""

import json
from flask import Blueprint, request, jsonify
from ..models import db, Mission, Drone, Waypoint, MissionLog, MissionStatus, SurveyPattern, LogType, DroneStatus
from ..services import MissionPlanner, WaypointGenerator
from datetime import datetime

# Create blueprint
missions_bp = Blueprint('missions', __name__)

# Initialize services
mission_planner = MissionPlanner()
waypoint_generator = WaypointGenerator()


@missions_bp.route('', methods=['GET'])
def get_missions():
    """
    Get list of missions with optional filtering and pagination.
    
    Query Parameters:
        status (str): Filter by mission status
        drone_id (int): Filter by assigned drone
        page (int): Page number for pagination (default: 1)
        per_page (int): Items per page (default: 20)
    
    Returns:
        JSON: List of missions with metadata
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        query = Mission.query
        
        # Apply filters
        status_filter = request.args.get('status')
        if status_filter:
            try:
                status_enum = MissionStatus(status_filter)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({'error': f'Invalid status: {status_filter}'}), 400
        
        drone_id = request.args.get('drone_id')
        if drone_id:
            query = query.filter_by(drone_id=int(drone_id))
        
        # Order by creation date (newest first)
        query = query.order_by(Mission.created_at.desc())
        
        # Paginate results
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        missions_data = []
        for mission in paginated.items:
            mission_dict = mission.to_dict()
            
            # Add drone information if assigned
            if mission.drone:
                mission_dict['drone'] = {
                    'id': mission.drone.id,
                    'name': mission.drone.name,
                    'status': mission.drone.status.value
                }
            
            missions_data.append(mission_dict)
        
        return jsonify({
            'missions': missions_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500@missions_bp.route('/<int:mission_id>', methods=['GET'])
def get_mission(mission_id):
    """
    Get specific mission with detailed information.
    
    Args:
        mission_id (int): Mission identifier
        
    Returns:
        JSON: Complete mission details including waypoints and logs
    """
    try:
        mission = Mission.query.get_or_404(mission_id)
        
        mission_data = mission.to_dict()
        
        # Add waypoints
        waypoints = [wp.to_dict() for wp in mission.waypoints]
        mission_data['waypoints'] = waypoints
        
        # Add recent logs (last 20)
        logs = MissionLog.query.filter_by(mission_id=mission_id)\
                              .order_by(MissionLog.timestamp.desc())\
                              .limit(20).all()
        mission_data['recent_logs'] = [log.to_dict() for log in logs]
        
        # Add drone information
        if mission.drone:
            mission_data['drone'] = mission.drone.to_dict()
        
        return jsonify(mission_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@missions_bp.route('', methods=['POST'])
def create_mission():
    """
    Create a new mission with automatic waypoint generation.
    
    Request Body:
        name (str): Mission name
        description (str, optional): Mission description
        survey_area_geojson (dict): GeoJSON polygon for survey area
        altitude_m (float): Flight altitude in meters
        overlap_percentage (float): Image overlap percentage
        survey_pattern (str): Survey pattern type
        auto_assign_drone (bool, optional): Auto-assign best drone
        
    Returns:
        JSON: Created mission with generated waypoints
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Plan the mission
        planning_result = mission_planner.plan_mission(
            mission_data=data,
            auto_assign_drone=data.get('auto_assign_drone', True)
        )
        
        if not planning_result['success']:
            return jsonify({'error': planning_result['error']}), 400
        
        # Create mission in database
        try:
            survey_pattern = SurveyPattern(data['survey_pattern'])
        except ValueError:
            return jsonify({'error': f'Invalid survey pattern: {data["survey_pattern"]}'}), 400
        
        mission = Mission(
            name=data['name'],
            description=data.get('description'),
            survey_area_geojson=json.dumps(data['survey_area_geojson']),
            altitude_m=data['altitude_m'],
            overlap_percentage=data['overlap_percentage'],
            survey_pattern=survey_pattern,
            estimated_duration_minutes=planning_result['mission_data']['estimated_duration_minutes'],
            drone_id=planning_result['mission_data'].get('drone_id')
        )
        
        db.session.add(mission)
        db.session.flush()  # Get mission ID
        
        # Create waypoints
        for wp_data in planning_result['waypoints']:
            waypoint = Waypoint(
                mission_id=mission.id,
                latitude=wp_data['latitude'],
                longitude=wp_data['longitude'],
                altitude_m=wp_data['altitude_m'],
                order=wp_data['order']
            )
            db.session.add(waypoint)
        
        # Create initial log entry
        log_entry = MissionLog.create_log(
            mission_id=mission.id,
            message=f"Mission '{mission.name}' created with {len(planning_result['waypoints'])} waypoints",
            log_type=LogType.INFO
        )
        db.session.add(log_entry)
        
        db.session.commit()
        
        # Return complete mission data
        result = mission.to_dict()
        result['waypoints'] = planning_result['waypoints']
        result['assigned_drone'] = planning_result['assigned_drone']
        
        return jsonify(result), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500@missions_bp.route('/generate-waypoints', methods=['POST'])
def generate_waypoints():
    """
    Generate waypoints for mission planning without creating a mission.
    
    Request Body:
        survey_area_geojson (dict): GeoJSON polygon for survey area
        altitude_m (float): Flight altitude in meters
        overlap_percentage (float): Image overlap percentage
        survey_pattern (str): Survey pattern type
        
    Returns:
        JSON: Generated waypoints and mission estimates
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['survey_area_geojson', 'altitude_m', 'overlap_percentage', 'survey_pattern']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate survey pattern
        try:
            survey_pattern = SurveyPattern(data['survey_pattern'])
        except ValueError:
            return jsonify({'error': f'Invalid survey pattern: {data["survey_pattern"]}'}), 400
        
        # Generate waypoints
        waypoints = waypoint_generator.generate_waypoints(
            survey_area_geojson=data['survey_area_geojson'],
            altitude_m=data['altitude_m'],
            overlap_percentage=data['overlap_percentage'],
            survey_pattern=survey_pattern
        )
        
        # Calculate estimates
        estimated_duration = waypoint_generator.calculate_estimated_duration(waypoints)
        cost_estimate = mission_planner.estimate_mission_cost(waypoints)
        
        return jsonify({
            'waypoints': waypoints,
            'waypoint_count': len(waypoints),
            'estimated_duration_minutes': estimated_duration,
            'cost_estimate': cost_estimate,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@missions_bp.route('/<int:mission_id>/start', methods=['POST'])
def start_mission(mission_id):
    """
    Start a planned mission.
    
    Args:
        mission_id (int): Mission identifier
        
    Returns:
        JSON: Success confirmation with updated mission status
    """
    try:
        mission = Mission.query.get_or_404(mission_id)
        
        if mission.status != MissionStatus.PLANNED:
            return jsonify({'error': f'Cannot start mission with status: {mission.status.value}'}), 400
        
        if not mission.drone_id:
            return jsonify({'error': 'No drone assigned to mission'}), 400
        
        # Check drone availability
        drone = Drone.query.get(mission.drone_id)
        if not drone or not drone.is_available_for_mission():
            return jsonify({'error': 'Assigned drone is not available'}), 400
        
        # Start mission
        mission.start_mission()
        drone.status = DroneStatus.IN_MISSION
        
        # Create log entry
        log_entry = MissionLog.create_log(
            mission_id=mission.id,
            message=f"Mission started with drone {drone.name}",
            log_type=LogType.STATUS_CHANGE,
            drone_id=drone.id
        )
        db.session.add(log_entry)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Mission started successfully',
            'mission': mission.to_dict(),
            'drone': drone.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@missions_bp.route('/<int:mission_id>/pause', methods=['POST'])
def pause_mission(mission_id):
    """
    Pause an active mission.
    
    Args:
        mission_id (int): Mission identifier
        
    Returns:
        JSON: Success confirmation
    """
    try:
        mission = Mission.query.get_or_404(mission_id)
        
        if mission.status != MissionStatus.IN_PROGRESS:
            return jsonify({'error': f'Cannot pause mission with status: {mission.status.value}'}), 400
        
        mission.pause_mission()
        
        # Create log entry
        log_entry = MissionLog.create_log(
            mission_id=mission.id,
            message="Mission paused by operator",
            log_type=LogType.STATUS_CHANGE
        )
        db.session.add(log_entry)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Mission paused successfully',
            'mission': mission.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@missions_bp.route('/<int:mission_id>/resume', methods=['POST'])
def resume_mission(mission_id):
    """
    Resume a paused mission.
    
    Args:
        mission_id (int): Mission identifier
        
    Returns:
        JSON: Success confirmation
    """
    try:
        mission = Mission.query.get_or_404(mission_id)
        
        if mission.status != MissionStatus.PAUSED:
            return jsonify({'error': f'Cannot resume mission with status: {mission.status.value}'}), 400
        
        mission.resume_mission()
        
        # Create log entry
        log_entry = MissionLog.create_log(
            mission_id=mission.id,
            message="Mission resumed by operator",
            log_type=LogType.STATUS_CHANGE
        )
        db.session.add(log_entry)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Mission resumed successfully',
            'mission': mission.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@missions_bp.route('/<int:mission_id>/abort', methods=['POST'])
def abort_mission(mission_id):
    """
    Abort an active or paused mission.
    
    Args:
        mission_id (int): Mission identifier
        
    Request Body:
        reason (str, optional): Reason for aborting mission
        
    Returns:
        JSON: Success confirmation
    """
    try:
        mission = Mission.query.get_or_404(mission_id)
        
        if mission.status not in [MissionStatus.IN_PROGRESS, MissionStatus.PAUSED]:
            return jsonify({'error': f'Cannot abort mission with status: {mission.status.value}'}), 400
        
        data = request.get_json() or {}
        reason = data.get('reason', 'Mission aborted by operator')
        
        mission.abort_mission()
        
        # Update drone status if assigned
        if mission.drone:
            mission.drone.status = DroneStatus.AVAILABLE
        
        # Create log entry
        log_entry = MissionLog.create_log(
            mission_id=mission.id,
            message=f"Mission aborted: {reason}",
            log_type=LogType.STATUS_CHANGE,
            details=reason
        )
        db.session.add(log_entry)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Mission aborted successfully',
            'mission': mission.to_dict(),
            'reason': reason
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500@missions_bp.route('/<int:mission_id>/progress', methods=['PUT'])
def update_mission_progress(mission_id):
    """
    Update mission progress during execution.
    
    Args:
        mission_id (int): Mission identifier
        
    Request Body:
        progress_percentage (float): Progress percentage (0-100)
        current_waypoint_id (int, optional): Currently active waypoint
        completed_waypoint_ids (list, optional): List of completed waypoint IDs
        
    Returns:
        JSON: Updated mission status
    """
    try:
        mission = Mission.query.get_or_404(mission_id)
        
        if mission.status != MissionStatus.IN_PROGRESS:
            return jsonify({'error': 'Mission is not in progress'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update progress
        if 'progress_percentage' in data:
            mission.update_progress(data['progress_percentage'])
        
        # Mark waypoints as completed
        if 'completed_waypoint_ids' in data:
            for wp_id in data['completed_waypoint_ids']:
                waypoint = Waypoint.query.filter_by(
                    id=wp_id, 
                    mission_id=mission_id
                ).first()
                if waypoint and not waypoint.completed:
                    waypoint.mark_completed()
                    
                    # Create log entry
                    log_entry = MissionLog.create_log(
                        mission_id=mission.id,
                        message=f"Waypoint {waypoint.order} completed",
                        log_type=LogType.WAYPOINT_REACHED
                    )
                    db.session.add(log_entry)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Progress updated successfully',
            'mission': mission.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@missions_bp.route('/<int:mission_id>/logs', methods=['GET'])
def get_mission_logs(mission_id):
    """
    Get mission logs with pagination.
    
    Args:
        mission_id (int): Mission identifier
        
    Query Parameters:
        page (int): Page number
        per_page (int): Logs per page
        log_type (str): Filter by log type
        
    Returns:
        JSON: Mission logs with pagination
    """
    try:
        Mission.query.get_or_404(mission_id)  # Verify mission exists
        
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 200)
        
        query = MissionLog.query.filter_by(mission_id=mission_id)
        
        # Filter by log type
        log_type_filter = request.args.get('log_type')
        if log_type_filter:
            try:
                log_type_enum = LogType(log_type_filter)
                query = query.filter_by(log_type=log_type_enum)
            except ValueError:
                return jsonify({'error': f'Invalid log type: {log_type_filter}'}), 400
        
        # Order by timestamp (newest first)
        query = query.order_by(MissionLog.timestamp.desc())
        
        # Paginate
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'logs': [log.to_dict() for log in paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@missions_bp.route('/<int:mission_id>', methods=['DELETE'])
def delete_mission(mission_id):
    """
    Delete a mission (only if not in progress).
    
    Args:
        mission_id (int): Mission identifier
        
    Returns:
        JSON: Success confirmation
    """
    try:
        mission = Mission.query.get_or_404(mission_id)
        
        # Prevent deletion of active missions
        if mission.status == MissionStatus.IN_PROGRESS:
            return jsonify({'error': 'Cannot delete mission in progress. Abort first.'}), 400
        
        mission_name = mission.name
        db.session.delete(mission)
        db.session.commit()
        
        return jsonify({
            'message': f'Mission "{mission_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500