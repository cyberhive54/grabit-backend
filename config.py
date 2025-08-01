"""
Configuration management for GRABIT backend.
Loads and validates environment variables using python-dotenv.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """Configuration class that loads and validates environment variables."""
    
    def __init__(self):
        """Initialize configuration by loading .env file and validating variables."""
        # Load environment variables from .env file
        env_path = Path(__file__).parent / '.env'
        load_dotenv(env_path)
        
        # Core settings
        self.SITENAME_PREFIX = self._get_env_var('SITENAME_PREFIX', 'GRABIT')
        self.CORS_ORIGINS = self._parse_cors_origins(
            self._get_env_var('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080')
        )
        self.WEBSOCKET_URL = self._get_env_var('WEBSOCKET_URL', 'ws://localhost:8000/ws')
        self.FFMPEG_PATH = self._get_env_var('FFMPEG_PATH', './ffmpeg/bin/ffmpeg')
        
        # Server configuration
        self.HOST = self._get_env_var('HOST', '0.0.0.0')
        self.PORT = int(self._get_env_var('PORT', '8000'))
        self.WORKERS = int(self._get_env_var('WORKERS', '4'))
        
        # Download configuration
        self.MAX_CONCURRENT_DOWNLOADS = int(self._get_env_var('MAX_CONCURRENT_DOWNLOADS', '5'))
        self.DEFAULT_DOWNLOAD_PATH = self._get_env_var('DEFAULT_DOWNLOAD_PATH', './downloads')
        self.TEMP_PATH = self._get_env_var('TEMP_PATH', './temp')
        
        # Quality limits
        self.MAX_QUALITY_DIRECT = int(self._get_env_var('MAX_QUALITY_DIRECT', '720'))
        self.MIN_QUALITY = int(self._get_env_var('MIN_QUALITY', '144'))
        
        # WebSocket settings
        self.WS_HEARTBEAT_INTERVAL = int(self._get_env_var('WS_HEARTBEAT_INTERVAL', '30'))
        self.WS_MAX_CONNECTIONS = int(self._get_env_var('WS_MAX_CONNECTIONS', '100'))
        
        # Security settings
        self.MAX_FILE_SIZE_MB = int(self._get_env_var('MAX_FILE_SIZE_MB', '2048'))
        self.RATE_LIMIT_PER_MINUTE = int(self._get_env_var('RATE_LIMIT_PER_MINUTE', '60'))
        
        # Logging configuration
        self.LOG_LEVEL = self._get_env_var('LOG_LEVEL', 'INFO')
        self.LOG_FILE = self._get_env_var('LOG_FILE', './logs/grabit.log')
        
        # Optional settings
        self.YOUTUBE_API_KEY = self._get_env_var('YOUTUBE_API_KEY', '', required=False)
        self.DEBUG = self._get_env_var('DEBUG', 'false').lower() == 'true'
        
        # Validate configuration
        self._validate_config()
        
        # Create necessary directories
        self._create_directories()
    
    def _get_env_var(self, key: str, default: str = '', required: bool = True) -> str:
        """Get environment variable with optional default value."""
        value = os.getenv(key, default)
        if required and not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def _parse_cors_origins(self, cors_string: str) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if not cors_string:
            return ["*"]
        return [origin.strip() for origin in cors_string.split(',') if origin.strip()]
    
    def _validate_config(self):
        """Validate configuration values and dependencies."""
        errors = []
        
        # Validate FFMPEG_PATH
        if not os.path.exists(self.FFMPEG_PATH) and not self._is_in_path('ffmpeg'):
            errors.append(f"FFmpeg not found at {self.FFMPEG_PATH} or in system PATH")
        
        # Validate port range
        if not (1 <= self.PORT <= 65535):
            errors.append(f"Invalid port number: {self.PORT}")
        
        # Validate quality settings
        if self.MAX_QUALITY_DIRECT < self.MIN_QUALITY:
            errors.append("MAX_QUALITY_DIRECT must be greater than MIN_QUALITY")
        
        # Validate positive integers
        positive_int_configs = [
            ('WORKERS', self.WORKERS),
            ('MAX_CONCURRENT_DOWNLOADS', self.MAX_CONCURRENT_DOWNLOADS),
            ('WS_HEARTBEAT_INTERVAL', self.WS_HEARTBEAT_INTERVAL),
            ('WS_MAX_CONNECTIONS', self.WS_MAX_CONNECTIONS),
            ('MAX_FILE_SIZE_MB', self.MAX_FILE_SIZE_MB),
            ('RATE_LIMIT_PER_MINUTE', self.RATE_LIMIT_PER_MINUTE)
        ]
        
        for name, value in positive_int_configs:
            if value <= 0:
                errors.append(f"{name} must be a positive integer, got: {value}")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            errors.append(f"Invalid log level: {self.LOG_LEVEL}. Must be one of {valid_log_levels}")
        
        if errors:
            error_message = "Configuration validation errors:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_message)
    
    def _is_in_path(self, program: str) -> bool:
        """Check if a program is available in system PATH."""
        import shutil
        return shutil.which(program) is not None
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.DEFAULT_DOWNLOAD_PATH,
            self.TEMP_PATH,
            os.path.dirname(self.LOG_FILE) if self.LOG_FILE else None
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Set up logging configuration."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format=log_format,
            handlers=[
                logging.StreamHandler(),  # Console output
                logging.FileHandler(self.LOG_FILE) if self.LOG_FILE else logging.NullHandler()
            ]
        )
        
        # Set specific logger levels
        if not self.DEBUG:
            # Reduce noise from third-party libraries in production
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("websockets").setLevel(logging.WARNING)
    
    def get_ffmpeg_command(self) -> str:
        """Get the FFmpeg command path."""
        if os.path.exists(self.FFMPEG_PATH):
            return self.FFMPEG_PATH
        elif self._is_in_path('ffmpeg'):
            return 'ffmpeg'
        else:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg or set FFMPEG_PATH.")
    
    def is_quality_direct_download(self, quality: int) -> bool:
        """Check if quality should be downloaded directly (pytube) or rendered (yt-dlp + FFmpeg)."""
        return quality <= self.MAX_QUALITY_DIRECT
    
    def get_download_filename(self, base_name: str, extension: str = 'mp4') -> str:
        """Generate filename with sitename prefix."""
        clean_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = ' '.join(clean_name.split())  # Remove extra spaces
        return f"{self.SITENAME_PREFIX}_{clean_name}.{extension}"
    
    def __str__(self) -> str:
        """String representation of configuration (excluding sensitive data)."""
        config_items = []
        for attr_name in dir(self):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                value = getattr(self, attr_name)
                # Hide sensitive information
                if 'api_key' in attr_name.lower() or 'password' in attr_name.lower():
                    value = '***' if value else 'Not set'
                config_items.append(f"{attr_name}: {value}")
        
        return f"GRABIT Configuration:\n" + "\n".join(config_items)


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def validate_startup():
    """Validate configuration at startup and raise errors if invalid."""
    try:
        config.setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Configuration loaded and validated successfully")
        logger.debug(f"Configuration details:\n{config}")
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        raise e