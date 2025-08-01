"""
PyTube handler for GRABIT backend.
"""

import asyncio
import logging
import time
import os
from typing import List, Optional, Dict, Callable
from pathlib import Path
import pytube
from pytube import YouTube, Stream

from models import DownloadRequest, DownloadResult, QualityFormat, VideoMetadata, DownloadProgress, DownloadStatus
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class PytubeHandler:
    """Handles video downloads using pytube for streams ≤720p."""
    
    def __init__(self):
        self.download_path = config.DEFAULT_DOWNLOAD_PATH
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
    
    async def download_video(self, request: DownloadRequest, progress_callback: Optional[Callable] = None) -> DownloadResult:
        """Download video using pytube."""
        url = str(request.url)
        start_time = time.time()
        task_id = f"pytube_{int(time.time())}"
        
        try:
            loop = asyncio.get_event_loop()
            yt = await loop.run_in_executor(None, YouTube, url)
            
            # Get metadata
            video_metadata = VideoMetadata(
                id=yt.video_id,
                title=yt.title,
                description=yt.description or "",
                uploader=yt.author,
                duration=yt.length,
                view_count=yt.views,
                thumbnail=yt.thumbnail_url,
                webpage_url=f"https://www.youtube.com/watch?v={yt.video_id}",
                extraction_source="pytube"
            )
            
            # Get stream
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            if not stream:
                stream = yt.streams.filter(adaptive=True, only_video=True).order_by('resolution').desc().first()
            
            if not stream:
                raise ValueError("No suitable stream found")
            
            # Download
            safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = config.get_download_filename(safe_title)
            
            def download():
                return stream.download(output_path=self.download_path, filename=filename)
            
            video_file = await loop.run_in_executor(None, download)
            
            return DownloadResult(
                task_id=task_id,
                status=DownloadStatus.COMPLETED,
                video_metadata=video_metadata,
                video_file=video_file,
                filesize=os.path.getsize(video_file) if os.path.exists(video_file) else 0,
                download_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time()
            )
            
        except Exception as e:
            logger.error(f"Pytube download failed: {e}")
            return DownloadResult(
                task_id=task_id,
                status=DownloadStatus.FAILED,
                error=str(e),
                error_type=type(e).__name__,
                started_at=start_time,
                completed_at=time.time()
            )
    
    async def get_available_streams(self, url: str) -> List[QualityFormat]:
        """Get available streams."""
        try:
            loop = asyncio.get_event_loop()
            yt = await loop.run_in_executor(None, YouTube, url)
            
            formats = []
            for stream in yt.streams.filter(progressive=True, file_extension='mp4'):
                if stream.resolution:
                    quality = int(stream.resolution.replace('p', ''))
                    formats.append(QualityFormat(
                        format_id=f"pytube_{stream.itag}",
                        quality=quality,
                        resolution=stream.resolution,
                        filesize=stream.filesize,
                        ext="mp4"
                    ))
            return formats
        except Exception as e:
            logger.error(f"Failed to get streams: {e}")
            return []