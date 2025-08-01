"""
Metadata extraction module for GRABIT backend.
Uses yt-dlp for comprehensive metadata extraction with error isolation.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse, parse_qs
import yt_dlp
from datetime import datetime

from models import (
    VideoMetadata, PlaylistMetadata, QualityFormat, SubtitleTrack, VideoType,
    MetadataResponse
)
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class MetadataExtractor:
    """Handles metadata extraction using yt-dlp."""
    
    def __init__(self):
        """Initialize the metadata extractor."""
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'dump_single_json': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
            'embedsubtitles': False,
            'writeinfojson': False,
            'no_color': True,
            'skip_download': True,
        }
    
    async def extract_video_metadata(self, url: str) -> VideoMetadata:
        """
        Extract metadata for a single video.
        
        Args:
            url: Video URL
            
        Returns:
            VideoMetadata object
            
        Raises:
            Exception: If extraction fails
        """
        logger.info(f"Extracting metadata for video: {url}")
        start_time = time.time()
        
        try:
            # Run yt-dlp extraction in executor to avoid blocking
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, self._extract_info, url, False
            )
            
            if not info:
                raise ValueError("No video information extracted")
            
            # Convert to our VideoMetadata model
            metadata = self._convert_to_video_metadata(info)
            
            extraction_time = time.time() - start_time
            logger.info(f"Metadata extraction completed in {extraction_time:.2f}s for: {metadata.title}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata for {url}: {e}")
            raise e
    
    async def extract_playlist_metadata(self, url: str) -> PlaylistMetadata:
        """
        Extract metadata for a playlist.
        
        Args:
            url: Playlist URL
            
        Returns:
            PlaylistMetadata object
            
        Raises:
            Exception: If extraction fails
        """
        logger.info(f"Extracting playlist metadata: {url}")
        start_time = time.time()
        
        try:
            # Run yt-dlp extraction in executor
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, self._extract_info, url, True
            )
            
            if not info:
                raise ValueError("No playlist information extracted")
            
            # Convert to our PlaylistMetadata model
            metadata = self._convert_to_playlist_metadata(info)
            
            extraction_time = time.time() - start_time
            logger.info(f"Playlist metadata extraction completed in {extraction_time:.2f}s for: {metadata.title}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract playlist metadata for {url}: {e}")
            raise e
    
    async def extract_batch_metadata(self, urls: List[str]) -> List[VideoMetadata]:
        """
        Extract metadata for multiple videos with error isolation.
        
        Args:
            urls: List of video URLs
            
        Returns:
            List of VideoMetadata objects (failed extractions are skipped)
        """
        logger.info(f"Extracting batch metadata for {len(urls)} videos")
        start_time = time.time()
        
        # Create tasks for concurrent extraction
        tasks = []
        for url in urls:
            task = asyncio.create_task(self._extract_single_with_error_handling(url))
            tasks.append(task)
        
        # Wait for all extractions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results (failed extractions)
        successful_extractions = [
            result for result in results 
            if isinstance(result, VideoMetadata)
        ]
        
        # Log failures
        failed_count = len(urls) - len(successful_extractions)
        if failed_count > 0:
            logger.warning(f"Failed to extract metadata for {failed_count} out of {len(urls)} videos")
        
        extraction_time = time.time() - start_time
        logger.info(f"Batch metadata extraction completed in {extraction_time:.2f}s")
        
        return successful_extractions
    
    async def _extract_single_with_error_handling(self, url: str) -> Optional[VideoMetadata]:
        """Extract metadata for a single video with error handling."""
        try:
            return await self.extract_video_metadata(url)
        except Exception as e:
            logger.error(f"Failed to extract metadata for {url}: {e}")
            return None
    
    def _extract_info(self, url: str, is_playlist: bool = False) -> Optional[Dict[str, Any]]:
        """
        Extract information using yt-dlp.
        
        Args:
            url: URL to extract from
            is_playlist: Whether this is a playlist extraction
            
        Returns:
            Extracted information dictionary
        """
        opts = self.ydl_opts.copy()
        
        if is_playlist:
            opts['extract_flat'] = False  # Get full info for playlist videos
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.error(f"yt-dlp extraction failed for {url}: {e}")
            return None
    
    def _convert_to_video_metadata(self, info: Dict[str, Any]) -> VideoMetadata:
        """Convert yt-dlp info dict to VideoMetadata object."""
        
        # Extract basic information
        video_id = info.get('id', '')
        title = info.get('title', 'Unknown Title')
        description = info.get('description', '')
        uploader = info.get('uploader', info.get('channel', 'Unknown'))
        uploader_id = info.get('uploader_id', info.get('channel_id'))
        uploader_url = info.get('uploader_url', info.get('channel_url'))
        
        # Duration and view information
        duration = info.get('duration')
        duration_string = info.get('duration_string')
        view_count = info.get('view_count')
        like_count = info.get('like_count')
        comment_count = info.get('comment_count')
        
        # Date information
        upload_date = info.get('upload_date')
        release_date = info.get('release_date')
        timestamp = info.get('timestamp')
        
        # Video type detection
        video_type = self._detect_video_type(info)
        is_live = info.get('is_live', False)
        was_live = info.get('was_live', False)
        
        # Availability and age limit
        availability = info.get('availability')
        age_limit = info.get('age_limit', 0)
        
        # Thumbnail information
        thumbnail = info.get('thumbnail')
        thumbnails = info.get('thumbnails', [])
        
        # Format information
        formats = self._extract_formats(info.get('formats', []))
        audio_formats = self._extract_audio_formats(info.get('formats', []))
        
        # Subtitle information
        subtitles = self._extract_subtitles(info.get('subtitles', {}))
        automatic_captions = self._extract_subtitles(info.get('automatic_captions', {}), auto_generated=True)
        
        # Playlist information (if applicable)
        playlist_title = info.get('playlist_title')
        playlist_id = info.get('playlist_id')
        playlist_index = info.get('playlist_index')
        playlist_count = info.get('playlist_count')
        
        # Tags and categories
        tags = info.get('tags', [])
        categories = info.get('categories', [])
        
        # URLs
        webpage_url = info.get('webpage_url', '')
        original_url = info.get('original_url')
        
        return VideoMetadata(
            id=video_id,
            title=title,
            description=description,
            uploader=uploader,
            uploader_id=uploader_id,
            uploader_url=uploader_url,
            channel=uploader,
            channel_id=uploader_id,
            channel_url=uploader_url,
            duration=duration,
            duration_string=duration_string,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            upload_date=upload_date,
            release_date=release_date,
            timestamp=timestamp,
            video_type=video_type,
            is_live=is_live,
            was_live=was_live,
            availability=availability,
            age_limit=age_limit,
            thumbnail=thumbnail,
            thumbnails=thumbnails,
            formats=formats,
            audio_formats=audio_formats,
            subtitles=subtitles,
            automatic_captions=automatic_captions,
            playlist_title=playlist_title,
            playlist_id=playlist_id,
            playlist_index=playlist_index,
            playlist_count=playlist_count,
            tags=tags,
            categories=categories,
            webpage_url=webpage_url,
            original_url=original_url,
            extraction_source="yt-dlp"
        )
    
    def _convert_to_playlist_metadata(self, info: Dict[str, Any]) -> PlaylistMetadata:
        """Convert yt-dlp playlist info dict to PlaylistMetadata object."""
        
        playlist_id = info.get('id', '')
        title = info.get('title', 'Unknown Playlist')
        description = info.get('description', '')
        uploader = info.get('uploader', info.get('channel', 'Unknown'))
        uploader_id = info.get('uploader_id', info.get('channel_id'))
        uploader_url = info.get('uploader_url', info.get('channel_url'))
        
        # Playlist details
        entries = info.get('entries', [])
        video_count = len(entries)
        view_count = info.get('view_count')
        
        # Dates
        upload_date = info.get('upload_date')
        modified_date = info.get('modified_date')
        
        # URLs
        webpage_url = info.get('webpage_url', '')
        thumbnail = info.get('thumbnail')
        
        # Convert entries to VideoMetadata objects
        videos = []
        for entry in entries:
            if entry:  # entry can be None for unavailable videos
                try:
                    video_metadata = self._convert_to_video_metadata(entry)
                    videos.append(video_metadata)
                except Exception as e:
                    logger.warning(f"Failed to convert playlist entry: {e}")
                    continue
        
        return PlaylistMetadata(
            id=playlist_id,
            title=title,
            description=description,
            uploader=uploader,
            uploader_id=uploader_id,
            uploader_url=uploader_url,
            video_count=len(videos),  # Use actual converted videos count
            view_count=view_count,
            upload_date=upload_date,
            modified_date=modified_date,
            webpage_url=webpage_url,
            thumbnail=thumbnail,
            videos=videos
        )
    
    def _detect_video_type(self, info: Dict[str, Any]) -> VideoType:
        """Detect video type from yt-dlp info."""
        if info.get('is_live'):
            return VideoType.LIVE
        elif info.get('was_live'):
            return VideoType.LIVE
        elif info.get('live_status') == 'is_upcoming':
            return VideoType.PREMIERE
        
        # Check duration for shorts (≤60 seconds)
        duration = info.get('duration')
        if duration and duration <= 60:
            return VideoType.SHORTS
        
        return VideoType.VIDEO
    
    def _extract_formats(self, formats: List[Dict[str, Any]]) -> List[QualityFormat]:
        """Extract video formats from yt-dlp format list."""
        quality_formats = []
        
        for fmt in formats:
            if fmt.get('vcodec') != 'none':  # Only video formats
                try:
                    quality_format = QualityFormat(
                        format_id=fmt.get('format_id', ''),
                        quality=int(fmt.get('height', 0)),
                        resolution=f"{fmt.get('width', 0)}x{fmt.get('height', 0)}",
                        fps=fmt.get('fps'),
                        vcodec=fmt.get('vcodec'),
                        acodec=fmt.get('acodec'),
                        filesize=fmt.get('filesize'),
                        ext=fmt.get('ext', 'mp4'),
                        format_note=fmt.get('format_note')
                    )
                    quality_formats.append(quality_format)
                except Exception as e:
                    logger.warning(f"Failed to parse format: {e}")
                    continue
        
        return quality_formats
    
    def _extract_audio_formats(self, formats: List[Dict[str, Any]]) -> List[QualityFormat]:
        """Extract audio formats from yt-dlp format list."""
        audio_formats = []
        
        for fmt in formats:
            if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':  # Only audio formats
                try:
                    quality_format = QualityFormat(
                        format_id=fmt.get('format_id', ''),
                        quality=0,  # Audio doesn't have height
                        resolution='audio',
                        fps=None,
                        vcodec=None,
                        acodec=fmt.get('acodec'),
                        filesize=fmt.get('filesize'),
                        ext=fmt.get('ext', 'mp3'),
                        format_note=fmt.get('format_note')
                    )
                    audio_formats.append(quality_format)
                except Exception as e:
                    logger.warning(f"Failed to parse audio format: {e}")
                    continue
        
        return audio_formats
    
    def _extract_subtitles(self, subtitles: Dict[str, Any], auto_generated: bool = False) -> List[SubtitleTrack]:
        """Extract subtitle tracks from yt-dlp subtitle info."""
        subtitle_tracks = []
        
        for lang_code, sub_list in subtitles.items():
            if isinstance(sub_list, list) and sub_list:
                # Take the first subtitle option
                sub_info = sub_list[0]
                
                try:
                    subtitle_track = SubtitleTrack(
                        language=lang_code,  # You might want to convert to full language name
                        language_code=lang_code,
                        ext=sub_info.get('ext', 'srt'),
                        url=sub_info.get('url'),
                        auto_generated=auto_generated
                    )
                    subtitle_tracks.append(subtitle_track)
                except Exception as e:
                    logger.warning(f"Failed to parse subtitle track {lang_code}: {e}")
                    continue
        
        return subtitle_tracks
    
    def is_playlist_url(self, url: str) -> bool:
        """Check if URL is a playlist URL."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Check for playlist parameter
        if 'list' in query_params:
            return True
        
        # Check for playlist in path
        if '/playlist' in parsed.path:
            return True
        
        return False
    
    def is_video_url(self, url: str) -> bool:
        """Check if URL is a video URL."""
        parsed = urlparse(url)
        
        # YouTube video patterns
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            return True
        
        # Add other supported sites as needed
        return False


