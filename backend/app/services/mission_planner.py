"""
Mission planning service for drone survey operations.

This module provides business logic for mission planning, validation,
and optimization for autonomous drone surveys.
"""

import json
from typing import Dict, List, Optional, Any
from shapely.geometry import Polygon
from ..models import Drone, Mission, Waypoint, DroneStatus, MissionStatus
from .waypoint_generator import WaypointGenerator


class MissionPlanner:
    """
    Service class for mission planning and optimization.
    
    Handles mission validation, drone assignment, waypoint generation,
    and mission feasibility analysis.
    """
    
    def __init__(self):
        """Initialize the mission planner."""
        self.waypoint_generator = WaypointGenerator()
    
    def plan_mission(
        self,
        mission_data: Dict[str, Any],
        auto_assign_drone: bool = True
    ) -> Dict[str, Any]:
        """
        Plan a complete mission with waypoint generation and validation.
        
        Args:
            mission_data (dict): Mission configuration data
            auto_assign_drone (bool): Whether to automatically assign a drone
            
        Returns:
            dict: Planning result with mission details and waypoints
        """
        # Validate mission parameters
        validation_result = self.validate_mission_parameters(mission_data)
        if not validation_result['valid']:
            return {
                'success': False,
                'error': validation_result['errors'],
                'mission': None,
                'waypoints': []
            }
        
        # Generate waypoints
        try:
            waypoints = self.waypoint_generator.generate_waypoints(
                survey_area_geojson=mission_data['survey_area_geojson'],
                altitude_m=mission_data['altitude_m'],
                overlap_percentage=mission_data['overlap_percentage'],
                survey_pattern=mission_data['survey_pattern']
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Waypoint generation failed: {str(e)}',
                'mission': None,
                'waypoints': []
            }
        
        # Calculate estimated duration
        estimated_duration = self.waypoint_generator.calculate_estimated_duration(waypoints)
        
        # Auto-assign drone if requested
        assigned_drone = None
        if auto_assign_drone:
            assigned_drone = self.find_best_drone_for_mission(
                waypoints, estimated_duration
            )
        
        return {
            'success': True,
            'mission_data': {
                **mission_data,
                'estimated_duration_minutes': estimated_duration,
                'drone_id': assigned_drone.id if assigned_drone else None
            },
            'waypoints': waypoints,
            'assigned_drone': assigned_drone.to_dict() if assigned_drone else None
        }    
    def validate_mission_parameters(self, mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate mission parameters for safety and feasibility.
        
        Args:
            mission_data (dict): Mission configuration data
            
        Returns:
            dict: Validation result with valid flag and error list
        """
        errors = []
        
        # Required fields
        required_fields = [
            'name', 'survey_area_geojson', 'altitude_m', 
            'overlap_percentage', 'survey_pattern'
        ]
        
        for field in required_fields:
            if field not in mission_data:
                errors.append(f'Missing required field: {field}')
        
        if errors:
            return {'valid': False, 'errors': errors}
        
        # Validate altitude
        altitude = mission_data['altitude_m']
        if not isinstance(altitude, (int, float)) or altitude <= 0:
            errors.append('Altitude must be a positive number')
        elif altitude > 120:  # Regulatory limit in many countries
            errors.append('Altitude exceeds maximum limit of 120 meters')
        elif altitude < 10:
            errors.append('Altitude below minimum safe limit of 10 meters')
        
        # Validate overlap percentage
        overlap = mission_data['overlap_percentage']
        if not isinstance(overlap, (int, float)):
            errors.append('Overlap percentage must be a number')
        elif overlap < 10 or overlap > 90:
            errors.append('Overlap percentage must be between 10% and 90%')
        
        # Validate survey area
        try:
            geojson = mission_data['survey_area_geojson']
            if isinstance(geojson, str):
                geojson = json.loads(geojson)
            
            coords = geojson['coordinates'][0]
            polygon = Polygon(coords)
            
            if not polygon.is_valid:
                errors.append('Survey area polygon is not valid')
            elif polygon.area == 0:
                errors.append('Survey area has zero area')
            
        except Exception as e:
            errors.append(f'Invalid survey area GeoJSON: {str(e)}')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def find_best_drone_for_mission(
        self, 
        waypoints: List[Dict[str, Any]], 
        estimated_duration_minutes: int
    ) -> Optional[Drone]:
        """
        Find the best available drone for a mission.
        
        Args:
            waypoints (List[Dict]): Mission waypoints
            estimated_duration_minutes (int): Estimated mission duration
            
        Returns:
            Drone: Best suited drone or None if none available
        """
        # Get all available drones
        available_drones = Drone.query.filter_by(status=DroneStatus.AVAILABLE).all()
        
        if not available_drones:
            return None
        
        # Score drones based on suitability
        drone_scores = []
        
        for drone in available_drones:
            score = self._calculate_drone_suitability_score(
                drone, waypoints, estimated_duration_minutes
            )
            
            if score > 0:  # Drone is suitable
                drone_scores.append((drone, score))
        
        if not drone_scores:
            return None
        
        # Return drone with highest score
        drone_scores.sort(key=lambda x: x[1], reverse=True)
        return drone_scores[0][0]
    
    def _calculate_drone_suitability_score(
        self, 
        drone: Drone, 
        waypoints: List[Dict[str, Any]], 
        estimated_duration_minutes: int
    ) -> float:
        """
        Calculate suitability score for a drone for a specific mission.
        
        Args:
            drone (Drone): Drone to evaluate
            waypoints (List[Dict]): Mission waypoints
            estimated_duration_minutes (int): Estimated mission duration
            
        Returns:
            float: Suitability score (0 = unsuitable, higher = better)
        """
        score = 0.0
        
        # Battery level scoring (50% of total score)
        battery_score = min(drone.battery_percentage / 100.0, 1.0)
        
        # Require minimum battery for mission
        # Estimate: 1% battery per minute of flight + 20% buffer
        required_battery = (estimated_duration_minutes * 1.0) + 20
        
        if drone.battery_percentage < required_battery:
            return 0.0  # Insufficient battery
        
        score += battery_score * 50
        
        # Experience scoring (30% of total score)
        # Prefer drones with more completed missions
        experience_score = min(drone.missions_completed / 50.0, 1.0)
        score += experience_score * 30
        
        # Location proximity scoring (20% of total score)
        if waypoints and drone.current_location_lat and drone.current_location_lng:
            # Distance to first waypoint
            first_waypoint = waypoints[0]
            lat_diff = abs(drone.current_location_lat - first_waypoint['latitude'])
            lng_diff = abs(drone.current_location_lng - first_waypoint['longitude'])
            distance_score = max(0, 1.0 - (lat_diff + lng_diff) / 2.0)  # Simplified
            score += distance_score * 20
        else:
            score += 10  # Partial score if location unknown
        
        return score
    
    def estimate_mission_cost(
        self, 
        waypoints: List[Dict[str, Any]], 
        drone_model: str = None
    ) -> Dict[str, Any]:
        """
        Estimate operational cost for a mission.
        
        Args:
            waypoints (List[Dict]): Mission waypoints
            drone_model (str): Specific drone model for cost calculation
            
        Returns:
            dict: Cost breakdown and estimates
        """
        if not waypoints:
            return {'total_cost': 0, 'breakdown': {}}
        
        duration_minutes = self.waypoint_generator.calculate_estimated_duration(waypoints)
        
        # Basic cost estimates (would be configurable in production)
        costs = {
            'flight_time_cost': duration_minutes * 2.50,  # $2.50 per minute
            'battery_wear_cost': duration_minutes * 0.50,  # Battery degradation
            'maintenance_cost': duration_minutes * 0.75,   # Maintenance allocation
            'operator_cost': duration_minutes * 1.00       # Operator time
        }
        
        total_cost = sum(costs.values())
        
        return {
            'total_cost': round(total_cost, 2),
            'duration_minutes': duration_minutes,
            'breakdown': costs
        }