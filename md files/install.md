# GRABIT Backend Installation Guide

This guide provides step-by-step instructions for setting up the GRABIT backend on your local machine. The setup process includes Python environment configuration, dependency installation, FFmpeg setup, and environment configuration.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+, CentOS 7+)
- **Python**: 3.8 or higher (3.10+ recommended)
- **Memory**: Minimum 2GB RAM, 4GB+ recommended for concurrent downloads
- **Storage**: 1GB+ free space for downloads and temporary files
- **Network**: Stable internet connection for video downloads

### Required Software

1. **Python 3.8+** with pip
2. **FFmpeg** (for high-quality video rendering)
3. **Git** (for cloning the repository)

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd grabit-backend
```

### 2. Python Environment Setup

#### Option A: Using Virtual Environment (Recommended)

**Windows:**
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify Python version
python --version
```

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify Python version
python --version
```

#### Option B: Using Conda

```bash
# Create conda environment
conda create -n grabit python=3.10

# Activate environment
conda activate grabit
```

### 3. Install Python Dependencies

```bash
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install all required dependencies
pip install -r requirements.txt

# Verify key packages are installed
python -c "import fastapi; import pytube; import yt_dlp; print('All packages installed successfully')"
```

### 4. FFmpeg Installation

FFmpeg is required for high-quality video rendering (>720p) and format conversion.

#### Windows Installation

**Option A: Download Pre-built Binaries (Recommended)**
1. Download FFmpeg from [https://ffmpeg.org/download.html#build-windows](https://ffmpeg.org/download.html#build-windows)
2. Extract to `C:\ffmpeg` or your preferred location
3. Add `C:\ffmpeg\bin` to your system PATH, or
4. Place FFmpeg binaries in `./ffmpeg/bin/` directory within the project

**Option B: Using Chocolatey**
```cmd
# Install using Chocolatey (if installed)
choco install ffmpeg

# Verify installation
ffmpeg -version
```

**Option C: Using Winget**
```cmd
# Install using Windows Package Manager
winget install FFmpeg

# Verify installation
ffmpeg -version
```

#### Linux Installation

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install FFmpeg
sudo apt install ffmpeg

# Verify installation
ffmpeg -version
```

**CentOS/RHEL/Fedora:**
```bash
# CentOS/RHEL (requires EPEL repository)
sudo yum install epel-release
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Verify installation
ffmpeg -version
```

**Arch Linux:**
```bash
# Install FFmpeg
sudo pacman -S ffmpeg

# Verify installation
ffmpeg -version
```

#### macOS Installation

**Using Homebrew (Recommended):**
```bash
# Install FFmpeg
brew install ffmpeg

# Verify installation
ffmpeg -version
```

**Using MacPorts:**
```bash
# Install FFmpeg
sudo port install ffmpeg

# Verify installation
ffmpeg -version
```

### 5. Environment Configuration

#### Create Environment File

Copy the example environment file and configure your settings:

```bash
# Copy example environment file
cp .env.example .env
```

#### Configure Environment Variables

Edit the `.env` file with your preferred settings:

```env
# Basic Configuration
SITENAME_PREFIX=GRABIT
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
WEBSOCKET_URL=ws://localhost:8000/ws

# FFmpeg Configuration
# Windows example: FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe
# Linux/macOS example: FFMPEG_PATH=/usr/bin/ffmpeg
FFMPEG_PATH=ffmpeg

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Download Configuration
MAX_CONCURRENT_DOWNLOADS=5
DEFAULT_DOWNLOAD_PATH=./downloads
TEMP_PATH=./temp

# Quality Settings
MAX_QUALITY_DIRECT=720
MIN_QUALITY=144

# WebSocket Settings
WS_HEARTBEAT_INTERVAL=30
WS_MAX_CONNECTIONS=100

# Security Settings
MAX_FILE_SIZE_MB=2048
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/grabit.log

# Development Settings
DEBUG=false
```

#### Environment Variable Details

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SITENAME_PREFIX` | Prefix for all downloaded files | GRABIT | Yes |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | localhost:3000,localhost:8080 | Yes |
| `WEBSOCKET_URL` | WebSocket URL for client connections | ws://localhost:8000/ws | Yes |
| `FFMPEG_PATH` | Path to FFmpeg executable | ffmpeg | Yes |
| `HOST` | Server bind address | 0.0.0.0 | No |
| `PORT` | Server port | 8000 | No |
| `WORKERS` | Number of worker processes | 4 | No |
| `MAX_CONCURRENT_DOWNLOADS` | Maximum concurrent downloads | 5 | No |
| `DEFAULT_DOWNLOAD_PATH` | Default download directory | ./downloads | No |
| `TEMP_PATH` | Temporary files directory | ./temp | No |
| `MAX_QUALITY_DIRECT` | Maximum quality for direct download | 720 | No |
| `MIN_QUALITY` | Minimum allowed quality | 144 | No |
| `WS_HEARTBEAT_INTERVAL` | WebSocket heartbeat interval (seconds) | 30 | No |
| `WS_MAX_CONNECTIONS` | Maximum WebSocket connections | 100 | No |
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | 2048 | No |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per minute | 60 | No |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO | No |
| `LOG_FILE` | Log file path | ./logs/grabit.log | No |
| `DEBUG` | Enable debug mode | false | No |

### 6. Directory Structure Setup

The application will automatically create necessary directories, but you can create them manually:

```bash
# Create required directories
mkdir -p downloads temp logs ffmpeg/bin

