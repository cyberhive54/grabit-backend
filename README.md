# GRABIT Backend API Documentation

This comprehensive guide provides detailed information about the GRABIT backend API, including endpoint specifications, request/response schemas, and integration examples for developers.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Data Models](#data-models)
4. [REST Endpoints](#rest-endpoints)
5. [WebSocket API](#websocket-api)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Integration Examples](#integration-examples)
9. [SDKs and Libraries](#sdks-and-libraries)

## API Overview

### Base URL
```
http://localhost:8000  # Development
https://api.yoursite.com  # Production
```

### Content Type
All requests and responses use `application/json` content type unless specified otherwise.

### API Versioning
Current API version: `v1` (embedded in URL structure)

### OpenAPI Documentation
Interactive API documentation is available at:
- **Swagger UI**: `{base_url}/docs`
- **ReDoc**: `{base_url}/redoc`
- **OpenAPI Schema**: `{base_url}/openapi.json`

## Authentication

**Current Version**: No authentication required (public API)

**Future Versions**: Will support API key authentication via headers:
```http
Authorization: Bearer YOUR_API_KEY
```

## Data Models

### Core Models

#### VideoMetadata
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "uploader": "string",
  "uploader_id": "string",
  "duration": "integer",
  "view_count": "integer",
  "like_count": "integer",
  "upload_date": "string (ISO 8601)",
  "thumbnail": "string (URL)",
  "video_type": "video|shorts|live|premiere",
  "formats": [
    {
      "quality": "string",
      "extension": "string",
      "filesize": "integer",
      "vcodec": "string",
      "acodec": "string",
      "fps": "number",
      "format_id": "string"
    }
  ],
  "subtitles": [
    {
      "language": "string",
      "language_code": "string",
      "auto_generated": "boolean",
      "url": "string"
    }
  ]
}
```

#### PlaylistMetadata
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "uploader": "string",
  "video_count": "integer",
  "videos": ["VideoMetadata[]"]
}
```

#### DownloadRequest
```json
{
  "url": "string (required)",
  "quality": "string (optional, default: best)",
  "format": "string (optional, default: mp4)",
  "include_subtitles": "boolean (optional, default: false)",
  "subtitle_languages": ["string[]"] | null,
  "include_thumbnail": "boolean (optional, default: false)",
  "output_path": "string (optional)"
}
```

#### PlaylistRequest
```json
{
  "url": "string (required)",
  "quality": "string (optional, default: best)",
  "format": "string (optional, default: mp4)",
  "include_subtitles": "boolean (optional, default: false)",
  "max_downloads": "integer (optional)",
  "start_index": "integer (optional, default: 0)",
  "end_index": "integer (optional)",
  "selected_videos": ["string[]"] | null,
  "reverse_order": "boolean (optional, default: false)"
}
```

#### BatchRequest
```json
{
  "urls": ["string[] (required)"],
  "quality": "string (optional, default: best)",
  "format": "string (optional, default: mp4)",
  "include_subtitles": "boolean (optional, default: false)",
  "max_concurrent": "integer (optional, default: 3)"
}
```

#### TaskStatus
```json
{
  "task_id": "string",
  "status": "pending|in_progress|completed|failed|cancelled",
  "progress": {
    "current": "integer",
    "total": "integer",
    "percentage": "number",
    "speed": "string",
    "eta": "string"
  },
  "result": {
    "downloaded_files": ["string[]"],
    "failed_downloads": ["object[]"],
    "metadata": "VideoMetadata|PlaylistMetadata"
  },
  "error": "string | null",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

## REST Endpoints

### 1. Extract Metadata

Extract video or playlist metadata without downloading.

#### Endpoint
```http
POST /extract
```

#### Request Body
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

#### Response
```json
{
  "success": true,
  "data": {
    // VideoMetadata or PlaylistMetadata object
  },
  "extraction_time": 1.23
}
```

#### cURL Example
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

#### JavaScript Example
```javascript
const response = await fetch('http://localhost:8000/extract', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
  })
});
const data = await response.json();
```

### 2. Single Video Download

Download a single video with specified options.

#### Endpoint
```http
POST /download/single
```

#### Request Body
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "720p",
  "format": "mp4",
  "include_subtitles": true,
  "subtitle_languages": ["en", "es"],
  "include_thumbnail": true
}
```

