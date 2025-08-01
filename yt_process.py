"""
Abstraction layer for GRABIT backend.
Routes between pytube and yt-dlp based on use case and quality requirements.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union, Tuple
from enum import Enum

from models import (
    VideoMetadata, PlaylistMetadata, DownloadRequest, PlaylistRequest, 
    BatchRequest, QualityFormat, DownloadProgress, DownloadResult
)
from config import get_config
from extract import get_extractor

logger = logging.getLogger(__name__)
config = get_config()


class ProcessorType(str, Enum):
    """Enum for processor types."""
    PYTUBE = "pytube"
    YTDLP = "yt-dlp"


class ProcessingStrategy:
    """Determines which processor to use based on requirements."""
    
    @staticmethod
    def determine_processor(quality: int, operation: str) -> ProcessorType:
        """
        Determine which processor to use based on quality and operation.
        
        Args:
            quality: Requested video quality
            operation: Type of operation (download, metadata, etc.)
            
        Returns:
            ProcessorType to use
        """
        
        # For metadata extraction, always use yt-dlp
        if operation in ['metadata', 'extract', 'info']:
            return ProcessorType.YTDLP
        
        # For downloads, check quality threshold
        if operation in ['download', 'stream']:
            if config.is_quality_direct_download(quality):
                # Use pytube for direct downloads ≤720p
                return ProcessorType.PYTUBE
            else:
                # Use yt-dlp + FFmpeg for rendering >720p
                return ProcessorType.YTDLP
        
        # For subtitle and thumbnail operations, use yt-dlp
        if operation in ['subtitles', 'thumbnail', 'captions']:
            return ProcessorType.YTDLP
        
        # Default to yt-dlp for unknown operations
        return ProcessorType.YTDLP
    
    @staticmethod
    def requires_rendering(quality: int) -> bool:
        """Check if quality requires FFmpeg rendering."""
        return not config.is_quality_direct_download(quality)
    
    @staticmethod
    def get_recommended_qualities() -> Dict[str, List[int]]:
        """Get recommended quality ranges for each processor."""
        return {
            "pytube": [144, 240, 360, 480, 720],
            "yt-dlp": [144, 240, 360, 480, 720, 1080, 1440, 2160],
            "render": [1080, 1440, 2160]
        }


class YouTubeProcessor:
    """Main processor that coordinates between pytube and yt-dlp."""
    
    def __init__(self):
        """Initialize the processor."""
        self.extractor = get_extractor()
        self._pytube_processor = None
        self._ytdlp_processor = None
    
    @property
    def pytube_processor(self):
        """Lazy load pytube processor."""
        if self._pytube_processor is None:
            from pytube_handler import PytubeHandler
            self._pytube_processor = PytubeHandler()
        return self._pytube_processor
    
    @property
    def ytdlp_processor(self):
        """Lazy load yt-dlp processor."""
        if self._ytdlp_processor is None:
            from ytdlp_handler import YtDlpHandler
            self._ytdlp_processor = YtDlpHandler()
        return self._ytdlp_processor
    
    async def extract_metadata(self, url: str) -> Union[VideoMetadata, PlaylistMetadata]:
        """
        Extract metadata using yt-dlp.
        
        Args:
            url: Video or playlist URL
            
        Returns:
            VideoMetadata or PlaylistMetadata
        """
        logger.info(f"Extracting metadata for: {url}")
        
        if self.extractor.is_playlist_url(url):
            return await self.extractor.extract_playlist_metadata(url)
        else:
            return await self.extractor.extract_video_metadata(url)
    
    async def download_video(self, request: DownloadRequest, 
                           progress_callback: Optional[callable] = None) -> DownloadResult:
        """
        Download a single video using appropriate processor.
        
        Args:
            request: Download request
            progress_callback: Optional progress callback function
            
        Returns:
            DownloadResult
        """
        url = str(request.url)
        quality = request.quality
        
        # Determine which processor to use
        processor_type = ProcessingStrategy.determine_processor(quality, 'download')
        
        logger.info(f"Downloading video {url} at {quality}p using {processor_type}")
        
        if processor_type == ProcessorType.PYTUBE:
            # Use pytube for direct download
            return await self.pytube_processor.download_video(request, progress_callback)
        else:
            # Use yt-dlp (possibly with rendering)
            if ProcessingStrategy.requires_rendering(quality):
                # High quality - render with FFmpeg
                return await self.ytdlp_processor.download_and_render(request, progress_callback)
            else:
                # Lower quality - direct download with yt-dlp
                return await self.ytdlp_processor.download_video(request, progress_callback)
    
    async def download_playlist(self, request: PlaylistRequest,
                               progress_callback: Optional[callable] = None) -> List[DownloadResult]:
        """
        Download playlist videos with error isolation.
        
        Args:
            request: Playlist download request
            progress_callback: Optional progress callback function
            
        Returns:
            List of DownloadResult objects
        """
        url = str(request.url)
        
        logger.info(f"Starting playlist download: {url}")
        
        # First extract playlist metadata
        playlist_metadata = await self.extractor.extract_playlist_metadata(url)
        
        # Determine which videos to download
        videos_to_download = self._select_playlist_videos(playlist_metadata, request)
        
        logger.info(f"Downloading {len(videos_to_download)} videos from playlist")
        
        # Create download tasks
        download_tasks = []
        for i, video in enumerate(videos_to_download):
            # Create individual download request
            video_request = DownloadRequest(
                url=video.webpage_url,
                quality=request.quality,
                format=request.format,
                include_audio=request.include_audio,
                include_subtitles=request.include_subtitles,
                subtitle_languages=request.subtitle_languages,
                download_thumbnail=request.download_thumbnail
            )
            
            # Create task with error isolation
            task = asyncio.create_task(
                self._download_with_error_isolation(
                    video_request, progress_callback, f"playlist_video_{i}"
                )
            )
            download_tasks.append(task)
        
        # Execute downloads with concurrency limit
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
        
        async def limited_download(task):
            async with semaphore:
                return await task
        
        # Wait for all downloads to complete
        results = await asyncio.gather(
            *[limited_download(task) for task in download_tasks],
            return_exceptions=True
        )
        
        # Filter out exceptions and return successful downloads
        successful_results = [
            result for result in results 
            if isinstance(result, DownloadResult) and result.status == "completed"
        ]
        
        logger.info(f"Playlist download completed: {len(successful_results)} successful, "
                   f"{len(results) - len(successful_results)} failed")
        
        return successful_results
    
    async def download_batch(self, request: BatchRequest,
                            progress_callback: Optional[callable] = None) -> List[DownloadResult]:
        """
        Download multiple videos with error isolation.
        
        Args:
            request: Batch download request
            progress_callback: Optional progress callback function
            
        Returns:
            List of DownloadResult objects
        """
        urls = [str(url) for url in request.urls]
        
        logger.info(f"Starting batch download for {len(urls)} videos")
        
        # Create download tasks
        download_tasks = []
        for i, url in enumerate(urls):
            # Create individual download request
            video_request = DownloadRequest(
                url=url,
                quality=request.quality,
                format=request.format,
                include_audio=request.include_audio,
                include_subtitles=request.include_subtitles,
                subtitle_languages=request.subtitle_languages,
                download_thumbnail=request.download_thumbnail
            )
            
            # Create task with error isolation
            task = asyncio.create_task(
                self._download_with_error_isolation(
                    video_request, progress_callback, f"batch_video_{i}"
                )
            )
            download_tasks.append(task)
        
        # Execute downloads with concurrency limit
        max_concurrent = request.max_concurrent or config.MAX_CONCURRENT_DOWNLOADS
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_download(task):
            async with semaphore:
                return await task
        
        # Wait for all downloads to complete
        results = await asyncio.gather(
            *[limited_download(task) for task in download_tasks],
            return_exceptions=True
        )
        
        # Process results
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, DownloadResult):
                if result.status == "completed":
                    successful_results.append(result)
                else:
                    failed_results.append(result)
            else:
                # Exception occurred
                failed_results.append(result)
        
        logger.info(f"Batch download completed: {len(successful_results)} successful, "
                   f"{len(failed_results)} failed")
        
        return successful_results
    
    async def download_thumbnail(self, url: str, quality: str = "maxresdefault") -> Optional[str]:
        """
        Download video thumbnail.
        
        Args:
            url: Video URL
            quality: Thumbnail quality
            
        Returns:
            Path to downloaded thumbnail file
        """
        logger.info(f"Downloading thumbnail for: {url}")
        return await self.ytdlp_processor.download_thumbnail(url, quality)
    
    async def download_subtitles(self, url: str, languages: List[str], 
                                auto_generated: bool = True) -> Dict[str, str]:
        """
        Download video subtitles.
        
        Args:
            url: Video URL
            languages: List of language codes
            auto_generated: Include auto-generated subtitles
            
        Returns:
            Dictionary mapping language codes to file paths
        """
        logger.info(f"Downloading subtitles for: {url}")
        return await self.ytdlp_processor.download_subtitles(url, languages, auto_generated)
    
    async def get_available_formats(self, url: str) -> Tuple[List[QualityFormat], List[QualityFormat]]:
        """
        Get available video and audio formats.
        
        Args:
            url: Video URL
            
        Returns:
            Tuple of (video_formats, audio_formats)
        """
        # Extract metadata to get formats
        metadata = await self.extract_metadata(url)
        
        if isinstance(metadata, VideoMetadata):
            return metadata.formats, metadata.audio_formats
        else:
            # For playlists, return formats from first video
            if metadata.videos:
                first_video = metadata.videos[0]
                return first_video.formats, first_video.audio_formats
            else:
                return [], []
    
    def _select_playlist_videos(self, playlist: PlaylistMetadata, 
                               request: PlaylistRequest) -> List[VideoMetadata]:
        """Select videos from playlist based on request parameters."""
        videos = playlist.videos
        
        if request.download_all:
            selected_videos = videos
        else:
            # Select specific videos by index
            selected_videos = []
            for index in request.selected_videos:
                if 0 <= index < len(videos):
                    selected_videos.append(videos[index])
        
        # Apply start/end index filters
        if request.start_index is not None:
            start_idx = max(0, request.start_index)
            selected_videos = selected_videos[start_idx:]
        
        if request.end_index is not None:
            end_idx = min(len(selected_videos), request.end_index + 1)
            selected_videos = selected_videos[:end_idx]
        
        # Apply max downloads limit
        if request.max_downloads is not None:
            selected_videos = selected_videos[:request.max_downloads]
        
        return selected_videos
    
    async def _download_with_error_isolation(self, request: DownloadRequest,
                                            progress_callback: Optional[callable],
                                            task_id: str) -> DownloadResult:
        """Download video with error isolation."""
        try:
            return await self.download_video(request, progress_callback)
        except Exception as e:
            logger.error(f"Download failed for task {task_id}: {e}")
            
            # Return failed result
            return DownloadResult(
                task_id=task_id,
                status="failed",
                error=str(e),
                error_type=type(e).__name__
            )
    
    def get_processor_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of available processors."""
        return {
            "pytube": {
                "max_quality": config.MAX_QUALITY_DIRECT,
                "supported_operations": ["download", "formats", "streams"],
                "direct_download": True,
                "rendering_required": False
            },
            "yt-dlp": {
                "max_quality": 2160,  # 4K
                "supported_operations": ["metadata", "download", "render", "subtitles", "thumbnail"],
                "direct_download": True,
                "rendering_required": True
            },
            "ffmpeg": {
                "available": True,
                "supported_codecs": ["h264", "vp9", "av1"],
                "supported_formats": ["mp4", "mkv", "webm"]
            }
        }


# Global processor instance
_processor = None


def get_processor() -> YouTubeProcessor:
    """Get the global YouTube processor instance."""
    global _processor
    if _processor is None:
        _processor = YouTubeProcessor()
    return _processor


async def process_download_request(request: Union[DownloadRequest, PlaylistRequest, BatchRequest],
                                  progress_callback: Optional[callable] = None) -> Union[DownloadResult, List[DownloadResult]]:
    """
    Process any type of download request using appropriate strategy.
    
    Args:
        request: Download request (single, playlist, or batch)
        progress_callback: Optional progress callback
        
    Returns:
        DownloadResult or list of DownloadResult objects
    """
    processor = get_processor()
    
    if isinstance(request, DownloadRequest):
        return await processor.download_video(request, progress_callback)
    elif isinstance(request, PlaylistRequest):
        return await processor.download_playlist(request, progress_callback)
    elif isinstance(request, BatchRequest):
        return await processor.download_batch(request, progress_callback)
    else:
        raise ValueError(f"Unsupported request type: {type(request)}")


def get_processing_strategy() -> ProcessingStrategy:
    """Get the processing strategy instance."""
    return ProcessingStrategy()