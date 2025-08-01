"""
Pydantic models for GRABIT backend.
Defines schemas for video metadata, requests, responses, and data validation.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, HttpUrl, Field, validator


class VideoType(str, Enum):
    """Enum for video types."""
    VIDEO = "video"
    SHORTS = "shorts"
    LIVE = "live"
    PREMIERE = "premiere"


class DownloadStatus(str, Enum):
    """Enum for download status."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    DOWNLOADING = "downloading"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QualityFormat(BaseModel):
    """Model for video quality format information."""
    format_id: str
    quality: int
    resolution: str
    fps: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    filesize_mb: Optional[float] = None
    ext: str = "mp4"
    format_note: Optional[str] = None
    
    @validator('filesize_mb', pre=True, always=True)
    def calculate_filesize_mb(cls, v, values):
        """Calculate filesize in MB from bytes."""
        if v is not None:
            return v
        filesize = values.get('filesize')
        if filesize:
            return round(filesize / (1024 * 1024), 2)
        return None


class SubtitleTrack(BaseModel):
    """Model for subtitle track information."""
    language: str
    language_code: str
    ext: str = "srt"
    url: Optional[str] = None
    auto_generated: bool = False


class VideoMetadata(BaseModel):
    """Comprehensive video metadata model."""
    # Basic information
    id: str
    title: str
    description: Optional[str] = None
    uploader: str
    uploader_id: Optional[str] = None
    uploader_url: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    
    # Media information
    duration: Optional[int] = None  # in seconds
    duration_string: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    
    # Dates
    upload_date: Optional[str] = None
    release_date: Optional[str] = None
    timestamp: Optional[int] = None
    
    # Technical details
    video_type: VideoType = VideoType.VIDEO
    is_live: bool = False
    was_live: bool = False
    availability: Optional[str] = None
    age_limit: Optional[int] = None
    
    # Media URLs and formats
    thumbnail: Optional[str] = None
    thumbnails: List[Dict[str, Any]] = []
    formats: List[QualityFormat] = []
    
    # Audio information
    audio_formats: List[QualityFormat] = []
    
    # Subtitles
    subtitles: List[SubtitleTrack] = []
    automatic_captions: List[SubtitleTrack] = []
    
    # Playlist information (if applicable)
    playlist_title: Optional[str] = None
    playlist_id: Optional[str] = None
    playlist_index: Optional[int] = None
    playlist_count: Optional[int] = None
    
    # Additional metadata
    tags: List[str] = []
    categories: List[str] = []
    webpage_url: str
    original_url: Optional[str] = None
    
    # Processing metadata
    extracted_at: datetime = Field(default_factory=datetime.now)
    extraction_source: str = "yt-dlp"  # or "pytube"


class PlaylistMetadata(BaseModel):
    """Model for playlist metadata."""
    id: str
    title: str
    description: Optional[str] = None
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    uploader_url: Optional[str] = None
    
    # Playlist details
    video_count: int
    view_count: Optional[int] = None
    
    # Dates
    upload_date: Optional[str] = None
    modified_date: Optional[str] = None
    
    # URLs
    webpage_url: str
    thumbnail: Optional[str] = None
    
    # Videos in playlist
    videos: List[VideoMetadata] = []
    
    # Processing metadata
    extracted_at: datetime = Field(default_factory=datetime.now)


class DownloadRequest(BaseModel):
    """Base model for download requests."""
    url: HttpUrl
    quality: int = Field(default=720, ge=144, le=2160)
    format: str = Field(default="mp4", pattern="^(mp4|webm|mkv)$")
    include_audio: bool = True
    include_subtitles: bool = False
    subtitle_languages: List[str] = ["en"]
    download_thumbnail: bool = False
    custom_filename: Optional[str] = None


class SingleVideoRequest(DownloadRequest):
    """Model for single video download request."""
    pass


class PlaylistRequest(BaseModel):
    """Model for playlist download request."""
    url: HttpUrl
    quality: int = Field(default=720, ge=144, le=2160)
    format: str = Field(default="mp4", pattern="^(mp4|webm|mkv)$")
    include_audio: bool = True
    include_subtitles: bool = False
    subtitle_languages: List[str] = ["en"]
    download_thumbnail: bool = False
    
    # Playlist-specific options
    download_all: bool = True
    selected_videos: List[int] = []  # Indices of videos to download
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    max_downloads: Optional[int] = None
    
    @validator('selected_videos')
    def validate_selected_videos(cls, v, values):
        """Validate selected videos when not downloading all."""
        if not values.get('download_all') and not v:
            raise ValueError("Must specify selected_videos when download_all is False")
        return v