#### Response
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "message": "Download started successfully"
}
```

#### Quality Options
- `"144p"`, `"240p"`, `"360p"`, `"480p"`, `"720p"`, `"1080p"`, `"1440p"`, `"2160p"`
- `"best"` - Highest available quality
- `"worst"` - Lowest available quality
- `"audio"` - Audio only

#### Format Options
- `"mp4"` - MP4 container (default)
- `"webm"` - WebM container
- `"mkv"` - Matroska container
- `"mp3"` - Audio only (MP3)
- `"m4a"` - Audio only (M4A)

### 3. Playlist Download

Download videos from a YouTube playlist with filtering options.

#### Endpoint
```http
POST /download/playlist
```

#### Request Body
```json
{
  "url": "https://www.youtube.com/playlist?list=PLv2TTfvkOHvyRKqL4Qw1QRJo5Z-Rq5l4",
  "quality": "720p",
  "max_downloads": 10,
  "start_index": 0,
  "end_index": 9,
  "include_subtitles": false
}
```

#### Advanced Filtering
```json
{
  "url": "https://www.youtube.com/playlist?list=PLv2TTfvkOHvyRKqL4Qw1QRJo5Z-Rq5l4",
  "quality": "480p",
  "selected_videos": [
    "dQw4w9WgXcQ",
    "oHg5SJYRHA0"
  ],
  "reverse_order": true
}
```

### 4. Batch Download

Download multiple videos from different URLs.

#### Endpoint
```http
POST /download/batch
```

#### Request Body
```json
{
  "urls": [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=oHg5SJYRHA0",
    "https://www.youtube.com/playlist?list=PLv2TTfvkOHvyRKqL4Qw1QRJo5Z-Rq5l4"
  ],
  "quality": "720p",
  "max_concurrent": 3
}
```

### 5. Task Status

Get the current status and progress of a download task.

#### Endpoint
```http
GET /task/{task_id}
```

#### Response
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "in_progress",
  "progress": {
    "current": 5,
    "total": 10,
    "percentage": 50.0,
    "speed": "2.5 MB/s",
    "eta": "00:02:30"
  },
  "result": {
    "downloaded_files": [
      "GRABIT_Rick_Astley_Never_Gonna_Give_You_Up.mp4"
    ],
    "failed_downloads": [],
    "metadata": {
      // VideoMetadata object
    }
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:32:15Z"
}
```

### 6. Cancel Task

Cancel a running download task.

#### Endpoint
```http
DELETE /task/{task_id}
```

#### Response
```json
{
  "message": "Task cancelled successfully"
}
```

### 7. Download Thumbnail

Download video thumbnail without downloading the video.

#### Endpoint
```http
POST /thumbnail
```

#### Request Body
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "maxresdefault"
}
```

#### Quality Options
- `"maxresdefault"` - Maximum resolution (1280x720)
- `"hqdefault"` - High quality (480x360)
- `"mqdefault"` - Medium quality (320x180)
- `"default"` - Default quality (120x90)

#### Response
```json
{
  "success": true,
  "thumbnail_path": "downloads/GRABIT_Rick_Astley_Never_Gonna_Give_You_Up_thumbnail.jpg"
}
```

### 8. Download Subtitles

Download video subtitles in specified languages.

#### Endpoint
```http
POST /subtitles
```

#### Request Body
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "languages": ["en", "es", "fr"],
  "auto_generated": true
}
```

#### Response
```json
{
  "success": true,
  "subtitle_files": [
    {
      "language": "en",
      "path": "downloads/GRABIT_Rick_Astley_Never_Gonna_Give_You_Up_en.srt",
      "auto_generated": false
    },
    {
      "language": "es",
      "path": "downloads/GRABIT_Rick_Astley_Never_Gonna_Give_You_Up_es.srt",
      "auto_generated": true
    }
  ]
}
```

