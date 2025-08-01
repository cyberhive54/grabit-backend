"""
Download orchestration module for GRABIT backend.
Handles single video, playlist, and batch downloads with error isolation.
"""

import asyncio
import logging
import time
import uuid
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from models import (
    DownloadRequest, PlaylistRequest, BatchRequest, DownloadResult, 
    BatchResult, PlaylistResult, DownloadProgress, DownloadStatus,
    VideoMetadata, PlaylistMetadata
)
from config import get_config
from yt_process import get_processor
from websocket import broadcast_progress, broadcast_status, broadcast_error, broadcast_metadata

logger = logging.getLogger(__name__)
config = get_config()


class DownloadOrchestrator:
    """Orchestrates downloads and manages task lifecycle."""
    
    def __init__(self):
        """Initialize the download orchestrator."""
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Union[DownloadResult, BatchResult, PlaylistResult]] = {}
        self.processor = get_processor()
    
    async def start_single_download(self, request: DownloadRequest) -> str:
        """
        Start single video download.
        
        Args:
            request: Download request
            
        Returns:
            Task ID
        """
        task_id = self._generate_task_id("single")
        
        logger.info(f"Starting single download task {task_id}: {request.url}")
        
        # Create progress callback
        async def progress_callback(progress: DownloadProgress):
            progress.task_id = task_id
            await broadcast_progress(progress)
        
        # Create and start task
        task = asyncio.create_task(
            self._execute_single_download(task_id, request, progress_callback)
        )
        
        self.active_tasks[task_id] = task
        
        # Broadcast task start
        await broadcast_status(task_id, "started", {
            "url": str(request.url),
            "quality": request.quality,
            "type": "single_video"
        })
        
        return task_id
    
    async def start_playlist_download(self, request: PlaylistRequest) -> str:
        """
        Start playlist download.
        
        Args:
            request: Playlist request
            
        Returns:
            Task ID
        """
        task_id = self._generate_task_id("playlist")
        
        logger.info(f"Starting playlist download task {task_id}: {request.url}")
        
        # Create progress callback
        async def progress_callback(progress: DownloadProgress):
            progress.task_id = task_id
            await broadcast_progress(progress)
        
        # Create and start task
        task = asyncio.create_task(
            self._execute_playlist_download(task_id, request, progress_callback)
        )
        
        self.active_tasks[task_id] = task
        
        # Broadcast task start
        await broadcast_status(task_id, "started", {
            "url": str(request.url),
            "quality": request.quality,
            "type": "playlist"
        })
        
        return task_id
    
    async def start_batch_download(self, request: BatchRequest) -> str:
        """
        Start batch download.
        
        Args:
            request: Batch request
            
        Returns:
            Task ID
        """
        task_id = self._generate_task_id("batch")
        
        logger.info(f"Starting batch download task {task_id}: {len(request.urls)} videos")
        
        # Create progress callback
        async def progress_callback(progress: DownloadProgress):
            progress.task_id = task_id
            await broadcast_progress(progress)
        
        # Create and start task
        task = asyncio.create_task(
            self._execute_batch_download(task_id, request, progress_callback)
        )
        
        self.active_tasks[task_id] = task
        
        # Broadcast task start
        await broadcast_status(task_id, "started", {
            "urls": [str(url) for url in request.urls],
            "quality": request.quality,
            "type": "batch"
        })
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status dictionary or None if not found
        """
        # Check if task is active
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            
            return {
                "task_id": task_id,
                "status": "running" if not task.done() else "completed",
                "done": task.done(),
                "cancelled": task.cancelled()
            }
        
        # Check if task result is available
        if task_id in self.task_results:
            result = self.task_results[task_id]
            
            return {
                "task_id": task_id,
                "status": "completed",
                "done": True,
                "result": result.dict() if hasattr(result, 'dict') else result
            }
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            
            if not task.done():
                task.cancel()
                
                await broadcast_status(task_id, "cancelled", {
                    "message": "Task cancelled by user"
                })
                
                logger.info(f"Task {task_id} cancelled")
                return True
        
        return False
    
    async def cleanup_completed_tasks(self):
        """Clean up completed tasks to free memory."""
        completed_tasks = []
        
        for task_id, task in self.active_tasks.items():
            if task.done():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            del self.active_tasks[task_id]
        
        logger.debug(f"Cleaned up {len(completed_tasks)} completed tasks")
    
    async def _execute_single_download(self, task_id: str, request: DownloadRequest,
                                      progress_callback: callable) -> DownloadResult:
        """Execute single video download."""
        start_time = time.time()
        
        try:
            # Extract metadata first
            await broadcast_status(task_id, "extracting", {"message": "Extracting video metadata"})
            
            metadata = await self.processor.extract_metadata(str(request.url))
            
            if isinstance(metadata, VideoMetadata):
                await broadcast_metadata(task_id, metadata.dict())
            
            # Start download
            await broadcast_status(task_id, "downloading", {"message": "Starting download"})
            
            result = await self.processor.download_video(request, progress_callback)
            result.task_id = task_id
            
            # Store result
            self.task_results[task_id] = result
            
            # Broadcast completion
            if result.status == DownloadStatus.COMPLETED:
                await broadcast_status(task_id, "completed", {
                    "message": "Download completed successfully",
                    "file_path": result.video_file,
                    "file_size": result.filesize,
                    "download_time": result.download_time
                })
            else:
                await broadcast_error(task_id, result.error or "Download failed", result.error_type)
            
            logger.info(f"Single download task {task_id} completed: {result.status}")
            return result
            
        except Exception as e:
            logger.error(f"Single download task {task_id} failed: {e}")
            
            # Create failed result
            result = DownloadResult(
                task_id=task_id,
                status=DownloadStatus.FAILED,
                error=str(e),
                error_type=type(e).__name__,
                started_at=start_time,
                completed_at=time.time()
            )
            
            self.task_results[task_id] = result
            await broadcast_error(task_id, str(e), type(e).__name__)
            
            return result
    
    async def _execute_playlist_download(self, task_id: str, request: PlaylistRequest,
                                        progress_callback: callable) -> PlaylistResult:
        """Execute playlist download."""
        start_time = time.time()
        
        try:
            # Extract playlist metadata
            await broadcast_status(task_id, "extracting", {"message": "Extracting playlist metadata"})
            
            playlist_metadata = await self.processor.extract_metadata(str(request.url))
            
            if not isinstance(playlist_metadata, PlaylistMetadata):
                raise ValueError("URL is not a valid playlist")
            
            await broadcast_metadata(task_id, playlist_metadata.dict())
            
            # Determine videos to download
            videos_to_download = self._select_playlist_videos(playlist_metadata, request)
            
            await broadcast_status(task_id, "downloading", {
                "message": f"Starting download of {len(videos_to_download)} videos",
                "total_videos": len(videos_to_download)
            })
            
            # Download videos with error isolation
            results = await self._download_videos_with_isolation(
                videos_to_download, request, progress_callback, task_id
            )
            
            # Create playlist result
            successful_results = [r for r in results if r.status == DownloadStatus.COMPLETED]
            failed_results = [r for r in results if r.status != DownloadStatus.COMPLETED]
            
            playlist_result = PlaylistResult(
                playlist_id=task_id,
                playlist_metadata=playlist_metadata,
                total_videos=len(videos_to_download),
                successful_downloads=len(successful_results),
                failed_downloads=len(failed_results),
                results=results,
                total_filesize=sum(r.filesize or 0 for r in successful_results),
                total_download_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time()
            )
            
            self.task_results[task_id] = playlist_result
            
            # Broadcast completion
            await broadcast_status(task_id, "completed", {
                "message": "Playlist download completed",
                "successful": len(successful_results),
                "failed": len(failed_results),
                "total_size": playlist_result.total_filesize
            })
            
            logger.info(f"Playlist download task {task_id} completed: {len(successful_results)}/{len(videos_to_download)} successful")
            return playlist_result
            
        except Exception as e:
            logger.error(f"Playlist download task {task_id} failed: {e}")
            
            # Create failed result
            playlist_result = PlaylistResult(
                playlist_id=task_id,
                total_videos=0,
                successful_downloads=0,
                failed_downloads=0,
                results=[],
                started_at=start_time,
                completed_at=time.time()
            )
            
            self.task_results[task_id] = playlist_result
            await broadcast_error(task_id, str(e), type(e).__name__)
            
            return playlist_result
    
    async def _execute_batch_download(self, task_id: str, request: BatchRequest,
                                     progress_callback: callable) -> BatchResult:
        """Execute batch download."""
        start_time = time.time()
        
        try:
            urls = [str(url) for url in request.urls]
            
            await broadcast_status(task_id, "downloading", {
                "message": f"Starting batch download of {len(urls)} videos",
                "total_videos": len(urls)
            })
            
            # Create individual download requests
            video_requests = []
            for url in urls:
                video_request = DownloadRequest(
                    url=url,
                    quality=request.quality,
                    format=request.format,
                    include_audio=request.include_audio,
                    include_subtitles=request.include_subtitles,
                    subtitle_languages=request.subtitle_languages,
                    download_thumbnail=request.download_thumbnail
                )
                video_requests.append(video_request)
            
            # Download videos with error isolation
            results = await self._download_requests_with_isolation(
                video_requests, progress_callback, task_id, request.max_concurrent
            )
            
            # Create batch result
            successful_results = [r for r in results if r.status == DownloadStatus.COMPLETED]
            failed_results = [r for r in results if r.status != DownloadStatus.COMPLETED]
            
            batch_result = BatchResult(
                batch_id=task_id,
                total_videos=len(urls),
                successful_downloads=len(successful_results),
                failed_downloads=len(failed_results),
                results=results,
                total_filesize=sum(r.filesize or 0 for r in successful_results),
                total_download_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time()
            )
            
            self.task_results[task_id] = batch_result
            
            # Broadcast completion
            await broadcast_status(task_id, "completed", {
                "message": "Batch download completed",
                "successful": len(successful_results),
                "failed": len(failed_results),
                "total_size": batch_result.total_filesize
            })
            
            logger.info(f"Batch download task {task_id} completed: {len(successful_results)}/{len(urls)} successful")
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch download task {task_id} failed: {e}")
            
            # Create failed result
            batch_result = BatchResult(
                batch_id=task_id,
                total_videos=len(request.urls),
                successful_downloads=0,
                failed_downloads=0,
                results=[],
                started_at=start_time,
                completed_at=time.time()
            )
            
            self.task_results[task_id] = batch_result
            await broadcast_error(task_id, str(e), type(e).__name__)
            
            return batch_result
    
    def _select_playlist_videos(self, playlist: PlaylistMetadata, request: PlaylistRequest) -> List[VideoMetadata]:
        """Select videos from playlist based on request parameters."""
        videos = playlist.videos
        
        if request.download_all:
            selected_videos = videos
        else:
            selected_videos = []
            for index in request.selected_videos:
                if 0 <= index < len(videos):
                    selected_videos.append(videos[index])
        
        # Apply filters
        if request.start_index is not None:
            start_idx = max(0, request.start_index)
            selected_videos = selected_videos[start_idx:]
        
        if request.end_index is not None:
            end_idx = min(len(selected_videos), request.end_index + 1)
            selected_videos = selected_videos[:end_idx]
        
        if request.max_downloads is not None:
            selected_videos = selected_videos[:request.max_downloads]
        
        return selected_videos
    
    async def _download_videos_with_isolation(self, videos: List[VideoMetadata], 
                                             request: PlaylistRequest, progress_callback: callable,
                                             task_id: str) -> List[DownloadResult]:
        """Download videos with error isolation."""
        # Create download requests
        video_requests = []
        for video in videos:
            video_request = DownloadRequest(
                url=video.webpage_url,
                quality=request.quality,
                format=request.format,
                include_audio=request.include_audio,
                include_subtitles=request.include_subtitles,
                subtitle_languages=request.subtitle_languages,
                download_thumbnail=request.download_thumbnail
            )
            video_requests.append(video_request)
        
        return await self._download_requests_with_isolation(
            video_requests, progress_callback, task_id
        )
    
    async def _download_requests_with_isolation(self, requests: List[DownloadRequest],
                                               progress_callback: callable, task_id: str,
                                               max_concurrent: Optional[int] = None) -> List[DownloadResult]:
        """Download requests with error isolation and concurrency control."""
        max_concurrent = max_concurrent or config.MAX_CONCURRENT_DOWNLOADS
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(request: DownloadRequest, index: int) -> DownloadResult:
            async with semaphore:
                try:
                    return await self.processor.download_video(request, progress_callback)
                except Exception as e:
                    logger.error(f"Download failed for video {index}: {e}")
                    return DownloadResult(
                        task_id=f"{task_id}_video_{index}",
                        status=DownloadStatus.FAILED,
                        error=str(e),
                        error_type=type(e).__name__,
                        started_at=time.time(),
                        completed_at=time.time()
                    )
        
        # Create tasks
        tasks = [
            download_with_semaphore(request, i) 
            for i, request in enumerate(requests)
        ]
        
        # Execute with progress tracking
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results.append(result)
            
            # Update overall progress
            progress_percentage = ((i + 1) / len(tasks)) * 100
            await broadcast_status(task_id, "downloading", {
                "message": f"Downloaded {i + 1}/{len(tasks)} videos",
                "progress": progress_percentage
            })
        
        return results
    
    def _generate_task_id(self, prefix: str) -> str:
        """Generate unique task ID."""
        return f"{prefix}_{uuid.uuid4().hex[:8]}_{int(time.time())}"


# Global orchestrator instance
_orchestrator = None


def get_orchestrator() -> DownloadOrchestrator:
    """Get the global download orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DownloadOrchestrator()
    return _orchestrator


# Convenience functions
async def start_single_download(request: DownloadRequest) -> str:
    """Start single video download."""
    orchestrator = get_orchestrator()
    return await orchestrator.start_single_download(request)


async def start_playlist_download(request: PlaylistRequest) -> str:
    """Start playlist download."""
    orchestrator = get_orchestrator()
    return await orchestrator.start_playlist_download(request)


async def start_batch_download(request: BatchRequest) -> str:
    """Start batch download."""
    orchestrator = get_orchestrator()
    return await orchestrator.start_batch_download(request)


async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status."""
    orchestrator = get_orchestrator()
    return await orchestrator.get_task_status(task_id)


async def cancel_task(task_id: str) -> bool:
    """Cancel task."""
    orchestrator = get_orchestrator()
    return await orchestrator.cancel_task(task_id)