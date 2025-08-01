"""
WebSocket module for GRABIT backend.
Handles real-time progress broadcasting for downloads and operations.
"""

import asyncio
import json
import logging
import time
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from models import DownloadProgress, WebSocketMessage
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: Set[WebSocket] = set()
        self.task_subscribers: Dict[str, Set[WebSocket]] = {}
        self.connection_count = 0
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Start heartbeat task
        self._start_heartbeat()
    
    async def connect(self, websocket: WebSocket) -> bool:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            True if connection accepted, False if rejected
        """
        if len(self.active_connections) >= config.WS_MAX_CONNECTIONS:
            logger.warning("WebSocket connection rejected: max connections reached")
            return False
        
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_count += 1
        
        logger.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_message(websocket, WebSocketMessage(
            type="status",
            data={
                "message": "Connected to GRABIT WebSocket",
                "connection_id": id(websocket),
                "server_time": time.time()
            }
        ))
        
        return True
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # Remove from task subscriptions
            for task_id, subscribers in self.task_subscribers.items():
                subscribers.discard(websocket)
            
            logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")
    
    async def subscribe_to_task(self, websocket: WebSocket, task_id: str):
        """
        Subscribe a connection to task updates.
        
        Args:
            websocket: WebSocket connection
            task_id: Task ID to subscribe to
        """
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        
        self.task_subscribers[task_id].add(websocket)
        
        logger.debug(f"WebSocket subscribed to task {task_id}")
        
        # Send subscription confirmation
        await self.send_message(websocket, WebSocketMessage(
            type="subscription",
            task_id=task_id,
            data={"message": f"Subscribed to task {task_id}"}
        ))
    
    async def unsubscribe_from_task(self, websocket: WebSocket, task_id: str):
        """
        Unsubscribe a connection from task updates.
        
        Args:
            websocket: WebSocket connection
            task_id: Task ID to unsubscribe from
        """
        if task_id in self.task_subscribers:
            self.task_subscribers[task_id].discard(websocket)
            
            # Clean up empty subscriber sets
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
        
        logger.debug(f"WebSocket unsubscribed from task {task_id}")
    
    async def broadcast_progress(self, progress: DownloadProgress):
        """
        Broadcast progress update to subscribers.
        
        Args:
            progress: Progress update to broadcast
        """
        if not progress.task_id:
            return
        
        subscribers = self.task_subscribers.get(progress.task_id, set())
        if not subscribers:
            return
        
        message = WebSocketMessage(
            type="progress",
            task_id=progress.task_id,
            data=progress.dict()
        )
        
        # Send to all subscribers
        await self._broadcast_to_connections(subscribers, message)
        
        logger.debug(f"Broadcasted progress for task {progress.task_id} to {len(subscribers)} subscribers")
    
    async def broadcast_status(self, task_id: str, status: str, data: Dict[str, Any]):
        """
        Broadcast status update to subscribers.
        
        Args:
            task_id: Task ID
            status: Status message
            data: Additional data
        """
        subscribers = self.task_subscribers.get(task_id, set())
        if not subscribers:
            return
        
        message = WebSocketMessage(
            type="status",
            task_id=task_id,
            data={"status": status, **data}
        )
        
        await self._broadcast_to_connections(subscribers, message)
        
        logger.debug(f"Broadcasted status for task {task_id}: {status}")
    
    async def broadcast_error(self, task_id: str, error: str, error_type: str = "error"):
        """
        Broadcast error message to subscribers.
        
        Args:
            task_id: Task ID
            error: Error message
            error_type: Type of error
        """
        subscribers = self.task_subscribers.get(task_id, set())
        if not subscribers:
            return
        
        message = WebSocketMessage(
            type="error",
            task_id=task_id,
            data={
                "error": error,
                "error_type": error_type
            }
        )
        
        await self._broadcast_to_connections(subscribers, message)
        
        logger.debug(f"Broadcasted error for task {task_id}: {error}")
    
    async def broadcast_metadata(self, task_id: str, metadata: Dict[str, Any]):
        """
        Broadcast metadata to subscribers.
        
        Args:
            task_id: Task ID
            metadata: Metadata to broadcast
        """
        subscribers = self.task_subscribers.get(task_id, set())
        if not subscribers:
            return
        
        message = WebSocketMessage(
            type="metadata",
            task_id=task_id,
            data=metadata
        )
        
        await self._broadcast_to_connections(subscribers, message)
        
        logger.debug(f"Broadcasted metadata for task {task_id}")
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message to broadcast
        """
        await self._broadcast_to_connections(self.active_connections, message)
        
        logger.debug(f"Broadcasted message to all {len(self.active_connections)} connections")
    
    async def send_message(self, websocket: WebSocket, message: WebSocketMessage):
        """
        Send message to specific WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_text(message.json())
        except (WebSocketDisconnect, ConnectionClosed):
            # Connection is closed, remove it
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            self.disconnect(websocket)
    
    async def _broadcast_to_connections(self, connections: Set[WebSocket], message: WebSocketMessage):
        """Broadcast message to specific set of connections."""
        if not connections:
            return
        
        # Create tasks for parallel sending
        tasks = []
        for websocket in list(connections):  # Create copy to avoid modification during iteration
            tasks.append(self.send_message(websocket, message))
        
        # Send all messages concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def _start_heartbeat(self):
        """Start heartbeat task to keep connections alive."""
        async def heartbeat():
            while True:
                try:
                    await asyncio.sleep(config.WS_HEARTBEAT_INTERVAL)
                    
                    if self.active_connections:
                        heartbeat_message = WebSocketMessage(
                            type="heartbeat",
                            data={
                                "timestamp": time.time(),
                                "active_connections": len(self.active_connections)
                            }
                        )
                        
                        await self.broadcast_to_all(heartbeat_message)
                    
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
        
        self.heartbeat_task = asyncio.create_task(heartbeat())
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.connection_count,
            "active_tasks": len(self.task_subscribers),
            "max_connections": config.WS_MAX_CONNECTIONS
        }


# Global connection manager
_connection_manager = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


async def handle_websocket_connection(websocket: WebSocket):
    """
    Handle a new WebSocket connection.
    
    Args:
        websocket: WebSocket connection
    """
    manager = get_connection_manager()
    
    # Accept connection
    if not await manager.connect(websocket):
        await websocket.close(code=1008, reason="Server at capacity")
        return
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(websocket, message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket: {data}")
                await manager.send_message(websocket, WebSocketMessage(
                    type="error",
                    data={"error": "Invalid JSON format"}
                ))
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, message: Dict[str, Any]):
    """
    Handle message from WebSocket client.
    
    Args:
        websocket: WebSocket connection
        message: Message from client
    """
    manager = get_connection_manager()
    
    message_type = message.get('type')
    
    if message_type == "subscribe":
        task_id = message.get('task_id')
        if task_id:
            await manager.subscribe_to_task(websocket, task_id)
        else:
            await manager.send_message(websocket, WebSocketMessage(
                type="error",
                data={"error": "task_id required for subscription"}
            ))
    
    elif message_type == "unsubscribe":
        task_id = message.get('task_id')
        if task_id:
            await manager.unsubscribe_from_task(websocket, task_id)
        else:
            await manager.send_message(websocket, WebSocketMessage(
                type="error",
                data={"error": "task_id required for unsubscription"}
            ))
    
    elif message_type == "ping":
        await manager.send_message(websocket, WebSocketMessage(
            type="pong",
            data={"timestamp": time.time()}
        ))
    
    elif message_type == "stats":
        stats = manager.get_connection_stats()
        await manager.send_message(websocket, WebSocketMessage(
            type="stats",
            data=stats
        ))
    
    else:
        await manager.send_message(websocket, WebSocketMessage(
            type="error",
            data={"error": f"Unknown message type: {message_type}"}
        ))


# Convenience functions for broadcasting
async def broadcast_progress(progress: DownloadProgress):
    """Broadcast progress update."""
    manager = get_connection_manager()
    await manager.broadcast_progress(progress)


async def broadcast_status(task_id: str, status: str, data: Dict[str, Any] = None):
    """Broadcast status update."""
    manager = get_connection_manager()
    await manager.broadcast_status(task_id, status, data or {})


async def broadcast_error(task_id: str, error: str, error_type: str = "error"):
    """Broadcast error message."""
    manager = get_connection_manager()
    await manager.broadcast_error(task_id, error, error_type)


async def broadcast_metadata(task_id: str, metadata: Dict[str, Any]):
    """Broadcast metadata."""
    manager = get_connection_manager()
    await manager.broadcast_metadata(task_id, metadata)