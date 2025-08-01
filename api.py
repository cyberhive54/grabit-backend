"""
FastAPI application for GRABIT backend.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import logging

from models import (
    DownloadRequest, PlaylistRequest, BatchRequest, ThumbnailRequest, SubtitleRequest,
    DownloadResponse, ExtractResponse, TaskStatusResponse, ServerStatus, ErrorResponse
)
from config import get_config, validate_startup
from extract import extract_metadata
from download import start_single_download, start_playlist_download, start_batch_download, get_task_status, cancel_task
from websocket import handle_websocket_connection, get_connection_manager
from yt_process import get_processor

logger = logging.getLogger(__name__)
config = get_config()

# Initialize FastAPI app
app = FastAPI(
    title="GRABIT API",
    description="YouTube video downloader backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        validate_startup()
        logger.info("GRABIT backend started successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise e


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "GRABIT Backend API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "GRABIT"}


@app.post("/extract", response_model=ExtractResponse)
async def extract_video_metadata(url: str):
    """Extract video or playlist metadata."""
    try:
        result = await extract_metadata(url)
        return ExtractResponse(
            success=True,
            data=result.video_metadata or result.playlist_metadata,
            extraction_time=result.extraction_time
        )
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/download/single", response_model=DownloadResponse)
async def download_single_video(request: DownloadRequest):
    """Start single video download."""
    try:
        task_id = await start_single_download(request)
        return DownloadResponse(
            success=True,
            task_id=task_id,
            message="Download started successfully"
        )
    except Exception as e:
        logger.error(f"Single download failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/download/playlist", response_model=DownloadResponse)
async def download_playlist(request: PlaylistRequest):
    """Start playlist download."""
    try:
        task_id = await start_playlist_download(request)
        return DownloadResponse(
            success=True,
            task_id=task_id,
            message="Playlist download started successfully"
        )
    except Exception as e:
        logger.error(f"Playlist download failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/download/batch", response_model=DownloadResponse)
async def download_batch(request: BatchRequest):
    """Start batch download."""
    try:
        task_id = await start_batch_download(request)
        return DownloadResponse(
            success=True,
            task_id=task_id,
            message="Batch download started successfully"
        )
    except Exception as e:
        logger.error(f"Batch download failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_endpoint(task_id: str):
    """Get task status."""
    status = await get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(**status)


@app.delete("/task/{task_id}")
async def cancel_task_endpoint(task_id: str):
    """Cancel task."""
    success = await cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already completed")
    
    return {"message": "Task cancelled successfully"}


@app.post("/thumbnail")
async def download_thumbnail(request: ThumbnailRequest):
    """Download video thumbnail."""
    try:
        processor = get_processor()
        thumbnail_path = await processor.download_thumbnail(str(request.url), request.quality)
        return {"success": True, "thumbnail_path": thumbnail_path}
    except Exception as e:
        logger.error(f"Thumbnail download failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/subtitles")
async def download_subtitles(request: SubtitleRequest):
    """Download video subtitles."""
    try:
        processor = get_processor()
        subtitle_files = await processor.download_subtitles(
            str(request.url), request.languages, request.auto_generated
        )
        return {"success": True, "subtitle_files": subtitle_files}
    except Exception as e:
        logger.error(f"Subtitle download failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/status", response_model=ServerStatus)
async def get_server_status():
    """Get server status."""
    import time
    import psutil
    
    manager = get_connection_manager()
    stats = manager.get_connection_stats()
    
    return ServerStatus(
        version="1.0.0",
        active_downloads=stats.get("active_tasks", 0),
        total_downloads=0,  # TODO: Implement total counter
        uptime=time.time(),  # TODO: Track actual uptime
        memory_usage=psutil.virtual_memory().used / (1024 * 1024),
        max_concurrent_downloads=config.MAX_CONCURRENT_DOWNLOADS
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await handle_websocket_connection(websocket)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return ErrorResponse(
        error=str(exc),
        error_type=type(exc).__name__,
        message="An unexpected error occurred"
    )