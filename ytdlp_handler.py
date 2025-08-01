"""
YT-DLP handler for GRABIT backend.
"""

import asyncio
import logging
import time
import os
import subprocess
from typing import List, Optional, Dict, Callable
from pathlib import Path
import yt_dlp

from models import DownloadRequest, DownloadResult, QualityFormat, VideoMetadata, DownloadProgress, DownloadStatus
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class YtDlpHandler:
    """Handles downloads using yt-dlp for >720p and special operations."""
    
    def __init__(self):
        self.download_path = config.DEFAULT_DOWNLOAD_PATH
        self.temp_path = config.TEMP_PATH
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
        Path(self.temp_path).mkdir(parents=True, exist_ok=True)
    
    async def download_video(self, request: DownloadRequest, progress_callback: Optional[Callable] = None) -> DownloadResult:
        """Download video using yt-dlp."""
        url = str(request.url)
        start_time = time.time()
        task_id = f"ytdlp_{int(time.time())}"
        
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'format': f'best[height<={request.quality}]',
                'outtmpl': os.path.join(self.download_path, f'{config.SITENAME_PREFIX}_%(title)s.%(ext)s'),
                'writesubtitles': request.include_subtitles,
                'writeautomaticsub': request.include_subtitles,
                'writethumbnail': request.download_thumbnail,
                'quiet': True,
                'no_warnings': True
            }
            
            # Download
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return info
            
            info = await loop.run_in_executor(None, download)
            
            # Create metadata
            video_metadata = VideoMetadata(
                id=info.get('id', ''),
                title=info.get('title', 'Unknown'),
                description=info.get('description', ''),
                uploader=info.get('uploader', 'Unknown'),
                duration=info.get('duration'),
                view_count=info.get('view_count'),
                thumbnail=info.get('thumbnail'),
                webpage_url=info.get('webpage_url', url),
                extraction_source="yt-dlp"
            )
            
            # Find downloaded file
            video_file = self._find_downloaded_file(info)
            
            return DownloadResult(
                task_id=task_id,
                status=DownloadStatus.COMPLETED,
                video_metadata=video_metadata,
                video_file=video_file,
                filesize=os.path.getsize(video_file) if video_file and os.path.exists(video_file) else 0,
                download_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time()
            )
            
        except Exception as e:
            logger.error(f"yt-dlp download failed: {e}")
            return DownloadResult(
                task_id=task_id,
                status=DownloadStatus.FAILED,
                error=str(e),
                error_type=type(e).__name__,
                started_at=start_time,
                completed_at=time.time()
            )
    
    async def download_and_render(self, request: DownloadRequest, progress_callback: Optional[Callable] = None) -> DownloadResult:
        """Download high quality video and render with FFmpeg."""
        url = str(request.url)
        start_time = time.time()
        task_id = f"render_{int(time.time())}"
        
        try:
            # Download best video and audio separately
            video_opts = {
                'format': f'bestvideo[height<={request.quality}]',
                'outtmpl': os.path.join(self.temp_path, f'video_{task_id}.%(ext)s'),
                'quiet': True
            }
            
            audio_opts = {
                'format': 'bestaudio',
                'outtmpl': os.path.join(self.temp_path, f'audio_{task_id}.%(ext)s'),
                'quiet': True
            }
            
            loop = asyncio.get_event_loop()
            
            # Download video
            def download_video():
                with yt_dlp.YoutubeDL(video_opts) as ydl:
                    return ydl.extract_info(url, download=True)
            
            # Download audio
            def download_audio():
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    return ydl.extract_info(url, download=True)
            
            video_info, audio_info = await asyncio.gather(
                loop.run_in_executor(None, download_video),
                loop.run_in_executor(None, download_audio)
            )
            
            # Find downloaded files
            video_file = self._find_temp_file(f'video_{task_id}')
            audio_file = self._find_temp_file(f'audio_{task_id}')
            
            if not video_file or not audio_file:
                raise ValueError("Failed to download video or audio components")
            
            # Render with FFmpeg
            from render import render_video
            output_file = await render_video(video_file, audio_file, video_info.get('title', 'video'))
            
            # Cleanup temp files
            self._cleanup_files([video_file, audio_file])
            
            # Create metadata
            video_metadata = VideoMetadata(
                id=video_info.get('id', ''),
                title=video_info.get('title', 'Unknown'),
                description=video_info.get('description', ''),
                uploader=video_info.get('uploader', 'Unknown'),
                duration=video_info.get('duration'),
                view_count=video_info.get('view_count'),
                thumbnail=video_info.get('thumbnail'),
                webpage_url=video_info.get('webpage_url', url),
                extraction_source="yt-dlp"
            )
            
            return DownloadResult(
                task_id=task_id,
                status=DownloadStatus.COMPLETED,
                video_metadata=video_metadata,
                video_file=output_file,
                filesize=os.path.getsize(output_file) if os.path.exists(output_file) else 0,
                download_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time()
            )
            
        except Exception as e:
            logger.error(f"yt-dlp render failed: {e}")
            return DownloadResult(
                task_id=task_id,
                status=DownloadStatus.FAILED,
                error=str(e),
                error_type=type(e).__name__,
                started_at=start_time,
                completed_at=time.time()
            )
    
    async def download_subtitles(self, url: str, languages: List[str], auto_generated: bool = True) -> Dict[str, str]:
        """Download subtitles."""
        try:
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': auto_generated,
                'subtitleslangs': languages,
                'skip_download': True,
                'outtmpl': os.path.join(self.download_path, f'{config.SITENAME_PREFIX}_%(title)s.%(ext)s'),
                'quiet': True
            }
            
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)
            
            await loop.run_in_executor(None, download)
            
            # Find subtitle files
            subtitle_files = {}
            for lang in languages:
                subtitle_file = self._find_subtitle_file(lang)
                if subtitle_file:
                    subtitle_files[lang] = subtitle_file
            
            return subtitle_files
            
        except Exception as e:
            logger.error(f"Subtitle download failed: {e}")
            return {}
    
    async def download_thumbnail(self, url: str, quality: str = "maxresdefault") -> Optional[str]:
        """Download thumbnail."""
        try:
            ydl_opts = {
                'writethumbnail': True,
                'skip_download': True,
                'outtmpl': os.path.join(self.download_path, f'{config.SITENAME_PREFIX}_%(title)s.%(ext)s'),
                'quiet': True
            }
            
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)
            
            info = await loop.run_in_executor(None, download)
            
            # Find thumbnail file
            return self._find_thumbnail_file(info.get('title', 'thumbnail'))
            
        except Exception as e:
            logger.error(f"Thumbnail download failed: {e}")
            return None
    
    def _find_downloaded_file(self, info: Dict) -> Optional[str]:
        """Find the downloaded video file."""
        try:
            # yt-dlp should provide the filename
            if '_filename' in info:
                return info['_filename']
            
            # Fallback: search for files
            title = info.get('title', 'video')
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            
            for ext in ['mp4', 'mkv', 'webm']:
                filename = f"{config.SITENAME_PREFIX}_{safe_title}.{ext}"
                filepath = os.path.join(self.download_path, filename)
                if os.path.exists(filepath):
                    return filepath
            
            return None
        except Exception:
            return None
    
    def _find_temp_file(self, prefix: str) -> Optional[str]:
        """Find temporary file by prefix."""
        try:
            for file in os.listdir(self.temp_path):
                if file.startswith(prefix):
                    return os.path.join(self.temp_path, file)
            return None
        except Exception:
            return None
    
    def _find_subtitle_file(self, language: str) -> Optional[str]:
        """Find subtitle file by language."""
        try:
            for file in os.listdir(self.download_path):
                if f".{language}." in file and file.endswith('.srt'):
                    return os.path.join(self.download_path, file)
            return None
        except Exception:
            return None
    
    def _find_thumbnail_file(self, title: str) -> Optional[str]:
        """Find thumbnail file."""
        try:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            for ext in ['jpg', 'png', 'webp']:
                filename = f"{config.SITENAME_PREFIX}_{safe_title}.{ext}"
                filepath = os.path.join(self.download_path, filename)
                if os.path.exists(filepath):
                    return filepath
            return None
        except Exception:
            return None
    
    def _cleanup_files(self, files: List[str]):
        """Clean up temporary files."""
        for file in files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file}: {e}")