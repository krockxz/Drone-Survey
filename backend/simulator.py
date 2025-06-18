#!/usr/bin/env python3
"""
Drone Flight Simulator for Real-time Demo

This simulator creates realistic drone flight patterns for active missions,
enabling demonstration of real-time monitoring, WebSocket updates, and
mission progress tracking. Perfect for demo videos and system testing.

Features:
- Multi-drone concurrent mission simulation
- Realistic flight physics and battery consumption
- WebSocket event emission for real-time updates
- Waypoint-based navigation with smooth interpolation
- Emergency landing on low battery
- Mission completion and status management

Usage:
    python simulator.py [--interval SECONDS] [--verbose]

Author: FlytBase Assignment
Created: 2024
"""

import os
import sys
import time
import math
import json
import logging
import argparse
import threading
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add the app directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy

# Import application models and configuration
from config import get_config
from app.models import Drone, Mission, Waypoint, MissionStatus, DroneStatus, MissionLog


@dataclass
class FlightState:
    """Represents the current flight state of a simulated drone."""
    drone_id: int
    mission_id: int
    current_waypoint_index: int
    target_waypoint_index: int
    current_lat: float
    current_lon: float
    current_alt: float
    battery_percentage: float
    speed_mps: float  # meters per second
    last_update: datetime
    is_moving: bool = True
    emergency_landing: bool = False