### 9. Server Status

Get server health and statistics.

#### Endpoint
```http
GET /status
```

#### Response
```json
{
  "version": "1.0.0",
  "active_downloads": 3,
  "total_downloads": 1547,
  "uptime": 86400,
  "memory_usage": 256.7,
  "max_concurrent_downloads": 10,
  "websocket_connections": 5
}
```

### 10. Health Check

Simple health check endpoint.

#### Endpoint
```http
GET /health
```

#### Response
```json
{
  "status": "healthy",
  "service": "GRABIT"
}
```

## WebSocket API

Real-time communication for download progress and status updates.

### Connection URL
```
ws://localhost:8000/ws
```

### Message Format

All WebSocket messages follow this structure:
```json
{
  "type": "progress|status|error|metadata",
  "task_id": "string",
  "timestamp": "ISO 8601 string",
  "data": {}
}
```

### Client Commands

#### Subscribe to Task
```json
{
  "command": "subscribe",
  "task_id": "abc123-def456-ghi789"
}
```

#### Unsubscribe from Task
```json
{
  "command": "unsubscribe",
  "task_id": "abc123-def456-ghi789"
}
```

#### Get Connection Stats
```json
{
  "command": "stats"
}
```

#### Ping/Heartbeat
```json
{
  "command": "ping"
}
```

### Server Messages

#### Progress Update
```json
{
  "type": "progress",
  "task_id": "abc123-def456-ghi789",
  "timestamp": "2024-01-15T10:32:15Z",
  "data": {
    "current": 5,
    "total": 10,
    "percentage": 50.0,
    "speed": "2.5 MB/s",
    "eta": "00:02:30",
    "current_file": "video_5.mp4"
  }
}
```

#### Status Update
```json
{
  "type": "status",
  "task_id": "abc123-def456-ghi789",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "status": "completed",
    "message": "Download completed successfully"
  }
}
```

#### Error Notification
```json
{
  "type": "error",
  "task_id": "abc123-def456-ghi789",
  "timestamp": "2024-01-15T10:33:00Z",
  "data": {
    "error": "Network timeout",
    "error_type": "NetworkError",
    "retryable": true
  }
}
```

#### Metadata Update
```json
{
  "type": "metadata",
  "task_id": "abc123-def456-ghi789",
  "timestamp": "2024-01-15T10:30:30Z",
  "data": {
    "extracted_videos": 10,
    "total_duration": "01:23:45",
    "estimated_size": "1.2 GB"
  }
}
```

### JavaScript WebSocket Example

```javascript
class GrabitWebSocket {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    this.ws.onopen = () => {
      console.log('Connected to GRABIT WebSocket');
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log('Disconnected from GRABIT WebSocket');
      // Implement reconnection logic
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  handleMessage(message) {
    switch (message.type) {
      case 'progress':
        this.updateProgress(message.task_id, message.data);
        break;
      case 'status':
        this.updateStatus(message.task_id, message.data);
        break;
      case 'error':
        this.handleError(message.task_id, message.data);
        break;
      case 'metadata':
        this.updateMetadata(message.task_id, message.data);
        break;
    }
  }

  subscribeToTask(taskId) {
    this.send({
      command: 'subscribe',
      task_id: taskId
    });
  }

  unsubscribeFromTask(taskId) {
    this.send({
      command: 'unsubscribe',
      task_id: taskId
    });
  }

  send(data) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  updateProgress(taskId, progress) {
    // Update UI with progress information
    const progressBar = document.getElementById(`progress-${taskId}`);
    if (progressBar) {
      progressBar.style.width = `${progress.percentage}%`;
      progressBar.textContent = `${progress.percentage.toFixed(1)}% - ${progress.speed}`;
    }
  }

  updateStatus(taskId, status) {
    // Update UI with status information
    console.log(`Task ${taskId} status: ${status.status}`);
  }

  handleError(taskId, error) {
    // Handle error notification
    console.error(`Task ${taskId} error:`, error.error);
  }

  updateMetadata(taskId, metadata) {
    // Update UI with metadata information
    console.log(`Task ${taskId} metadata:`, metadata);
  }
}

// Usage
const grabitWS = new GrabitWebSocket('ws://localhost:8000/ws');
```

