#!/usr/bin/env python3
"""
Demo Setup Script for Drone Survey Management System.

This script creates sample missions and starts them to demonstrate
the real-time monitoring capabilities with the simulator.

Usage:
    python demo_setup.py

Author: FlytBase Assignment
Created: 2024
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_config
from app.models import db, Drone, Mission, Waypoint, MissionStatus, DroneStatus
from app.services.waypoint_generator import WaypointGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_demo_mission(session, drone_id: int, name: str, area_coords: list) -> Mission:
    """Create a demo mission with waypoints.
    
    Args:
        session: Database session
        drone_id: ID of drone to assign
        name: Mission name
        area_coords: Survey area coordinates
        
    Returns:
        Mission: Created mission
    """
    # Create GeoJSON for survey area
    survey_area_geojson = json.dumps({
        "type": "Polygon",
        "coordinates": [area_coords]
    })
    
    # Create mission
    mission = Mission(
        name=name,
        survey_area_geojson=survey_area_geojson,
        altitude_m=120.0,
        overlap_percentage=70.0,
        pattern_type="crosshatch",
        estimated_duration_minutes=25,
        drone_id=drone_id
    )
    
    session.add(mission)
    session.flush()  # Get mission ID
    
    # Generate waypoints using the waypoint generator
    generator = WaypointGenerator()
    try:
        waypoint_data = generator.generate_waypoints(
            survey_area_geojson, 120.0, 70.0, "crosshatch"
        )
        
        # Create waypoint objects
        for wp_data in waypoint_data:
            waypoint = Waypoint(
                mission_id=mission.id,
                latitude=wp_data.latitude,
                longitude=wp_data.longitude,
                altitude=wp_data.altitude,
                order=wp_data.order,
                action=wp_data.action,
                estimated_time_seconds=wp_data.estimated_time_seconds
            )
            session.add(waypoint)
    
    except Exception as e:
        print(f"Warning: Could not generate waypoints automatically: {e}")
        # Create simple manual waypoints as fallback
        simple_waypoints = [
            # Takeoff
            (area_coords[0][1], area_coords[0][0], 120.0, 0, "takeoff"),
            # Survey points
            (area_coords[0][1], area_coords[0][0], 120.0, 1, "capture"),
            (area_coords[1][1], area_coords[1][0], 120.0, 2, "capture"),
            (area_coords[2][1], area_coords[2][0], 120.0, 3, "capture"),
            (area_coords[3][1], area_coords[3][0], 120.0, 4, "capture"),
            # Landing
            (area_coords[0][1], area_coords[0][0], 0.0, 5, "land")
        ]
        
        for lat, lon, alt, order, action in simple_waypoints:
            waypoint = Waypoint(
                mission_id=mission.id,
                latitude=lat,
                longitude=lon,
                altitude=alt,
                order=order,
                action=action
            )
            session.add(waypoint)
    
    return mission


def setup_demo_data():
    """Set up demo data for real-time monitoring demonstration."""
    print("🚁 Setting up demo data for Drone Survey Management System")
    
    # Setup database connection
    config = get_config('development')()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Ensure we have available drones
        available_drones = session.query(Drone).filter_by(status=DroneStatus.AVAILABLE).all()
        
        if len(available_drones) < 2:
            print("❌ Need at least 2 available drones for demo. Creating additional drones...")
            
            # Create additional demo drones if needed
            demo_drones = [
                {
                    'name': 'DemoFlyer-001',
                    'model': 'DJI Mavic Pro',
                    'battery_percentage': 95.0,
                    'latitude': 37.7849,
                    'longitude': -122.4094
                },
                {
                    'name': 'DemoFlyer-002', 
                    'model': 'DJI Phantom 4',
                    'battery_percentage': 88.0,
                    'latitude': 37.7949,
                    'longitude': -122.4194
                }
            ]
            
            for drone_data in demo_drones:
                existing = session.query(Drone).filter_by(name=drone_data['name']).first()
                if not existing:
                    drone = Drone(**drone_data)
                    session.add(drone)
            
            session.commit()
            available_drones = session.query(Drone).filter_by(status=DroneStatus.AVAILABLE).all()
        
        # Create demo missions
        print("📋 Creating demo missions...")
        
        # Mission 1: Golden Gate Park Survey
        mission1_area = [
            [-122.4694, 37.7694],  # SW corner
            [-122.4594, 37.7694],  # SE corner 
            [-122.4594, 37.7794],  # NE corner
            [-122.4694, 37.7794],  # NW corner
            [-122.4694, 37.7694]   # Close polygon
        ]
        
        mission1 = create_demo_mission(
            session, 
            available_drones[0].id,
            "Golden Gate Park Survey Demo",
            mission1_area
        )
        
        # Mission 2: Marina District Survey  
        mission2_area = [
            [-122.4594, 37.7994],  # SW corner
            [-122.4494, 37.7994],  # SE corner
            [-122.4494, 37.8094],  # NE corner
            [-122.4594, 37.8094],  # NW corner
            [-122.4594, 37.7994]   # Close polygon
        ]
        
        mission2 = create_demo_mission(
            session,
            available_drones[1].id if len(available_drones) > 1 else available_drones[0].id,
            "Marina District Survey Demo", 
            mission2_area
        )
        
        session.commit()
        
        print(f"✅ Created demo missions:")
        print(f"   🎯 Mission 1: {mission1.name} (Drone: {available_drones[0].name})")
        print(f"   🎯 Mission 2: {mission2.name} (Drone: {available_drones[1].name if len(available_drones) > 1 else available_drones[0].name})")
        
        # Start the missions
        print("\n🚀 Starting demo missions...")
        
        mission1.start_mission()
        time.sleep(1)  # Small delay
        mission2.start_mission()
        
        session.commit()
        
        print("✅ Demo missions started!")
        print("\n📊 Demo Setup Complete!")
        print("=" * 50)
        print("🎬 Your demo environment is ready with:")
        print(f"   • {len(available_drones)} active drones")
        print(f"   • 2 running missions with waypoints") 
        print(f"   • Real-time monitoring capabilities")
        print("\n🚀 Next Steps:")
        print("   1. Start the Flask application: python run.py")
        print("   2. Start the simulator: python simulator.py")
        print("   3. Open the frontend to see live updates")
        print("\n📡 WebSocket Events Being Generated:")
        print("   • drone_status_update (GPS, battery, status)")
        print("   • mission_progress_update (waypoint progress)")
        print("   • battery_warning (when battery gets low)")
        print("   • mission_completed (when missions finish)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up demo data: {e}")
        session.rollback()
        return False
        
    finally:
        session.close()


def main():
    """Main entry point."""
    try:
        success = setup_demo_data()
        if success:
            print("\n🎉 Demo setup completed successfully!")
            print("Run the following commands in separate terminals:")
            print("   Terminal 1: python run.py")
            print("   Terminal 2: python simulator.py --verbose")
        else:
            print("\n❌ Demo setup failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Demo setup interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()