class DroneFlightSimulator:
    """
    Advanced drone flight simulator that provides realistic movement patterns,
    battery consumption, and mission progress tracking for demonstration purposes.
    """
    
    def __init__(self, config_name: str = 'development'):
        """Initialize the simulator with database connection and configuration.
        
        Args:
            config_name: Configuration environment to use
        """
        self.config = get_config(config_name)()
        
        # Setup logging
        self.setup_logging()
        
        # Database setup
        self.setup_database()
        
        # Flight simulation parameters
        self.update_interval = 2.0  # seconds between updates
        self.flight_speed_mps = 15.0  # 15 m/s ≈ 54 km/h (realistic drone speed)
        self.battery_consumption_rate = 0.8  # percent per minute at cruise
        self.hover_battery_rate = 0.3  # percent per minute when hovering
        self.takeoff_landing_rate = 1.5  # percent per takeoff/landing
        
        # WebSocket client for real-time updates
        self.websocket_url = "http://localhost:5000"
        
        # Active flight states
        self.active_flights: Dict[int, FlightState] = {}
        
        # Simulation control
        self.running = False
        self.simulation_thread = None
        
        self.logger.info("🚁 Drone Flight Simulator initialized")
    
    def setup_logging(self) -> None:
        """Configure logging for the simulator."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('drone_simulator.log')
            ]
        )
        self.logger = logging.getLogger('DroneSimulator')
    
    def setup_database(self) -> None:
        """Setup database connection using application configuration."""
        try:
            self.engine = create_engine(self.config.SQLALCHEMY_DATABASE_URI)
            Session = sessionmaker(bind=self.engine)
            self.db_session = Session()
            
            # Test connection
            self.db_session.execute("SELECT 1")
            self.logger.info("✅ Database connection established")
            
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def emit_websocket_event(self, event_name: str, data: Dict) -> None:
        """Emit WebSocket event to the Flask application.
        
        Args:
            event_name: Name of the WebSocket event
            data: Event data payload
        """
        try:
            response = requests.post(
                f"{self.websocket_url}/api/v1/simulator/emit",
                json={"event": event_name, "data": data},
                timeout=2
            )
            
            if response.status_code == 200:
                self.logger.debug(f"✅ Emitted {event_name}: {data.get('drone_id', 'N/A')}")
            else:
                self.logger.warning(f"⚠️ WebSocket emit failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"WebSocket emit error (service may be down): {e}")
    
    def get_active_missions(self) -> List[Mission]:
        """Get all missions currently in progress.
        
        Returns:
            List[Mission]: Active missions with assigned drones
        """
        try:
            missions = self.db_session.query(Mission).filter(
                Mission.status == MissionStatus.IN_PROGRESS,
                Mission.drone_id.isnot(None)
            ).all()
            
            return missions
            
        except Exception as e:
            self.logger.error(f"Error fetching active missions: {e}")
            return []
    
    def initialize_flight_state(self, mission: Mission) -> Optional[FlightState]:
        """Initialize flight state for a mission.
        
        Args:
            mission: Mission to initialize flight for
            
        Returns:
            FlightState: Initialized flight state or None if error
        """
        try:
            drone = self.db_session.query(Drone).get(mission.drone_id)
            waypoints = self.db_session.query(Waypoint).filter_by(
                mission_id=mission.id
            ).order_by(Waypoint.order).all()
            
            if not drone or not waypoints:
                self.logger.warning(f"Mission {mission.id} missing drone or waypoints")
                return None
            
            # Start at first waypoint or current drone location
            start_waypoint = waypoints[0]
            
            flight_state = FlightState(
                drone_id=drone.id,
                mission_id=mission.id,
                current_waypoint_index=0,
                target_waypoint_index=1 if len(waypoints) > 1 else 0,
                current_lat=drone.latitude or start_waypoint.latitude,
                current_lon=drone.longitude or start_waypoint.longitude,
                current_alt=drone.altitude or start_waypoint.altitude,
                battery_percentage=drone.battery_percentage,
                speed_mps=self.flight_speed_mps,
                last_update=datetime.now(timezone.utc)
            )
            
            self.logger.info(f"🚁 Initialized flight for drone {drone.name} on mission {mission.name}")
            return flight_state
            
        except Exception as e:
            self.logger.error(f"Error initializing flight state: {e}")
            return None
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates using Haversine formula.
        
        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate
            
        Returns:
            float: Distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat_rad = math.radians(lat2 - lat1)
        dlon_rad = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat_rad / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon_rad / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def interpolate_position(self, current_lat: float, current_lon: float,
                           target_lat: float, target_lon: float,
                           distance_to_move: float, total_distance: float) -> Tuple[float, float]:
        """Interpolate position between current and target coordinates.
        
        Args:
            current_lat, current_lon: Current position
            target_lat, target_lon: Target position
            distance_to_move: Distance to move in meters
            total_distance: Total distance to target
            
        Returns:
            Tuple[float, float]: New latitude and longitude
        """
        if total_distance == 0:
            return current_lat, current_lon
        
        # Calculate movement ratio
        ratio = min(distance_to_move / total_distance, 1.0)
        
        # Linear interpolation (good enough for short distances)
        new_lat = current_lat + (target_lat - current_lat) * ratio
        new_lon = current_lon + (target_lon - current_lon) * ratio
        
        return new_lat, new_lon
    
    def update_flight_state(self, flight_state: FlightState) -> bool:
        """Update a single drone's flight state and position.
        
        Args:
            flight_state: Current flight state to update
            
        Returns:
            bool: True if mission is still active, False if completed/aborted
        """
        try:
            # Get mission and waypoints
            mission = self.db_session.query(Mission).get(flight_state.mission_id)
            drone = self.db_session.query(Drone).get(flight_state.drone_id)
            waypoints = self.db_session.query(Waypoint).filter_by(
                mission_id=flight_state.mission_id
            ).order_by(Waypoint.order).all()
            
            if not mission or not drone or not waypoints:
                self.logger.warning(f"Mission {flight_state.mission_id} data missing")
                return False
            
            # Check if mission is still in progress
            if mission.status != MissionStatus.IN_PROGRESS:
                self.logger.info(f"Mission {mission.name} no longer in progress")
                return False
            
            # Emergency landing if battery critical
            if flight_state.battery_percentage <= 5.0 and not flight_state.emergency_landing:
                self.logger.warning(f"🔋 Emergency landing for drone {drone.name} - Critical battery!")
                flight_state.emergency_landing = True
                flight_state.is_moving = False
                
                # Emit emergency alert
                self.emit_websocket_event('emergency_alert', {
                    'drone_id': drone.id,
                    'mission_id': mission.id,
                    'alert_type': 'critical_battery',
                    'message': f'Emergency landing initiated for {drone.name}',
                    'battery_percentage': flight_state.battery_percentage
                })
                
                # Abort mission
                mission.abort_mission("Critical battery - emergency landing")
                self.db_session.commit()
                return False
            
            # Calculate time elapsed since last update
            now = datetime.now(timezone.utc)
            time_elapsed = (now - flight_state.last_update).total_seconds()
            flight_state.last_update = now
            
            # Update battery consumption
            battery_drain = 0.0
            if flight_state.is_moving:
                battery_drain = (self.battery_consumption_rate / 60.0) * time_elapsed
            else:
                battery_drain = (self.hover_battery_rate / 60.0) * time_elapsed
            
            flight_state.battery_percentage = max(0.0, flight_state.battery_percentage - battery_drain)
            
            # Get current target waypoint
            if flight_state.target_waypoint_index >= len(waypoints):
                # Mission completed!
                self.logger.info(f"🎯 Mission {mission.name} completed by drone {drone.name}")
                mission.complete_mission()
                self.db_session.commit()
                
                # Emit completion event
                self.emit_websocket_event('mission_completed', {
                    'mission_id': mission.id,
                    'drone_id': drone.id,
                    'completion_time': now.isoformat()
                })
                
                return False
            
            target_waypoint = waypoints[flight_state.target_waypoint_index]
            
            # Calculate distance to target
            distance_to_target = self.calculate_distance(
                flight_state.current_lat, flight_state.current_lon,
                target_waypoint.latitude, target_waypoint.longitude
            )
            
            # Check if we've reached the waypoint (within 5 meters)
            if distance_to_target <= 5.0:
                self.logger.info(f"📍 Drone {drone.name} reached waypoint {target_waypoint.order}")
                
                # Mark waypoint as completed
                target_waypoint.mark_completed()
                
                # Move to next waypoint
                flight_state.current_waypoint_index = flight_state.target_waypoint_index
                flight_state.target_waypoint_index += 1
                
                # Update mission progress
                progress = (flight_state.current_waypoint_index / len(waypoints)) * 100
                mission.update_progress(progress, flight_state.current_waypoint_index)
                
                # Perform waypoint action
                if target_waypoint.action == "takeoff":
                    flight_state.battery_percentage -= self.takeoff_landing_rate
                    self.logger.info(f"🛫 Drone {drone.name} taking off")
                elif target_waypoint.action == "land":
                    flight_state.battery_percentage -= self.takeoff_landing_rate
                    flight_state.is_moving = False
                    self.logger.info(f"🛬 Drone {drone.name} landing")
                elif target_waypoint.action == "hover":
                    flight_state.is_moving = False
                    time.sleep(1)  # Brief hover simulation
                    flight_state.is_moving = True
                
            else:
                # Move towards target waypoint
                if flight_state.is_moving:
                    distance_to_move = flight_state.speed_mps * time_elapsed
                    
                    new_lat, new_lon = self.interpolate_position(
                        flight_state.current_lat, flight_state.current_lon,
                        target_waypoint.latitude, target_waypoint.longitude,
                        distance_to_move, distance_to_target
                    )
                    
                    flight_state.current_lat = new_lat
                    flight_state.current_lon = new_lon
                    flight_state.current_alt = target_waypoint.altitude
            
            # Update drone in database
            drone.latitude = flight_state.current_lat
            drone.longitude = flight_state.current_lon
            drone.altitude = flight_state.current_alt
            drone.battery_percentage = flight_state.battery_percentage
            drone.last_seen = now
            
            # Commit database changes
            self.db_session.commit()
            
            # Emit real-time updates
            self.emit_websocket_event('drone_status_update', {
                'drone_id': drone.id,
                'latitude': flight_state.current_lat,
                'longitude': flight_state.current_lon,
                'altitude': flight_state.current_alt,
                'battery_percentage': flight_state.battery_percentage,
                'status': drone.status.value,
                'last_seen': now.isoformat()
            })
            
            self.emit_websocket_event('mission_progress_update', {
                'mission_id': mission.id,
                'progress_percentage': mission.progress_percentage,
                'current_waypoint': flight_state.current_waypoint_index,
                'total_waypoints': len(waypoints),
                'drone_location': {
                    'latitude': flight_state.current_lat,
                    'longitude': flight_state.current_lon,
                    'altitude': flight_state.current_alt
                }
            })
            
            # Check for battery warnings
            if flight_state.battery_percentage <= 10.0:
                self.emit_websocket_event('battery_warning', {
                    'drone_id': drone.id,
                    'battery_percentage': flight_state.battery_percentage,
                    'warning_level': 'critical' if flight_state.battery_percentage <= 5.0 else 'low'
                })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating flight state: {e}")
            self.db_session.rollback()
            return False
    
    def simulation_loop(self) -> None:
        """Main simulation loop that updates all active flights."""
        self.logger.info("🚀 Starting simulation loop")
        
        while self.running:
            try:
                # Get currently active missions
                active_missions = self.get_active_missions()
                
                # Initialize new flights
                for mission in active_missions:
                    if mission.drone_id not in self.active_flights:
                        flight_state = self.initialize_flight_state(mission)
                        if flight_state:
                            self.active_flights[mission.drone_id] = flight_state
                
                # Update existing flights
                completed_flights = []
                for drone_id, flight_state in self.active_flights.items():
                    if not self.update_flight_state(flight_state):
                        completed_flights.append(drone_id)
                
                # Remove completed flights
                for drone_id in completed_flights:
                    del self.active_flights[drone_id]
                    self.logger.info(f"✅ Removed completed flight for drone {drone_id}")
                
                # Log status
                if self.active_flights:
                    self.logger.info(f"🔄 Simulating {len(self.active_flights)} active flights")
                
                # Wait before next update
                time.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                self.logger.info("⏹️ Simulation interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in simulation loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        self.logger.info("🛑 Simulation loop stopped")
    
    def start_simulation(self) -> None:
        """Start the drone simulation in a background thread."""
        if self.running:
            self.logger.warning("Simulation is already running")
            return
        
        self.running = True
        self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.simulation_thread.start()
        
        self.logger.info("🚁 Drone simulator started")
    
    def stop_simulation(self) -> None:
        """Stop the drone simulation."""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        
        self.logger.info("🛑 Drone simulator stopped")
    
    def get_simulation_status(self) -> Dict:
        """Get current simulation status and statistics.
        
        Returns:
            Dict: Status information
        """
        return {
            'running': self.running,
            'active_flights': len(self.active_flights),
            'flight_details': [
                {
                    'drone_id': fs.drone_id,
                    'mission_id': fs.mission_id,
                    'current_waypoint': fs.current_waypoint_index,
                    'battery_percentage': fs.battery_percentage,
                    'is_moving': fs.is_moving,
                    'emergency_landing': fs.emergency_landing
                }
                for fs in self.active_flights.values()
            ]
        }


def main():
    """Main entry point for the simulator."""
    parser = argparse.ArgumentParser(description='Drone Flight Simulator')
    parser.add_argument('--interval', type=float, default=2.0,
                       help='Update interval in seconds (default: 2.0)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--config', default='development',
                       help='Configuration environment (default: development)')
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize simulator
        simulator = DroneFlightSimulator(config_name=args.config)
        simulator.update_interval = args.interval
        
        # Start simulation
        simulator.start_simulation()
        
        print("🚁 Drone Flight Simulator Running")
        print("📊 Monitor the web interface to see real-time updates")
        print("⌨️  Press Ctrl+C to stop\n")
        
        # Keep main thread alive
        while simulator.running:
            status = simulator.get_simulation_status()
            print(f"📈 Active flights: {status['active_flights']}")
            
            for flight in status['flight_details']:
                print(f"   🚁 Drone {flight['drone_id']}: Mission {flight['mission_id']}, "
                      f"Waypoint {flight['current_waypoint']}, Battery {flight['battery_percentage']:.1f}%")
            
            time.sleep(10)  # Status update every 10 seconds
    
    except KeyboardInterrupt:
        print("\n⏹️ Stopping simulator...")
    except Exception as e:
        print(f"❌ Simulator error: {e}")
    finally:
        if 'simulator' in locals():
            simulator.stop_simulation()
        print("✅ Simulator stopped")


if __name__ == "__main__":
    main()