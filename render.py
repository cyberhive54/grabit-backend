"""
FFmpeg rendering module for GRABIT backend.
Handles combining high-quality audio and video using FFmpeg.
"""

import asyncio
import logging
import os
import subprocess
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class FFmpegRenderer:
    """Handles video rendering using FFmpeg."""
    
    def __init__(self):
        """Initialize the FFmpeg renderer."""
        self.ffmpeg_path = config.get_ffmpeg_command()
        self.output_path = config.DEFAULT_DOWNLOAD_PATH
        self.temp_path = config.TEMP_PATH
        
        # Ensure directories exist
        Path(self.output_path).mkdir(parents=True, exist_ok=True)
        Path(self.temp_path).mkdir(parents=True, exist_ok=True)
    
    async def render_video(self, video_path: str, audio_path: str, 
                          output_title: str, progress_callback: Optional[callable] = None) -> str:
        """
        Render video by combining video and audio streams.
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file  
            output_title: Title for output file
            progress_callback: Optional progress callback
            
        Returns:
            Path to rendered output file
        """
        logger.info(f"Starting FFmpeg render: {video_path} + {audio_path}")
        
        # Generate output filename
        safe_title = self._sanitize_filename(output_title)
        output_filename = config.get_download_filename(safe_title, "mp4")
        output_path = os.path.join(self.output_path, output_filename)
        
        # Ensure input files exist
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',  # Copy video stream without re-encoding
            '-c:a', 'aac',   # Re-encode audio to AAC
            '-b:a', '128k',  # Audio bitrate
            '-movflags', '+faststart',  # Optimize for web streaming
            '-y',  # Overwrite output file
            output_path
        ]
        
        try:
            # Run FFmpeg in executor
            loop = asyncio.get_event_loop()
            
            def run_ffmpeg():
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, cmd, output=stdout, stderr=stderr
                    )
                
                return output_path
            
            result_path = await loop.run_in_executor(None, run_ffmpeg)
            
            logger.info(f"FFmpeg render completed: {result_path}")
            return result_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e.stderr}")
            raise RuntimeError(f"FFmpeg rendering failed: {e.stderr}")
        except Exception as e:
            logger.error(f"FFmpeg render error: {e}")
            raise e
    
    async def extract_audio(self, video_path: str, output_title: str) -> str:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to video file
            output_title: Title for output file
            
        Returns:
            Path to extracted audio file
        """
        logger.info(f"Extracting audio from: {video_path}")
        
        # Generate output filename
        safe_title = self._sanitize_filename(output_title)
        output_filename = config.get_download_filename(safe_title, "mp3")
        output_path = os.path.join(self.output_path, output_filename)
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'mp3',
            '-ab', '192k',
            '-ar', '44100',
            '-y',
            output_path
        ]
        
        try:
            loop = asyncio.get_event_loop()
            
            def run_ffmpeg():
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, cmd, output=stdout, stderr=stderr
                    )
                
                return output_path
            
            result_path = await loop.run_in_executor(None, run_ffmpeg)
            
            logger.info(f"Audio extraction completed: {result_path}")
            return result_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio extraction failed: {e.stderr}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr}")
    
    async def convert_format(self, input_path: str, output_format: str, output_title: str) -> str:
        """
        Convert video to different format.
        
        Args:
            input_path: Path to input file
            output_format: Target format (mp4, mkv, webm)
            output_title: Title for output file
            
        Returns:
            Path to converted file
        """
        logger.info(f"Converting {input_path} to {output_format}")
        
        # Generate output filename
        safe_title = self._sanitize_filename(output_title)
        output_filename = config.get_download_filename(safe_title, output_format)
        output_path = os.path.join(self.output_path, output_filename)
        
        # Build FFmpeg command based on format
        if output_format == "mp4":
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
        elif output_format == "mkv":
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-y',
                output_path
            ]
        elif output_format == "webm":
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', 'libvpx-vp9',
                '-c:a', 'libvorbis',
                '-y',
                output_path
            ]
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        try:
            loop = asyncio.get_event_loop()
            
            def run_ffmpeg():
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, cmd, output=stdout, stderr=stderr
                    )
                
                return output_path
            
            result_path = await loop.run_in_executor(None, run_ffmpeg)
            
            logger.info(f"Format conversion completed: {result_path}")
            return result_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Format conversion failed: {e.stderr}")
            raise RuntimeError(f"Format conversion failed: {e.stderr}")
    
    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video file information using FFprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video information
        """
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        try:
            loop = asyncio.get_event_loop()
            
            def run_ffprobe():
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, cmd, output=stdout, stderr=stderr
                    )
                
                import json
                return json.loads(stdout)
            
            return await loop.run_in_executor(None, run_ffprobe)
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {}
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename.strip()
    
    def is_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                check=True
            )
            return True
        except Exception:
            return False
    
    def get_supported_codecs(self) -> List[str]:
        """Get list of supported codecs."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-codecs'],
                capture_output=True,
                text=True,
                check=True
            )
            # Parse codec list from output
            # This is a simplified version
            return ['h264', 'vp9', 'av1', 'aac', 'mp3', 'vorbis']
        except Exception:
            return []


# Global renderer instance
_renderer = None


def get_renderer() -> FFmpegRenderer:
    """Get the global FFmpeg renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = FFmpegRenderer()
    return _renderer


async def render_video(video_path: str, audio_path: str, output_title: str,
                      progress_callback: Optional[callable] = None) -> str:
    """
    Render video by combining video and audio streams.
    
    Args:
        video_path: Path to video file
        audio_path: Path to audio file
        output_title: Title for output file
        progress_callback: Optional progress callback
        
    Returns:
        Path to rendered output file
    """
    renderer = get_renderer()
    return await renderer.render_video(video_path, audio_path, output_title, progress_callback)


async def extract_audio(video_path: str, output_title: str) -> str:
    """
    Extract audio from video file.
    
    Args:
        video_path: Path to video file
        output_title: Title for output file
        
    Returns:
        Path to extracted audio file
    """
    renderer = get_renderer()
    return await renderer.extract_audio(video_path, output_title)


async def convert_format(input_path: str, output_format: str, output_title: str) -> str:
    """
    Convert video to different format.
    
    Args:
        input_path: Path to input file
        output_format: Target format
        output_title: Title for output file
        
    Returns:
        Path to converted file
    """
    renderer = get_renderer()
    return await renderer.convert_format(input_path, output_format, output_title)