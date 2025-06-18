"""
Analytics and reporting API endpoints.

This blueprint provides data analytics, reporting features,
and organizational metrics for the drone survey system.
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import func, and_
from ..models import db, Mission, Drone, MissionLog, MissionStatus, DroneStatus, LogType
from datetime import datetime, timedelta

# Create blueprint
reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/overview', methods=['GET'])
def get_overview():
    """
    Get system overview with key metrics.
    
    Returns:
        JSON: High-level system statistics and status
    """
    try:
        # Fleet statistics
        total_drones = Drone.query.count()
        available_drones = Drone.query.filter_by(status=DroneStatus.AVAILABLE).count()
        active_drones = Drone.query.filter_by(status=DroneStatus.IN_MISSION).count()
        maintenance_drones = Drone.query.filter_by(status=DroneStatus.MAINTENANCE).count()
        
        # Mission statistics
        total_missions = Mission.query.count()
        completed_missions = Mission.query.filter_by(status=MissionStatus.COMPLETED).count()
        active_missions = Mission.query.filter_by(status=MissionStatus.IN_PROGRESS).count()
        planned_missions = Mission.query.filter_by(status=MissionStatus.PLANNED).count()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_missions = Mission.query.filter(Mission.created_at >= week_ago).count()
        recent_flight_hours = db.session.query(func.sum(Mission.actual_duration_minutes))\
                                       .filter(and_(
                                           Mission.completed_at >= week_ago,
                                           Mission.status == MissionStatus.COMPLETED
                                       )).scalar() or 0
        recent_flight_hours = round(recent_flight_hours / 60, 1)  # Convert to hours
        
        # Average battery levels
        avg_battery = db.session.query(func.avg(Drone.battery_percentage)).scalar() or 0
        avg_battery = round(avg_battery, 1)
        
        return jsonify({
            'fleet': {
                'total_drones': total_drones,
                'available': available_drones,
                'active': active_drones,
                'maintenance': maintenance_drones,
                'average_battery': avg_battery
            },
            'missions': {
                'total_missions': total_missions,
                'completed': completed_missions,
                'active': active_missions,
                'planned': planned_missions,
                'success_rate': round((completed_missions / max(total_missions, 1)) * 100, 1)
            },
            'recent_activity': {
                'missions_last_7_days': recent_missions,
                'flight_hours_last_7_days': recent_flight_hours
            },
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500@reports_bp.route('/missions', methods=['GET'])
def get_mission_analytics():
    """
    Get detailed mission analytics and statistics.
    
    Query Parameters:
        start_date (str): Start date for analysis (ISO format)
        end_date (str): End date for analysis (ISO format)
        groupby (str): Group results by 'day', 'week', or 'month'
    
    Returns:
        JSON: Mission analytics with time-series data
    """
    try:
        # Parse date filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_date = datetime.utcnow() - timedelta(days=30)  # Default: last 30 days
            
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_date = datetime.utcnow()
        
        # Base query for the date range
        base_query = Mission.query.filter(
            Mission.created_at.between(start_date, end_date)
        )
        
        # Mission status breakdown
        status_counts = {}
        for status in MissionStatus:
            count = base_query.filter_by(status=status).count()
            status_counts[status.value] = count
        
        # Completed missions analysis
        completed_missions = base_query.filter_by(status=MissionStatus.COMPLETED).all()
        
        total_flight_time = 0
        total_missions = len(completed_missions)
        
        for mission in completed_missions:
            if mission.actual_duration_minutes:
                total_flight_time += mission.actual_duration_minutes
        
        avg_flight_time = total_flight_time / max(total_missions, 1)
        
        # Mission efficiency metrics
        efficiency_metrics = {
            'total_completed': total_missions,
            'total_flight_hours': round(total_flight_time / 60, 1),
            'average_flight_time_minutes': round(avg_flight_time, 1),
            'missions_per_day': round(total_missions / max((end_date - start_date).days, 1), 2)
        }
        
        # Survey pattern popularity
        pattern_counts = db.session.query(
            Mission.survey_pattern,
            func.count(Mission.id)
        ).filter(
            Mission.created_at.between(start_date, end_date)
        ).group_by(Mission.survey_pattern).all()
        
        pattern_stats = {}
        for pattern, count in pattern_counts:
            pattern_stats[pattern.value] = count
        
        # Time series data (daily mission counts)
        groupby = request.args.get('groupby', 'day')
        time_series = []
        
        if groupby == 'day':
            delta = timedelta(days=1)
            date_format = '%Y-%m-%d'
        elif groupby == 'week':
            delta = timedelta(weeks=1)
            date_format = '%Y-W%U'
        else:  # month
            delta = timedelta(days=30)
            date_format = '%Y-%m'
        
        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + delta
            
            count = Mission.query.filter(
                Mission.created_at.between(current_date, next_date)
            ).count()
            
            time_series.append({
                'date': current_date.strftime(date_format),
                'count': count
            })
            
            current_date = next_date
        
        return jsonify({
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'status_breakdown': status_counts,
            'efficiency_metrics': efficiency_metrics,
            'survey_patterns': pattern_stats,
            'time_series': time_series,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/drones', methods=['GET'])
def get_drone_analytics():
    """
    Get drone fleet analytics and utilization statistics.
    
    Returns:
        JSON: Drone fleet analytics and performance metrics
    """
    try:
        # Fleet status breakdown
        status_counts = {}
        for status in DroneStatus:
            count = Drone.query.filter_by(status=status).count()
            status_counts[status.value] = count
        
        # Battery statistics
        battery_stats = db.session.query(
            func.min(Drone.battery_percentage).label('min_battery'),
            func.max(Drone.battery_percentage).label('max_battery'),
            func.avg(Drone.battery_percentage).label('avg_battery')
        ).first()
        
        # Low battery alerts
        low_battery_drones = Drone.query.filter(
            Drone.battery_percentage < 20
        ).all()
        
        # Flight hours statistics
        flight_stats = db.session.query(
            func.sum(Drone.flight_hours_total).label('total_hours'),
            func.avg(Drone.flight_hours_total).label('avg_hours'),
            func.max(Drone.flight_hours_total).label('max_hours')
        ).first()
        
        # Top performing drones
        top_drones = Drone.query.order_by(
            Drone.missions_completed.desc()
        ).limit(5).all()
        
        # Drone utilization (missions per drone)
        drone_utilization = []
        for drone in Drone.query.all():
            recent_missions = Mission.query.filter_by(drone_id=drone.id)\
                                          .filter(Mission.created_at >= datetime.utcnow() - timedelta(days=30))\
                                          .count()
            
            drone_utilization.append({
                'drone_id': drone.id,
                'drone_name': drone.name,
                'recent_missions': recent_missions,
                'total_missions': drone.missions_completed,
                'flight_hours': drone.flight_hours_total,
                'battery_level': drone.battery_percentage,
                'status': drone.status.value
            })
        
        # Sort by recent activity
        drone_utilization.sort(key=lambda x: x['recent_missions'], reverse=True)
        
        return jsonify({
            'fleet_status': status_counts,
            'battery_stats': {
                'minimum': round(battery_stats.min_battery or 0, 1),
                'maximum': round(battery_stats.max_battery or 0, 1),
                'average': round(battery_stats.avg_battery or 0, 1),
                'low_battery_count': len(low_battery_drones)
            },
            'flight_hours': {
                'total_fleet_hours': round(flight_stats.total_hours or 0, 1),
                'average_per_drone': round(flight_stats.avg_hours or 0, 1),
                'highest_individual': round(flight_stats.max_hours or 0, 1)
            },
            'top_performers': [
                {
                    'id': drone.id,
                    'name': drone.name,
                    'missions_completed': drone.missions_completed,
                    'flight_hours': drone.flight_hours_total
                } for drone in top_drones
            ],
            'utilization_details': drone_utilization,
            'low_battery_alerts': [
                {
                    'id': drone.id,
                    'name': drone.name,
                    'battery_percentage': drone.battery_percentage,
                    'status': drone.status.value
                } for drone in low_battery_drones
            ],
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500@reports_bp.route('/operational', methods=['GET'])
def get_operational_metrics():
    """
    Get operational metrics and efficiency statistics.
    
    Query Parameters:
        period (str): Analysis period - 'week', 'month', 'quarter' (default: month)
    
    Returns:
        JSON: Operational efficiency and safety metrics
    """
    try:
        period = request.args.get('period', 'month')
        
        # Calculate date range based on period
        if period == 'week':
            start_date = datetime.utcnow() - timedelta(weeks=1)
        elif period == 'quarter':
            start_date = datetime.utcnow() - timedelta(days=90)
        else:  # month
            start_date = datetime.utcnow() - timedelta(days=30)
        
        end_date = datetime.utcnow()
        
        # Mission success rate
        total_missions = Mission.query.filter(
            Mission.created_at.between(start_date, end_date)
        ).count()
        
        completed_missions = Mission.query.filter(
            and_(
                Mission.created_at.between(start_date, end_date),
                Mission.status == MissionStatus.COMPLETED
            )
        ).count()
        
        aborted_missions = Mission.query.filter(
            and_(
                Mission.created_at.between(start_date, end_date),
                Mission.status == MissionStatus.ABORTED
            )
        ).count()
        
        success_rate = (completed_missions / max(total_missions, 1)) * 100
        
        # Average mission duration vs estimates
        completed_with_times = Mission.query.filter(
            and_(
                Mission.created_at.between(start_date, end_date),
                Mission.status == MissionStatus.COMPLETED,
                Mission.actual_duration_minutes.isnot(None),
                Mission.estimated_duration_minutes.isnot(None)
            )
        ).all()
        
        duration_accuracy = []
        for mission in completed_with_times:
            accuracy = (mission.estimated_duration_minutes / max(mission.actual_duration_minutes, 1)) * 100
            duration_accuracy.append(min(accuracy, 200))  # Cap at 200% for outliers
        
        avg_duration_accuracy = sum(duration_accuracy) / max(len(duration_accuracy), 1)
        
        # Error and warning analysis
        error_logs = MissionLog.query.filter(
            and_(
                MissionLog.timestamp.between(start_date, end_date),
                MissionLog.log_type == LogType.ERROR
            )
        ).count()
        
        warning_logs = MissionLog.query.filter(
            and_(
                MissionLog.timestamp.between(start_date, end_date),
                MissionLog.log_type == LogType.WARNING
            )
        ).count()
        
        # Fleet availability
        total_fleet_hours = Drone.query.count() * 24 * (end_date - start_date).days
        actual_flight_hours = db.session.query(func.sum(Mission.actual_duration_minutes))\
                                       .filter(and_(
                                           Mission.completed_at.between(start_date, end_date),
                                           Mission.status == MissionStatus.COMPLETED
                                       )).scalar() or 0
        actual_flight_hours = actual_flight_hours / 60  # Convert to hours
        
        fleet_utilization = (actual_flight_hours / max(total_fleet_hours, 1)) * 100
        
        # Safety metrics
        emergency_landings = MissionLog.query.filter(
            and_(
                MissionLog.timestamp.between(start_date, end_date),
                MissionLog.message.ilike('%emergency%')
            )
        ).count()
        
        low_battery_incidents = MissionLog.query.filter(
            and_(
                MissionLog.timestamp.between(start_date, end_date),
                MissionLog.message.ilike('%low battery%')
            )
        ).count()
        
        return jsonify({
            'analysis_period': {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'mission_metrics': {
                'total_missions': total_missions,
                'completed_missions': completed_missions,
                'aborted_missions': aborted_missions,
                'success_rate_percentage': round(success_rate, 1),
                'duration_accuracy_percentage': round(avg_duration_accuracy, 1)
            },
            'fleet_metrics': {
                'utilization_percentage': round(fleet_utilization, 2),
                'total_flight_hours': round(actual_flight_hours, 1),
                'average_missions_per_drone': round(total_missions / max(Drone.query.count(), 1), 1)
            },
            'safety_metrics': {
                'error_count': error_logs,
                'warning_count': warning_logs,
                'emergency_incidents': emergency_landings,
                'low_battery_incidents': low_battery_incidents,
                'incidents_per_mission': round((error_logs + emergency_landings) / max(total_missions, 1), 3)
            },
            'recommendations': [
                f"Mission success rate: {'Good' if success_rate > 90 else 'Needs improvement'}",
                f"Fleet utilization: {'Optimal' if 10 <= fleet_utilization <= 60 else 'Review required'}",
                f"Duration estimates: {'Accurate' if avg_duration_accuracy > 80 else 'Need calibration'}"
            ],
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/export', methods=['GET'])
def export_mission_data():
    """
    Export mission data for external analysis.
    
    Query Parameters:
        format (str): Export format - 'json' or 'csv' (default: json)
        start_date (str): Start date filter
        end_date (str): End date filter
        status (str): Mission status filter
    
    Returns:
        JSON/CSV: Mission data export
    """
    try:
        # Parse filters
        export_format = request.args.get('format', 'json')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status_filter = request.args.get('status')
        
        query = Mission.query
        
        # Apply filters
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Mission.created_at >= start_date)
        
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Mission.created_at <= end_date)
        
        if status_filter:
            try:
                status_enum = MissionStatus(status_filter)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({'error': f'Invalid status: {status_filter}'}), 400
        
        missions = query.all()
        
        # Prepare export data
        export_data = []
        for mission in missions:
            mission_data = {
                'id': mission.id,
                'name': mission.name,
                'status': mission.status.value,
                'survey_pattern': mission.survey_pattern.value,
                'altitude_m': mission.altitude_m,
                'overlap_percentage': mission.overlap_percentage,
                'estimated_duration_minutes': mission.estimated_duration_minutes,
                'actual_duration_minutes': mission.actual_duration_minutes,
                'progress_percentage': mission.progress_percentage,
                'drone_id': mission.drone_id,
                'drone_name': mission.drone.name if mission.drone else None,
                'created_at': mission.created_at.isoformat(),
                'started_at': mission.started_at.isoformat() if mission.started_at else None,
                'completed_at': mission.completed_at.isoformat() if mission.completed_at else None,
                'waypoint_count': len(mission.waypoints)
            }
            export_data.append(mission_data)
        
        if export_format == 'csv':
            # For CSV export, you would typically use pandas or csv module
            # For now, returning a structured format that can be converted
            return jsonify({
                'format': 'csv',
                'data': export_data,
                'headers': list(export_data[0].keys()) if export_data else [],
                'record_count': len(export_data),
                'exported_at': datetime.utcnow().isoformat()
            })
        
        # JSON export
        return jsonify({
            'format': 'json',
            'missions': export_data,
            'record_count': len(export_data),
            'filters_applied': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'status': status_filter
            },
            'exported_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500