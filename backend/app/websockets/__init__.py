"""
WebSocket handlers for real-time communication.

This package handles real-time updates for mission monitoring,
drone status changes, and fleet management via Socket.IO.
"""

from .mission_updates import register_websocket_handlers

__all__ = ['register_websocket_handlers']