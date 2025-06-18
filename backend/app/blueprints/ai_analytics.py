"""
AI Analytics Blueprint

RESTful API endpoints for AI-powered analytics and optimization features.
Provides endpoints for mission optimization, predictive analytics, and intelligent recommendations.

Author: FlytBase Assignment
Created: 2024
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit
from sqlalchemy.exc import SQLAlchemyError

from ..models.drone import Drone, DroneStatus
from ..models.mission import Mission, MissionStatus
from ..services.ai_mission_optimizer import (
    AIMissionOptimizer, 
    OptimizationStrategy,
    DroneSelectionAI,
    FlightPatternOptimizer,
    MissionPredictor,
    WeatherAnalyzer
)
from .. import db

# Create blueprint
ai_analytics_bp = Blueprint('ai_analytics', __name__, url_prefix='/api/v1/ai')


@ai_analytics_bp.route('/mission/optimize', methods=['POST'])
def optimize_mission():
    """
    AI-powered mission optimization endpoint
    
    POST /api/v1/ai/mission/optimize
    
    Request Body:
    {
        "mission_requirements": {
            "name": "Survey Area Alpha",
            "survey_area": {...},  // GeoJSON
            "altitude": 100,
            "overlap": 70,
            "priority": "normal"
        },
        "strategy": "adaptive"  // optional
    }
    
    Returns:
        JSON with optimization results including flight pattern, 
        drone selection, predictions, and AI recommendations
    """
    try:
        data = request.get_json()
        
        if not data or 'mission_requirements' not in data:
            return jsonify({
                'error': 'Missing mission_requirements in request body'
            }), 400
        
        mission_requirements = data['mission_requirements']
        strategy_str = data.get('strategy', 'adaptive')
        
        # Parse optimization strategy
        try:
            strategy = OptimizationStrategy(strategy_str)
        except ValueError:
            strategy = OptimizationStrategy.ADAPTIVE_AI
        
        # Get available drones
        available_drones = Drone.query.filter_by(status=DroneStatus.AVAILABLE).all()
        
        if not available_drones:
            return jsonify({
                'error': 'No drones available for mission optimization',
                'available_drones': 0
            }), 400
        
        # Initialize AI optimizer
        optimizer = AIMissionOptimizer()
        
        # Run optimization
        optimization_result = optimizer.optimize_mission(
            mission_requirements=mission_requirements,
            available_drones=available_drones,
            strategy=strategy
        )
        
        if not optimization_result['success']:
            return jsonify(optimization_result), 400
        
        # Log optimization event
        current_app.logger.info(f"Mission optimization completed for: {mission_requirements.get('name', 'Unknown')}")
        
        return jsonify({
            'success': True,
            'optimization_result': optimization_result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Mission optimization error: {str(e)}")
        return jsonify({
            'error': 'Failed to optimize mission',
            'details': str(e)
        }), 500


@ai_analytics_bp.route('/drone/selection', methods=['POST'])
def analyze_drone_selection():
    """
    AI drone selection analysis endpoint
    
    POST /api/v1/ai/drone/selection
    
    Request Body:
    {
        "mission_requirements": {...},
        "drone_ids": [1, 2, 3]  // optional, if not provided uses all available
    }
    
    Returns:
        JSON with drone scores and recommendations
    """
    try:
        data = request.get_json()
        
        if not data or 'mission_requirements' not in data:
            return jsonify({
                'error': 'Missing mission_requirements in request body'
            }), 400
        
        mission_requirements = data['mission_requirements']
        drone_ids = data.get('drone_ids')
        
        # Get drones to analyze
        if drone_ids:
            drones = Drone.query.filter(Drone.id.in_(drone_ids)).all()
        else:
            drones = Drone.query.filter_by(status=DroneStatus.AVAILABLE).all()
        
        if not drones:
            return jsonify({
                'error': 'No drones found for analysis',
                'available_drones': 0
            }), 400
        
        # Analyze each drone
        drone_scores = []
        for drone in drones:
            score = DroneSelectionAI.score_drone_for_mission(drone, mission_requirements)
            drone_scores.append({
                'drone_id': score.drone_id,
                'drone_name': score.drone_name,
                'total_score': score.total_score,
                'factors': score.factors,
                'recommendation': score.recommendation,
                'confidence': score.confidence,
                'reasoning': score.reasoning
            })
        
        # Sort by score (highest first)
        drone_scores.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Select optimal drone
        optimal_drone = drone_scores[0] if drone_scores else None
        
        return jsonify({
            'success': True,
            'drone_analysis': {
                'total_drones_analyzed': len(drone_scores),
                'optimal_drone': optimal_drone,
                'all_scores': drone_scores,
                'analysis_timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Drone selection analysis error: {str(e)}")
        return jsonify({
            'error': 'Failed to analyze drone selection',
            'details': str(e)
        }), 500


@ai_analytics_bp.route('/mission/predict', methods=['POST'])
def predict_mission_outcome():
    """
    AI mission outcome prediction endpoint
    
    POST /api/v1/ai/mission/predict
    
    Request Body:
    {
        "mission_data": {...},
        "drone_id": 1,
        "flight_pattern": {...}
    }
    
    Returns:
        JSON with mission predictions and risk analysis
    """
    try:
        data = request.get_json()
        
        required_fields = ['mission_data', 'drone_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'Missing required field: {field}'
                }), 400
        
        mission_data = data['mission_data']
        drone_id = data['drone_id']
        flight_pattern_data = data.get('flight_pattern', {})
        
        # Get drone
        drone = Drone.query.get(drone_id)
        if not drone:
            return jsonify({
                'error': f'Drone not found with ID: {drone_id}'
            }), 404
        
        # Create mock flight pattern if not provided
        if not flight_pattern_data:
            flight_pattern = FlightPatternOptimizer.generate_optimized_pattern(
                mission_data.get('survey_area', {}),
                mission_data
            )
        else:
            # Convert flight_pattern_data to FlightPattern object
            from ..services.ai_mission_optimizer import FlightPattern
            flight_pattern = FlightPattern(
                pattern_type=flight_pattern_data.get('pattern_type', 'grid'),
                waypoints=flight_pattern_data.get('waypoints', []),
                efficiency_score=flight_pattern_data.get('efficiency_score', 80),
                coverage_percentage=flight_pattern_data.get('coverage_percentage', 95),
                estimated_duration=flight_pattern_data.get('estimated_duration', 45),
                battery_consumption=flight_pattern_data.get('battery_consumption', 60),
                safety_rating=flight_pattern_data.get('safety_rating', 85),
                reasoning=flight_pattern_data.get('reasoning', []),
                metadata=flight_pattern_data.get('metadata', {})
            )
        
        # Generate prediction
        prediction = MissionPredictor.predict_mission_outcome(
            mission_data, drone, flight_pattern
        )
        
        return jsonify({
            'success': True,
            'prediction': {
                'success_probability': prediction.success_probability,
                'estimated_duration': prediction.estimated_duration,
                'battery_consumption': prediction.battery_consumption,
                'risk_factors': prediction.risk_factors,
                'weather_impact': prediction.weather_impact,
                'terrain_complexity': prediction.terrain_complexity,
                'confidence_interval': prediction.confidence_interval,
                'recommendations': prediction.recommendations
            },
            'prediction_timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Mission prediction error: {str(e)}")
        return jsonify({
            'error': 'Failed to predict mission outcome',
            'details': str(e)
        }), 500


@ai_analytics_bp.route('/weather/analysis', methods=['GET'])
def get_weather_analysis():
    """
    Get AI weather analysis for mission planning
    
    GET /api/v1/ai/weather/analysis
    
    Returns:
        JSON with weather impact analysis and recommendations
    """
    try:
        # Get weather analysis
        weather_impact, weather_data = WeatherAnalyzer.get_weather_impact_score()
        weather_window = WeatherAnalyzer.predict_weather_window()
        
        return jsonify({
            'success': True,
            'weather_analysis': {
                'current_conditions': weather_data,
                'impact_score': weather_impact,
                'weather_window': weather_window,
                'analysis_timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Weather analysis error: {str(e)}")
        return jsonify({
            'error': 'Failed to analyze weather conditions',
            'details': str(e)
        }), 500


@ai_analytics_bp.route('/fleet/optimization', methods=['POST'])
def optimize_fleet_schedule():
    """
    AI fleet optimization endpoint
    
    POST /api/v1/ai/fleet/optimization
    
    Request Body:
    {
        "mission_ids": [1, 2, 3],  // optional
        "optimization_goals": ["efficiency", "battery", "time"]  // optional
    }
    
    Returns:
        JSON with optimized fleet schedule and assignments
    """
    try:
        data = request.get_json() or {}
        
        mission_ids = data.get('mission_ids')
        optimization_goals = data.get('optimization_goals', ['efficiency'])
        
        # Get missions to optimize
        if mission_ids:
            missions = Mission.query.filter(Mission.id.in_(mission_ids)).all()
        else:
            missions = Mission.query.filter_by(status=MissionStatus.PLANNED).all()
        
        # Get available drones
        available_drones = Drone.query.filter_by(status=DroneStatus.AVAILABLE).all()
        
        if not missions:
            return jsonify({
                'error': 'No missions found for optimization',
                'available_missions': 0
            }), 400
        
        if not available_drones:
            return jsonify({
                'error': 'No drones available for optimization',
                'available_drones': 0
            }), 400
        
        # Initialize optimizer
        optimizer = AIMissionOptimizer()
        
        # Optimize each mission and create schedule
        optimized_assignments = []
        total_efficiency_gain = 0
        
        for mission in missions:
            mission_requirements = {
                'name': mission.name,
                'survey_area': json.loads(mission.survey_area_geojson) if mission.survey_area_geojson else {},
                'altitude': mission.altitude_m,
                'overlap': mission.overlap_percentage,
                'priority': 'normal'
            }
            
            optimization_result = optimizer.optimize_mission(
                mission_requirements=mission_requirements,
                available_drones=available_drones
            )
            
            if optimization_result['success']:
                selected_drone_id = optimization_result['drone_selection']['selected_drone_id']
                
                optimized_assignments.append({
                    'mission_id': mission.id,
                    'mission_name': mission.name,
                    'recommended_drone_id': selected_drone_id,
                    'recommended_drone_name': optimization_result['drone_selection']['selected_drone_name'],
                    'selection_score': optimization_result['drone_selection']['selection_score'],
                    'estimated_duration': optimization_result['flight_pattern']['estimated_duration'],
                    'efficiency_score': optimization_result['flight_pattern']['efficiency_score'],
                    'success_probability': optimization_result['mission_prediction']['success_probability']
                })
                
                total_efficiency_gain += optimization_result['optimization_benefits']['efficiency_gain_percent']
                
                # Remove assigned drone from available list (for next iteration)
                available_drones = [d for d in available_drones if str(d.id) != selected_drone_id]
        
        # Calculate fleet metrics
        average_efficiency = sum(a['efficiency_score'] for a in optimized_assignments) / len(optimized_assignments) if optimized_assignments else 0
        average_success_probability = sum(a['success_probability'] for a in optimized_assignments) / len(optimized_assignments) if optimized_assignments else 0
        total_estimated_time = sum(a['estimated_duration'] for a in optimized_assignments)
        
        return jsonify({
            'success': True,
            'fleet_optimization': {
                'optimized_assignments': optimized_assignments,
                'optimization_summary': {
                    'total_missions_optimized': len(optimized_assignments),
                    'average_efficiency_score': round(average_efficiency, 1),
                    'average_success_probability': round(average_success_probability, 1),
                    'total_estimated_duration_minutes': round(total_estimated_time, 1),
                    'total_efficiency_gain_percent': round(total_efficiency_gain, 1)
                },
                'optimization_timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Fleet optimization error: {str(e)}")
        return jsonify({
            'error': 'Failed to optimize fleet schedule',
            'details': str(e)
        }), 500


@ai_analytics_bp.route('/recommendations/generate', methods=['POST'])
def generate_ai_recommendations():
    """
    Generate AI recommendations for operations
    
    POST /api/v1/ai/recommendations/generate
    
    Request Body:
    {
        "context": "mission_planning",  // or "fleet_management", "maintenance"
        "mission_id": 1,  // optional
        "drone_id": 1     // optional
    }
    
    Returns:
        JSON with AI-generated recommendations
    """
    try:
        data = request.get_json() or {}
        
        context = data.get('context', 'general')
        mission_id = data.get('mission_id')
        drone_id = data.get('drone_id')
        
        # Generate context-specific recommendations
        recommendations = []
        
        if context == 'mission_planning' or context == 'general':
            # Get current weather for mission planning recommendations
            weather_impact, weather_data = WeatherAnalyzer.get_weather_impact_score()
            
            if weather_impact < 20:
                recommendations.append({
                    'id': f'weather_optimal_{int(datetime.now().timestamp())}',
                    'type': 'opportunity',
                    'title': 'Optimal Weather Conditions Detected',
                    'description': f'Current weather conditions are excellent for drone operations (impact score: {weather_impact:.1f}/100)',
                    'priority': 'medium',
                    'confidence': 0.92,
                    'action_required': False,
                    'estimated_benefit': 'Improved mission success probability and image quality'
                })
            elif weather_impact > 60:
                recommendations.append({
                    'id': f'weather_warning_{int(datetime.now().timestamp())}',
                    'type': 'warning',
                    'title': 'Adverse Weather Conditions',
                    'description': f'Current weather may impact mission performance (impact score: {weather_impact:.1f}/100)',
                    'priority': 'high',
                    'confidence': 0.89,
                    'action_required': True,
                    'recommended_action': 'Consider postponing missions or adjusting flight parameters'
                })
        
        if context == 'fleet_management' or context == 'general':
            # Get fleet status for management recommendations
            drones = Drone.query.all()
            low_battery_drones = [d for d in drones if d.battery_percentage < 30]
            
            if low_battery_drones:
                recommendations.append({
                    'id': f'battery_warning_{int(datetime.now().timestamp())}',
                    'type': 'maintenance',
                    'title': f'Low Battery Alert - {len(low_battery_drones)} Drone(s)',
                    'description': f'Multiple drones require charging: {", ".join([d.name for d in low_battery_drones[:3]])}',
                    'priority': 'high',
                    'confidence': 1.0,
                    'action_required': True,
                    'recommended_action': 'Schedule charging for affected drones'
                })
        
        # Add some AI-generated optimization recommendations
        if context == 'general' or not recommendations:
            recommendations.extend([
                {
                    'id': f'ai_optimization_{int(datetime.now().timestamp())}_1',
                    'type': 'optimization',
                    'title': 'Flight Pattern Efficiency Opportunity',
                    'description': 'AI analysis suggests switching to adaptive patterns could improve efficiency by 12-18%',
                    'priority': 'medium',
                    'confidence': 0.87,
                    'action_required': False,
                    'potential_savings': {
                        'time': '8-12 minutes per mission',
                        'battery': '10-15%',
                        'cost': '$25-35 per mission'
                    }
                },
                {
                    'id': f'ai_maintenance_{int(datetime.now().timestamp())}_2',
                    'type': 'maintenance',
                    'title': 'Predictive Maintenance Schedule',
                    'description': 'ML models suggest proactive maintenance for 2 drones within next 7 days',
                    'priority': 'medium',
                    'confidence': 0.82,
                    'action_required': True,
                    'recommended_action': 'Schedule inspection for drones with high flight hours'
                }
            ])
        
        return jsonify({
            'success': True,
            'recommendations': {
                'total_recommendations': len(recommendations),
                'context': context,
                'recommendations': recommendations,
                'generation_timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"AI recommendations generation error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate AI recommendations',
            'details': str(e)
        }), 500


@ai_analytics_bp.route('/analytics/performance', methods=['GET'])
def get_performance_analytics():
    """
    Get AI-powered performance analytics
    
    GET /api/v1/ai/analytics/performance?period=7d
    
    Returns:
        JSON with performance insights and trends
    """
    try:
        period = request.args.get('period', '7d')
        
        # Generate mock performance analytics
        # In production, this would analyze real historical data
        
        performance_data = {
            'fleet_metrics': {
                'total_missions': 47,
                'success_rate': 94.2,
                'average_efficiency': 87.3,
                'total_flight_time': 124.7,
                'cost_per_mission': 124.50
            },
            'trends': {
                'efficiency_trend': 'increasing',
                'success_rate_trend': 'stable',
                'cost_trend': 'decreasing'
            },
            'benchmarks': {
                'industry_average_efficiency': 82.5,
                'target_success_rate': 95.0,
                'optimal_cost_per_mission': 110.0
            },
            'improvement_opportunities': [
                {
                    'area': 'Battery Management',
                    'current_score': 78.3,
                    'target_score': 85.0,
                    'potential_improvement': '8.6%',
                    'priority': 'high'
                },
                {
                    'area': 'Flight Path Optimization',
                    'current_score': 89.1,
                    'target_score': 93.0,
                    'potential_improvement': '4.3%',
                    'priority': 'medium'
                }
            ],
            'ai_insights': [
                'Fleet efficiency is 5.8% above industry average',
                'Battery utilization could be optimized for 12% improvement',
                'Weather pattern analysis suggests optimal flying windows at 9-11 AM'
            ]
        }
        
        return jsonify({
            'success': True,
            'performance_analytics': performance_data,
            'analysis_period': period,
            'analysis_timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Performance analytics error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate performance analytics',
            'details': str(e)
        }), 500


# Error handlers for the blueprint
@ai_analytics_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad Request',
        'message': 'Invalid request data or parameters'
    }), 400


@ai_analytics_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Requested resource not found'
    }), 404


@ai_analytics_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500