class BatchRequest(BaseModel):
    """Model for batch download request."""
    urls: List[HttpUrl] = Field(min_items=1, max_items=50)
    quality: int = Field(default=720, ge=144, le=2160)
    format: str = Field(default="mp4", pattern="^(mp4|webm|mkv)$")
    include_audio: bool = True
    include_subtitles: bool = False
    subtitle_languages: List[str] = ["en"]
    download_thumbnail: bool = False
    
    # Batch-specific options
    continue_on_error: bool = True
    max_concurrent: Optional[int] = None


class ThumbnailRequest(BaseModel):
    """Model for thumbnail download request."""
    url: HttpUrl
    quality: str = Field(default="maxresdefault", pattern="^(maxresdefault|hqdefault|mqdefault|default)$")


class SubtitleRequest(BaseModel):
    """Model for subtitle download request."""
    url: HttpUrl
    languages: List[str] = ["en"]
    auto_generated: bool = True
    format: str = Field(default="srt", pattern="^(srt|vtt|ass)$")


class DownloadProgress(BaseModel):
    """Model for download progress updates."""
    task_id: str
    status: DownloadStatus
    progress_percentage: float = Field(ge=0, le=100)
    current_step: str
    total_steps: int
    current_step_number: int
    
    # File information
    filename: Optional[str] = None
    filesize_total: Optional[int] = None
    filesize_downloaded: Optional[int] = None
    speed: Optional[float] = None  # bytes per second
    eta: Optional[int] = None  # seconds
    
    # Additional context
    video_title: Optional[str] = None
    quality: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class DownloadResult(BaseModel):
    """Model for download completion result."""
    task_id: str
    status: DownloadStatus
    video_metadata: Optional[VideoMetadata] = None
    
    # File paths
    video_file: Optional[str] = None
    audio_file: Optional[str] = None
    subtitle_files: Dict[str, str] = {}  # language -> file_path
    thumbnail_file: Optional[str] = None
    
    # Download statistics
    filesize: Optional[int] = None
    download_time: Optional[float] = None  # seconds
    average_speed: Optional[float] = None  # bytes per second
    
    # Error information
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BatchResult(BaseModel):
    """Model for batch download results."""
    batch_id: str
    total_videos: int
    successful_downloads: int
    failed_downloads: int
    
    # Individual results
    results: List[DownloadResult] = []
    
    # Overall statistics
    total_filesize: Optional[int] = None
    total_download_time: Optional[float] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PlaylistResult(BaseModel):
    """Model for playlist download results."""
    playlist_id: str
    playlist_metadata: Optional[PlaylistMetadata] = None
    total_videos: int
    successful_downloads: int
    failed_downloads: int
    
    # Individual results
    results: List[DownloadResult] = []
    
    # Overall statistics
    total_filesize: Optional[int] = None
    total_download_time: Optional[float] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str
    error_type: str
    message: str
    task_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None


class StatusResponse(BaseModel):
    """Model for status responses."""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class MetadataResponse(BaseModel):
    """Model for metadata extraction responses."""
    video_metadata: Optional[VideoMetadata] = None
    playlist_metadata: Optional[PlaylistMetadata] = None
    extraction_time: float
    cached: bool = False
    
    
class WebSocketMessage(BaseModel):
    """Model for WebSocket messages."""
    type: str  # "progress", "status", "error", "metadata"
    task_id: Optional[str] = None
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class ServerStatus(BaseModel):
    """Model for server status information."""
    status: str = "running"
    version: str
    active_downloads: int
    total_downloads: int
    uptime: float  # seconds
    memory_usage: Optional[float] = None  # MB
    disk_space: Optional[float] = None  # MB available
    
    # Configuration info
    max_concurrent_downloads: int
    supported_formats: List[str] = ["mp4", "webm", "mkv"]
    supported_qualities: List[int] = [144, 240, 360, 480, 720, 1080, 1440, 2160]
    ffmpeg_available: bool = True
    
    timestamp: datetime = Field(default_factory=datetime.now)


# Response models for API endpoints
class ExtractResponse(BaseModel):
    """Response model for metadata extraction."""
    success: bool
    data: Optional[Union[VideoMetadata, PlaylistMetadata]] = None
    error: Optional[str] = None
    extraction_time: float


class DownloadResponse(BaseModel):
    """Response model for download initiation."""
    success: bool
    task_id: str
    message: str
    estimated_time: Optional[float] = None


class TaskStatusResponse(BaseModel):
    """Response model for task status queries."""
    task_id: str
    status: DownloadStatus
    progress: Optional[DownloadProgress] = None
    result: Optional[DownloadResult] = None