# Set appropriate permissions (Linux/macOS)
chmod 755 downloads temp logs
```

### 7. Verify Installation

#### Test Configuration

```bash
# Test configuration loading
python -c "from config import validate_startup; validate_startup(); print('Configuration valid!')"
```

#### Test Dependencies

```bash
# Test all imports
python -c "
import fastapi
import pytube
import yt_dlp
import uvicorn
import websockets
import pydantic
from dotenv import load_dotenv
print('All dependencies working correctly!')
"
```

#### Test FFmpeg Integration

```bash
# Test FFmpeg availability
python -c "
from config import get_config
config = get_config()
print(f'FFmpeg path: {config.FFMPEG_PATH}')
"
```

### 8. Run the Application

#### Development Mode

```bash
# Run with auto-reload (recommended for development)
python main.py

# Or using uvicorn directly
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode

```bash
# Set production environment
export DEBUG=false  # Linux/macOS
set DEBUG=false     # Windows

# Run production server
python main.py

# Or using gunicorn (Linux/macOS only)
pip install gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Verify Server is Running

1. **API Documentation**: Visit `http://localhost:8000/docs`
2. **Health Check**: Visit `http://localhost:8000/health`
3. **Server Status**: Visit `http://localhost:8000/status`

## Troubleshooting

### Common Installation Issues

#### 1. Python Version Issues

**Problem**: `ImportError` or syntax errors
**Solution**: Ensure Python 3.8+ is installed and activated

```bash
# Check Python version
python --version

# Update Python if needed
```

#### 2. FFmpeg Not Found

**Problem**: `FFmpeg binary not found` error
**Solutions**:

1. **Verify FFmpeg Installation**:
   ```bash
   ffmpeg -version
   ```

2. **Update Environment Variable**:
   ```env
   # In .env file, set full path to FFmpeg
   FFMPEG_PATH=/full/path/to/ffmpeg
   ```

3. **System PATH Issue**:
   - Windows: Add FFmpeg to system PATH
   - Linux/macOS: Install via package manager

#### 3. Permission Errors

**Problem**: Cannot create directories or files
**Solutions**:

1. **Check Directory Permissions**:
   ```bash
   # Linux/macOS
   chmod 755 downloads temp logs
   
   # Windows: Run as administrator if needed
   ```

2. **Change Download Path**:
   ```env
   # Use absolute path with write permissions
   DEFAULT_DOWNLOAD_PATH=/path/with/write/access
   ```

#### 4. Port Already in Use

**Problem**: `Port 8000 already in use`
**Solutions**:

1. **Change Port**:
   ```env
   PORT=8001
   ```

2. **Kill Existing Process**:
   ```bash
   # Linux/macOS
   lsof -ti:8000 | xargs kill -9
   
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

#### 5. Dependency Installation Failures

**Problem**: pip install errors
**Solutions**:

1. **Update pip**:
   ```bash
   python -m pip install --upgrade pip
   ```

2. **Use System Packages** (Linux):
   ```bash
   sudo apt install python3-dev build-essential
   ```

3. **Use Binary Wheels**:
   ```bash
   pip install --only-binary=all -r requirements.txt
   ```

#### 6. WebSocket Connection Issues

**Problem**: WebSocket connections failing
**Solutions**:

1. **Check Firewall**: Ensure port 8000 is open
2. **Update WebSocket URL**: Match your server configuration
3. **CORS Configuration**: Verify allowed origins

### Performance Optimization

#### 1. Concurrent Downloads

Adjust based on your system capabilities:

```env
# For high-end systems
MAX_CONCURRENT_DOWNLOADS=10

# For limited resources
MAX_CONCURRENT_DOWNLOADS=2
```

#### 2. Worker Processes

Optimize based on CPU cores:

```env
# Formula: (CPU cores * 2) + 1
WORKERS=9  # For 4-core system
```

#### 3. Memory Management

For systems with limited RAM:

```env
# Reduce concurrent operations
MAX_CONCURRENT_DOWNLOADS=3
WS_MAX_CONNECTIONS=50
```

### Log Analysis

#### Check Application Logs

```bash
# View recent logs
tail -f logs/grabit.log

# Search for errors
grep ERROR logs/grabit.log

# Check startup logs
head -n 50 logs/grabit.log
```

#### Enable Debug Logging

```env
# In .env file
LOG_LEVEL=DEBUG
DEBUG=true
```

## Next Steps

1. **API Testing**: Use the interactive documentation at `/docs`
2. **WebSocket Testing**: Connect to `/ws` endpoint for real-time updates
3. **Frontend Integration**: Connect your web/mobile frontend
4. **Production Deployment**: Configure reverse proxy and process management

## Support Resources

- **Documentation**: See `documentation.md` for complete API reference
- **Features**: See `features.md` for feature overview
- **Development**: See `plan.md` for development details
- **GitHub Issues**: Report problems and request features

## Security Considerations

### Production Deployment

1. **Environment Variables**: Never commit `.env` files to version control
2. **CORS Origins**: Restrict to known frontend domains
3. **Rate Limiting**: Configure appropriate limits for your use case
4. **File Permissions**: Ensure proper directory permissions
5. **Network Security**: Use HTTPS in production environments

### API Security

1. **Input Validation**: All inputs are validated by Pydantic models
2. **File Path Sanitization**: Prevents directory traversal attacks
3. **Resource Limits**: File size and concurrent download limits
4. **Error Information**: Limited error details in production mode

This installation guide should get you up and running with GRABIT backend quickly and efficiently!