# Global extractor instance
_extractor = None


def get_extractor() -> MetadataExtractor:
    """Get the global metadata extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = MetadataExtractor()
    return _extractor


async def extract_metadata(url: str) -> MetadataResponse:
    """
    Extract metadata from URL (video or playlist).
    
    Args:
        url: URL to extract metadata from
        
    Returns:
        MetadataResponse object
    """
    extractor = get_extractor()
    start_time = time.time()
    
    try:
        if extractor.is_playlist_url(url):
            playlist_metadata = await extractor.extract_playlist_metadata(url)
            extraction_time = time.time() - start_time
            
            return MetadataResponse(
                playlist_metadata=playlist_metadata,
                extraction_time=extraction_time
            )
        else:
            video_metadata = await extractor.extract_video_metadata(url)
            extraction_time = time.time() - start_time
            
            return MetadataResponse(
                video_metadata=video_metadata,
                extraction_time=extraction_time
            )
    
    except Exception as e:
        logger.error(f"Metadata extraction failed for {url}: {e}")
        raise e


async def extract_batch_metadata(urls: List[str]) -> List[VideoMetadata]:
    """
    Extract metadata for multiple videos with error isolation.
    
    Args:
        urls: List of video URLs
        
    Returns:
        List of VideoMetadata objects
    """
    extractor = get_extractor()
    return await extractor.extract_batch_metadata(urls)