## Error Handling

### HTTP Status Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid URL, parameters, or request format |
| 404 | Not Found | Task not found, video unavailable |
| 422 | Validation Error | Invalid request data format |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side processing error |
| 503 | Service Unavailable | Server overloaded or maintenance |

### Error Response Format

```json
{
  "error": "Detailed error message",
  "error_type": "ValidationError",
  "message": "A validation error occurred",
  "details": {
    "field": "url",
    "issue": "Invalid YouTube URL format"
  }
}
```

### Common Error Types

#### ValidationError
```json
{
  "error": "Invalid URL format",
  "error_type": "ValidationError",
  "message": "The provided URL is not a valid YouTube URL"
}
```

#### NetworkError
```json
{
  "error": "Failed to connect to YouTube",
  "error_type": "NetworkError",
  "message": "Network timeout while fetching video data",
  "retryable": true
}
```

#### VideoUnavailableError
```json
{
  "error": "Video is private or deleted",
  "error_type": "VideoUnavailableError",
  "message": "The requested video is not accessible"
}
```

#### QualityNotAvailableError
```json
{
  "error": "Requested quality not available",
  "error_type": "QualityNotAvailableError",
  "message": "1080p quality is not available for this video",
  "available_qualities": ["144p", "240p", "360p", "480p", "720p"]
}
```

## Rate Limiting

### Current Limits
- **API Requests**: 60 requests per minute per IP
- **Concurrent Downloads**: 5 simultaneous downloads per client
- **WebSocket Connections**: 100 maximum concurrent connections

### Rate Limit Headers
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642244400
```

### Rate Limit Response
```json
{
  "error": "Rate limit exceeded",
  "error_type": "RateLimitError",
  "message": "You have exceeded the maximum number of requests per minute",
  "retry_after": 60
}
```

## Integration Examples

### Python Integration

```python
import requests
import websocket
import json
import threading

class GrabitClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.ws = None
        
    def extract_metadata(self, url):
        response = requests.post(
            f"{self.base_url}/extract",
            json={"url": url}
        )
        return response.json()
    
    def download_video(self, url, quality="720p", include_subtitles=False):
        response = requests.post(
            f"{self.base_url}/download/single",
            json={
                "url": url,
                "quality": quality,
                "include_subtitles": include_subtitles
            }
        )
        return response.json()
    
    def get_task_status(self, task_id):
        response = requests.get(f"{self.base_url}/task/{task_id}")
        return response.json()
    
    def connect_websocket(self, on_message=None):
        def on_ws_message(ws, message):
            data = json.loads(message)
            if on_message:
                on_message(data)
        
        self.ws = websocket.WebSocketApp(
            f"ws://localhost:8000/ws",
            on_message=on_ws_message
        )
        
        # Run in separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
    
    def subscribe_to_task(self, task_id):
        if self.ws:
            self.ws.send(json.dumps({
                "command": "subscribe",
                "task_id": task_id
            }))

# Usage example
client = GrabitClient()

# Extract metadata
metadata = client.extract_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"Video title: {metadata['data']['title']}")

# Start download
download_result = client.download_video(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    quality="720p",
    include_subtitles=True
)
task_id = download_result['task_id']

# Connect WebSocket for progress updates
def handle_progress(message):
    if message['type'] == 'progress':
        progress = message['data']
        print(f"Progress: {progress['percentage']:.1f}% - {progress['speed']}")

client.connect_websocket(on_message=handle_progress)
client.subscribe_to_task(task_id)

# Check final status
import time
while True:
    status = client.get_task_status(task_id)
    if status['status'] in ['completed', 'failed', 'cancelled']:
        print(f"Download {status['status']}")
        break
    time.sleep(1)
```

### cURL Integration

```bash
#!/bin/bash

