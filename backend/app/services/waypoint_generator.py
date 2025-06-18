"""
Waypoint Generation Service for Automated Flight Planning.

This service provides sophisticated algorithms for generating flight waypoints
based on survey area geometry and mission parameters. Supports multiple
survey patterns including crosshatch, grid, and perimeter patterns.

Author: FlytBase Assignment
Created: 2024
"""

import json
import math
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

try:
    from shapely.geometry import Polygon, Point, LineString
    from shapely.ops import cascaded_union
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("Warning: Shapely not available. Some waypoint generation features will be limited.")


@dataclass
class WaypointData:
    """Data class representing a generated waypoint."""
    latitude: float
    longitude: float
    altitude: float
    order: int
    action: str = "capture"
    estimated_time_seconds: Optional[int] = None


class WaypointGenerator:
    """
    Advanced waypoint generation service for automated drone survey missions.
    
    Provides multiple survey patterns with configurable parameters:
    - Crosshatch: Parallel lines with optional cross lines
    - Grid: Systematic grid coverage with overlap
    - Perimeter: Boundary following with configurable offset
    - Custom: User-defined waypoint sequences
    """
    
    def __init__(self):
        """Initialize the waypoint generator."""
        self.earth_radius_m = 6371000  # Earth's radius in meters
        
        # Flight parameters
        self.default_speed_mps = 15.0  # 15 m/s default flight speed
        self.turn_time_seconds = 3.0   # Time for turns/direction changes
        self.capture_time_seconds = 2.0  # Time for photo capture
    
    def generate_waypoints(self, survey_area_geojson: str, altitude_m: float,
                          overlap_percentage: float, pattern_type: str,
                          **kwargs) -> List[WaypointData]:
        """Generate waypoints for a survey mission.
        
        Args:
            survey_area_geojson: GeoJSON polygon string defining survey area
            altitude_m: Flight altitude in meters
            overlap_percentage: Photo overlap percentage (30-90)
            pattern_type: Type of survey pattern (crosshatch, grid, perimeter)
            **kwargs: Additional pattern-specific parameters
            
        Returns:
            List[WaypointData]: Generated waypoints in flight order
            
        Raises:
            ValueError: If parameters are invalid
            NotImplementedError: If pattern type is not supported
        """
        # Validate inputs
        self._validate_inputs(survey_area_geojson, altitude_m, overlap_percentage, pattern_type)
        
        # Parse survey area
        survey_polygon = self._parse_survey_area(survey_area_geojson)
        
        # Generate waypoints based on pattern type
        if pattern_type == "crosshatch":
            waypoints = self._generate_crosshatch_pattern(
                survey_polygon, altitude_m, overlap_percentage, **kwargs
            )
        elif pattern_type == "grid":
            waypoints = self._generate_grid_pattern(
                survey_polygon, altitude_m, overlap_percentage, **kwargs
            )
        elif pattern_type == "perimeter":
            waypoints = self._generate_perimeter_pattern(
                survey_polygon, altitude_m, **kwargs
            )
        else:
            raise NotImplementedError(f"Pattern type '{pattern_type}' not implemented")
        
        # Add takeoff and landing waypoints
        waypoints = self._add_takeoff_landing(waypoints, survey_polygon)
        
        # Calculate estimated times
        waypoints = self._calculate_timing(waypoints)
        
        return waypoints
    
    def _validate_inputs(self, survey_area_geojson: str, altitude_m: float,
                        overlap_percentage: float, pattern_type: str) -> None:
        """Validate input parameters.
        
        Args:
            survey_area_geojson: Survey area GeoJSON
            altitude_m: Flight altitude
            overlap_percentage: Photo overlap percentage
            pattern_type: Survey pattern type
            
        Raises:
            ValueError: If any parameter is invalid
        """
        if not survey_area_geojson:
            raise ValueError("Survey area GeoJSON is required")
        
        if altitude_m < 10.0 or altitude_m > 400.0:
            raise ValueError("Altitude must be between 10 and 400 meters")
        
        if overlap_percentage < 30.0 or overlap_percentage > 90.0:
            raise ValueError("Overlap percentage must be between 30 and 90")
        
        valid_patterns = ["crosshatch", "grid", "perimeter"]
        if pattern_type not in valid_patterns:
            raise ValueError(f"Pattern type must be one of: {valid_patterns}")
    
    def _parse_survey_area(self, survey_area_geojson: str) -> Polygon:
        """Parse GeoJSON survey area into Shapely polygon.
        
        Args:
            survey_area_geojson: GeoJSON polygon string
            
        Returns:
            Polygon: Parsed survey area polygon
            
        Raises:
            ValueError: If GeoJSON is invalid
        """
        try:
            geojson_data = json.loads(survey_area_geojson)
            
            if geojson_data.get('type') != 'Polygon':
                raise ValueError("GeoJSON must be a Polygon")
            
            coordinates = geojson_data['coordinates'][0]  # Exterior ring
            
            if SHAPELY_AVAILABLE:
                # Use Shapely for precise geometric operations
                polygon = Polygon(coordinates)
                if not polygon.is_valid:
                    raise ValueError("Invalid polygon geometry")
                return polygon
            else:
                # Fallback: simple coordinate validation
                if len(coordinates) < 4:
                    raise ValueError("Polygon must have at least 4 coordinates")
                
                # Create a simple polygon representation
                return self._create_simple_polygon(coordinates)
                
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ValueError(f"Invalid GeoJSON format: {e}")
    
    def _create_simple_polygon(self, coordinates: List[List[float]]) -> Dict:
        """Create simple polygon representation when Shapely is not available.
        
        Args:
            coordinates: List of [lon, lat] coordinate pairs
            
        Returns:
            Dict: Simple polygon representation
        """
        return {
            'coordinates': coordinates,
            'bounds': self._calculate_bounds(coordinates)
        }
    
    def _calculate_bounds(self, coordinates: List[List[float]]) -> Tuple[float, float, float, float]:
        """Calculate bounding box of coordinates.
        
        Args:
            coordinates: List of [lon, lat] coordinate pairs
            
        Returns:
            Tuple: (min_lon, min_lat, max_lon, max_lat)
        """
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        return (min(lons), min(lats), max(lons), max(lats))
    
    def _generate_crosshatch_pattern(self, polygon, altitude_m: float,
                                   overlap_percentage: float, **kwargs) -> List[WaypointData]:
        """Generate crosshatch survey pattern.
        
        Args:
            polygon: Survey area polygon
            altitude_m: Flight altitude
            overlap_percentage: Photo overlap percentage
            **kwargs: Additional parameters (line_spacing_m, cross_lines)
            
        Returns:
            List[WaypointData]: Crosshatch waypoints
        """
        # Calculate line spacing based on altitude and overlap
        line_spacing_m = self._calculate_line_spacing(altitude_m, overlap_percentage)
        
        # Override with custom spacing if provided
        if 'line_spacing_m' in kwargs:
            line_spacing_m = kwargs['line_spacing_m']
        
        cross_lines = kwargs.get('cross_lines', True)
        
        if SHAPELY_AVAILABLE:
            return self._generate_crosshatch_shapely(polygon, altitude_m, line_spacing_m, cross_lines)
        else:
            return self._generate_crosshatch_simple(polygon, altitude_m, line_spacing_m, cross_lines)
    
    def _generate_crosshatch_shapely(self, polygon: Polygon, altitude_m: float,
                                   line_spacing_m: float, cross_lines: bool) -> List[WaypointData]:
        """Generate crosshatch pattern using Shapely (precise).
        
        Args:
            polygon: Shapely polygon
            altitude_m: Flight altitude
            line_spacing_m: Distance between parallel lines
            cross_lines: Whether to include perpendicular cross lines
            
        Returns:
            List[WaypointData]: Generated waypoints
        """
        waypoints = []
        order = 1
        
        # Get polygon bounds
        minx, miny, maxx, maxy = polygon.bounds
        
        # Convert line spacing from meters to degrees (approximate)
        lat_spacing_deg = line_spacing_m / 111000.0  # 1 degree lat ≈ 111 km
        lon_spacing_deg = line_spacing_m / (111000.0 * math.cos(math.radians((miny + maxy) / 2)))
        
        # Generate north-south lines
        current_lon = minx
        direction = 1  # 1 for north, -1 for south
        
        while current_lon <= maxx:
            # Create line from south to north or north to south
            if direction == 1:
                line = LineString([(current_lon, miny), (current_lon, maxy)])
            else:
                line = LineString([(current_lon, maxy), (current_lon, miny)])
            
            # Find intersection with polygon
            intersection = polygon.intersection(line)
            
            if intersection and hasattr(intersection, 'coords'):
                # Add waypoints along this line
                for coord in intersection.coords:
                    waypoints.append(WaypointData(
                        latitude=coord[1],
                        longitude=coord[0],
                        altitude=altitude_m,
                        order=order,
                        action="capture"
                    ))
                    order += 1
            
            current_lon += lon_spacing_deg
            direction *= -1  # Alternate direction for efficiency
        
        # Add cross lines if requested
        if cross_lines:
            current_lat = miny
            
            while current_lat <= maxy:
                line = LineString([(minx, current_lat), (maxx, current_lat)])
                intersection = polygon.intersection(line)
                
                if intersection and hasattr(intersection, 'coords'):
                    for coord in intersection.coords:
                        waypoints.append(WaypointData(
                            latitude=coord[1],
                            longitude=coord[0],
                            altitude=altitude_m,
                            order=order,
                            action="capture"
                        ))
                        order += 1
                
                current_lat += lat_spacing_deg
        
        return waypoints
    
    def _generate_crosshatch_simple(self, polygon: Dict, altitude_m: float,
                                  line_spacing_m: float, cross_lines: bool) -> List[WaypointData]:
        """Generate crosshatch pattern using simple geometry (fallback).
        
        Args:
            polygon: Simple polygon representation
            altitude_m: Flight altitude
            line_spacing_m: Distance between lines
            cross_lines: Whether to include cross lines
            
        Returns:
            List[WaypointData]: Generated waypoints
        """
        waypoints = []
        order = 1
        
        bounds = polygon['bounds']
        minx, miny, maxx, maxy = bounds
        
        # Convert spacing to degrees
        lat_spacing_deg = line_spacing_m / 111000.0
        lon_spacing_deg = line_spacing_m / (111000.0 * math.cos(math.radians((miny + maxy) / 2)))
        
        # Generate simple grid within bounds
        current_lat = miny + lat_spacing_deg
        while current_lat < maxy:
            current_lon = minx + lon_spacing_deg
            while current_lon < maxx:
                # Simple point-in-polygon test
                if self._point_in_polygon_simple(current_lon, current_lat, polygon['coordinates']):
                    waypoints.append(WaypointData(
                        latitude=current_lat,
                        longitude=current_lon,
                        altitude=altitude_m,
                        order=order,
                        action="capture"
                    ))
                    order += 1
                
                current_lon += lon_spacing_deg
            current_lat += lat_spacing_deg
        
        return waypoints
    
    def _generate_grid_pattern(self, polygon, altitude_m: float,
                             overlap_percentage: float, **kwargs) -> List[WaypointData]:
        """Generate grid survey pattern.
        
        Args:
            polygon: Survey area polygon
            altitude_m: Flight altitude
            overlap_percentage: Photo overlap percentage
            **kwargs: Additional parameters
            
        Returns:
            List[WaypointData]: Grid pattern waypoints
        """
        # Grid pattern is similar to crosshatch but with systematic coverage
        return self._generate_crosshatch_pattern(
            polygon, altitude_m, overlap_percentage, cross_lines=True, **kwargs
        )
    
    def _generate_perimeter_pattern(self, polygon, altitude_m: float,
                                  **kwargs) -> List[WaypointData]:
        """Generate perimeter survey pattern.
        
        Args:
            polygon: Survey area polygon
            altitude_m: Flight altitude
            **kwargs: Additional parameters (buffer_distance_m)
            
        Returns:
            List[WaypointData]: Perimeter waypoints
        """
        buffer_distance_m = kwargs.get('buffer_distance_m', 10.0)
        waypoints = []
        order = 1
        
        if SHAPELY_AVAILABLE and hasattr(polygon, 'exterior'):
            # Use Shapely for precise perimeter following
            coords = list(polygon.exterior.coords)
        else:
            # Use simple polygon coordinates
            coords = polygon['coordinates']
        
        # Generate waypoints along perimeter
        for i, coord in enumerate(coords[:-1]):  # Skip last point (same as first)
            waypoints.append(WaypointData(
                latitude=coord[1],
                longitude=coord[0],
                altitude=altitude_m,
                order=order,
                action="capture"
            ))
            order += 1
        
        return waypoints
    
    def _calculate_line_spacing(self, altitude_m: float, overlap_percentage: float) -> float:
        """Calculate line spacing based on altitude and desired overlap.
        
        Args:
            altitude_m: Flight altitude
            overlap_percentage: Desired photo overlap
            
        Returns:
            float: Line spacing in meters
        """
        # Simplified calculation for drone camera with typical field of view
        # Assumes 90-degree FOV camera (typical for survey drones)
        ground_width_m = altitude_m * 1.732  # tan(60°) for 60° half-angle
        
        # Calculate spacing for desired overlap
        overlap_factor = (100.0 - overlap_percentage) / 100.0
        line_spacing_m = ground_width_m * overlap_factor
        
        return max(line_spacing_m, 10.0)  # Minimum 10m spacing
    
    def _add_takeoff_landing(self, waypoints: List[WaypointData],
                           polygon) -> List[WaypointData]:
        """Add takeoff and landing waypoints to the mission.
        
        Args:
            waypoints: Existing survey waypoints
            polygon: Survey area polygon
            
        Returns:
            List[WaypointData]: Waypoints with takeoff/landing added
        """
        if not waypoints:
            return waypoints
        
        # Find a suitable takeoff/landing point (first waypoint location)
        first_waypoint = waypoints[0]
        
        # Create takeoff waypoint
        takeoff_waypoint = WaypointData(
            latitude=first_waypoint.latitude,
            longitude=first_waypoint.longitude,
            altitude=first_waypoint.altitude,
            order=0,
            action="takeoff"
        )
        
        # Create landing waypoint
        landing_waypoint = WaypointData(
            latitude=first_waypoint.latitude,
            longitude=first_waypoint.longitude,
            altitude=0.0,  # Land at ground level
            order=len(waypoints) + 1,
            action="land"
        )
        
        # Update order of existing waypoints
        for i, waypoint in enumerate(waypoints):
            waypoint.order = i + 1
        
        return [takeoff_waypoint] + waypoints + [landing_waypoint]
    
    def _calculate_timing(self, waypoints: List[WaypointData]) -> List[WaypointData]:
        """Calculate estimated time for each waypoint.
        
        Args:
            waypoints: Waypoints to calculate timing for
            
        Returns:
            List[WaypointData]: Waypoints with timing information
        """
        total_time = 0
        
        for i, waypoint in enumerate(waypoints):
            if i == 0:
                # First waypoint (takeoff)
                waypoint.estimated_time_seconds = int(total_time)
                if waypoint.action == "takeoff":
                    total_time += 10.0  # 10 seconds for takeoff
            else:
                # Calculate travel time from previous waypoint
                prev_waypoint = waypoints[i - 1]
                distance_m = self._calculate_distance(
                    prev_waypoint.latitude, prev_waypoint.longitude,
                    waypoint.latitude, waypoint.longitude
                )
                
                travel_time = distance_m / self.default_speed_mps
                total_time += travel_time
                
                # Add action time
                if waypoint.action == "capture":
                    total_time += self.capture_time_seconds
                elif waypoint.action == "hover":
                    total_time += 5.0  # 5 seconds hover
                elif waypoint.action == "land":
                    total_time += 15.0  # 15 seconds for landing
                
                waypoint.estimated_time_seconds = int(total_time)
        
        return waypoints
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates.
        
        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate
            
        Returns:
            float: Distance in meters
        """
        # Haversine formula
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat_rad = math.radians(lat2 - lat1)
        dlon_rad = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat_rad / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon_rad / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return self.earth_radius_m * c
    
    def _point_in_polygon_simple(self, x: float, y: float, polygon_coords: List[List[float]]) -> bool:
        """Simple point-in-polygon test using ray casting algorithm.
        
        Args:
            x, y: Point coordinates to test
            polygon_coords: Polygon coordinate list
            
        Returns:
            bool: True if point is inside polygon
        """
        n = len(polygon_coords)
        inside = False
        
        p1x, p1y = polygon_coords[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon_coords[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def estimate_mission_duration(self, waypoints: List[WaypointData]) -> int:
        """Estimate total mission duration in minutes.
        
        Args:
            waypoints: Mission waypoints
            
        Returns:
            int: Estimated duration in minutes
        """
        if not waypoints:
            return 0
        
        # Get the last waypoint's estimated time
        last_waypoint = waypoints[-1]
        total_seconds = last_waypoint.estimated_time_seconds or 0
        
        # Add buffer time (10% for safety margin)
        total_seconds = int(total_seconds * 1.1)
        
        return max(1, total_seconds // 60)  # Convert to minutes, minimum 1 minute
    
    def validate_waypoints(self, waypoints: List[WaypointData]) -> List[str]:
        """Validate generated waypoints for safety and feasibility.
        
        Args:
            waypoints: Waypoints to validate
            
        Returns:
            List[str]: List of validation warnings/errors
        """
        warnings = []
        
        if not waypoints:
            warnings.append("No waypoints generated")
            return warnings
        
        # Check for reasonable number of waypoints
        if len(waypoints) > 200:
            warnings.append("Large number of waypoints may exceed drone capabilities")
        
        # Check for altitude consistency
        altitudes = [wp.altitude for wp in waypoints if wp.action != "land"]
        if altitudes and (max(altitudes) - min(altitudes)) > 50:
            warnings.append("Large altitude variations detected")
        
        # Check for reasonable distances between waypoints
        for i in range(1, len(waypoints)):
            distance = self._calculate_distance(
                waypoints[i-1].latitude, waypoints[i-1].longitude,
                waypoints[i].latitude, waypoints[i].longitude
            )
            
            if distance > 1000:  # More than 1km between waypoints
                warnings.append(f"Large distance ({distance:.0f}m) between waypoints {i-1} and {i}")
        
        # Check mission duration
        duration_minutes = self.estimate_mission_duration(waypoints)
        if duration_minutes > 30:  # Typical drone flight time limit
            warnings.append(f"Mission duration ({duration_minutes} min) may exceed battery capacity")
        
        return warnings