# Extract metadata
METADATA=$(curl -s -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}')

echo "Metadata: $METADATA"

# Start download
DOWNLOAD_RESULT=$(curl -s -X POST "http://localhost:8000/download/single" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "quality": "720p",
    "include_subtitles": true
  }')

TASK_ID=$(echo $DOWNLOAD_RESULT | jq -r '.task_id')
echo "Started download with task ID: $TASK_ID"

# Poll for completion
while true; do
  STATUS=$(curl -s "http://localhost:8000/task/$TASK_ID")
  CURRENT_STATUS=$(echo $STATUS | jq -r '.status')
  
  if [ "$CURRENT_STATUS" = "completed" ] || [ "$CURRENT_STATUS" = "failed" ]; then
    echo "Download $CURRENT_STATUS"
    echo "Final result: $STATUS"
    break
  fi
  
  PROGRESS=$(echo $STATUS | jq -r '.progress.percentage // 0')
  echo "Progress: $PROGRESS%"
  sleep 2
done
```

### Node.js Integration

```javascript
const axios = require('axios');
const WebSocket = require('ws');

class GrabitClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.ws = null;
  }

  async extractMetadata(url) {
    const response = await axios.post(`${this.baseUrl}/extract`, { url });
    return response.data;
  }

  async downloadVideo(url, options = {}) {
    const response = await axios.post(`${this.baseUrl}/download/single`, {
      url,
      ...options
    });
    return response.data;
  }

  async getTaskStatus(taskId) {
    const response = await axios.get(`${this.baseUrl}/task/${taskId}`);
    return response.data;
  }

  connectWebSocket(onMessage) {
    this.ws = new WebSocket('ws://localhost:8000/ws');
    
    this.ws.on('open', () => {
      console.log('Connected to GRABIT WebSocket');
    });

    this.ws.on('message', (data) => {
      const message = JSON.parse(data);
      if (onMessage) onMessage(message);
    });

    this.ws.on('close', () => {
      console.log('Disconnected from GRABIT WebSocket');
    });

    this.ws.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
  }

  subscribeToTask(taskId) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        command: 'subscribe',
        task_id: taskId
      }));
    }
  }

  async waitForCompletion(taskId, onProgress) {
    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const status = await this.getTaskStatus(taskId);
          
          if (onProgress) onProgress(status);
          
          if (['completed', 'failed', 'cancelled'].includes(status.status)) {
            resolve(status);
          } else {
            setTimeout(checkStatus, 1000);
          }
        } catch (error) {
          reject(error);
        }
      };
      
      checkStatus();
    });
  }
}

// Usage example
async function main() {
  const client = new GrabitClient();

  try {
    // Extract metadata
    const metadata = await client.extractMetadata('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    console.log(`Video title: ${metadata.data.title}`);

    // Start download with WebSocket progress
    client.connectWebSocket((message) => {
      if (message.type === 'progress') {
        console.log(`Progress: ${message.data.percentage.toFixed(1)}% - ${message.data.speed}`);
      }
    });

    const downloadResult = await client.downloadVideo('https://www.youtube.com/watch?v=dQw4w9WgXcQ', {
      quality: '720p',
      include_subtitles: true
    });

    const taskId = downloadResult.task_id;
    console.log(`Started download with task ID: ${taskId}`);

    client.subscribeToTask(taskId);

    // Wait for completion
    const finalStatus = await client.waitForCompletion(taskId, (status) => {
      console.log(`Status: ${status.status}`);
    });

    console.log('Download completed:', finalStatus);

  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

main();
```

## SDKs and Libraries

### Official SDKs (Planned)
- **Python SDK**: `pip install grabit-client`
- **JavaScript/Node.js SDK**: `npm install grabit-client`
- **Go SDK**: `go get github.com/grabit/go-client`

### Community Libraries
- Submit your community-developed SDKs via GitHub issues

This comprehensive API documentation provides everything needed to integrate with the GRABIT backend effectively. For additional support, refer to the interactive documentation at `/docs` or submit issues via GitHub.
