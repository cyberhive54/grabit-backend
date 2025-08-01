// GRABIT Frontend - Real API Integration
// Configuration
const API_BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

// Global variables
let currentMainTab = "single";
let currentFormatTab = "video";
let websocket = null;
let isProcessing = false;
let activeDownloads = new Map();
let currentVideoData = null;
let currentPlaylistData = null;
let currentBatchData = null;

// DOM elements
const mainTabBtns = document.querySelectorAll(".main-tab-btn");
const mainTabContents = document.querySelectorAll(".main-tab-content");
const formatTabBtns = document.querySelectorAll(".format-tab-btn");
const formatContents = document.querySelectorAll(".format-content");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");
const progressFill = document.querySelector(".progress-fill");
const videoDetails = document.getElementById("video-details");
const formatTabs = document.querySelector(".format-tabs");
const batchTextarea = document.getElementById("batch-urls");
const urlCount = document.querySelector(".url-count");
const faqItems = document.querySelectorAll(".faq-item");
const progressPanel = document.getElementById("progress-panel");
const progressList = document.getElementById("progress-list");

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
    initializeMainTabs();
    initializeFormatTabs();
    initializeFAQ();
    initializeBatchCounter();
    initializeMobileMenu();
    initializeSmoothScrolling();
    initializeWebSocket();
    handleScrollAnimations();
});

// WebSocket connection
function initializeWebSocket() {
    try {
        websocket = new WebSocket(WS_URL);
        
        websocket.onopen = function(event) {
            console.log('WebSocket connected to GRABIT backend');
        };
        
        websocket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        websocket.onclose = function(event) {
            console.log('WebSocket disconnected, attempting to reconnect...');
            setTimeout(initializeWebSocket, 3000);
        };
        
        websocket.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setTimeout(initializeWebSocket, 5000);
    }
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    const { type, task_id, status, progress, message, error } = data;
    
    switch (type) {
        case 'extraction_progress':
            updateExtractionProgress(task_id, progress, message);
            break;
        case 'download_progress':
            updateDownloadProgress(task_id, progress, message);
            break;
        case 'render_progress':
            updateRenderProgress(task_id, progress, message);
            break;
        case 'task_complete':
            handleTaskComplete(task_id, data);
            break;
        case 'task_error':
          handleTaskError(task_id, error);
          break;
        case 'status':
          console.log('Backend status:', data);
          break;
        case 'heartbeat':
          console.log('Backend heartbeat received');
          break;
        default:
          console.log('Unknown WebSocket message type:', type, data);
    }
}

// Main tab functionality
function initializeMainTabs() {
    mainTabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            switchMainTab(tabId);
        });
    });
}

function switchMainTab(tabId) {
    mainTabBtns.forEach((btn) => {
        btn.classList.remove("active");
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        }
    });

    mainTabContents.forEach((content) => {
        content.classList.remove("active");
        if (content.id === `${tabId}-tab`) {
            content.classList.add("active");
        }
    });

    currentMainTab = tabId;
}

// Format tab functionality
function initializeFormatTabs() {
    formatTabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const formatId = btn.getAttribute("data-format");
            switchFormatTab(formatId);
        });
    });
}

function switchFormatTab(formatId) {
    formatTabBtns.forEach((btn) => {
        btn.classList.remove("active");
        if (btn.getAttribute("data-format") === formatId) {
            btn.classList.add("active");
        }
    });

    formatContents.forEach((content) => {
        content.classList.remove("active");
        if (content.id === `${formatId}-formats`) {
            content.classList.add("active");
        }
    });

    currentFormatTab = formatId;
}

// FAQ functionality
function initializeFAQ() {
    faqItems.forEach((item) => {
        const question = item.querySelector(".faq-question");
        question.addEventListener("click", () => {
            const isActive = item.classList.contains("active");
            faqItems.forEach((faqItem) => {
                faqItem.classList.remove("active");
            });
            if (!isActive) {
                item.classList.add("active");
            }
        });
    });
}

// Batch URL counter
function initializeBatchCounter() {
    if (batchTextarea) {
        batchTextarea.addEventListener("input", updateUrlCount);
    }
}

function updateUrlCount() {
    const text = batchTextarea.value.trim();
    const urls = text ? text.split("\n").filter((line) => line.trim() !== "") : [];
    const validUrls = urls.filter((url) => isValidYouTubeUrl(url.trim()));
    urlCount.textContent = `${validUrls.length} valid URLs detected`;
}

// Mobile menu functionality
function initializeMobileMenu() {
    const mobileMenuBtn = document.querySelector(".mobile-menu-btn");
    const nav = document.querySelector(".nav");

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener("click", () => {
            nav.classList.toggle("active");
        });
    }
}

// Smooth scrolling for navigation links
function initializeSmoothScrolling() {
    const navLinks = document.querySelectorAll(".nav-link");
    navLinks.forEach((link) => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const targetId = link.getAttribute("href").substring(1);
            const targetElement = document.getElementById(targetId);

            if (targetElement) {
                const headerHeight = document.querySelector(".header").offsetHeight;
                const targetPosition = targetElement.offsetTop - headerHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: "smooth",
                });
            }
        });
    });
}

// URL validation
function isValidYouTubeUrl(url) {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|playlist\?list=)|youtu\.be\/)/;
    return youtubeRegex.test(url);
}

// API Helper functions
async function makeAPIRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Loading overlay functions
function showLoading(text = "Processing...") {
    loadingText.textContent = text;
    progressFill.style.width = "0%";
    loadingOverlay.classList.add("active");
    isProcessing = true;
}

function hideLoading() {
    loadingOverlay.classList.remove("active");
    isProcessing = false;
}

function updateLoadingProgress(progress, text) {
    progressFill.style.width = `${progress}%`;
    if (text) loadingText.textContent = text;
}

// Notification system
function showNotification(message, type = "info") {
    const container = document.getElementById("notification-container");
    if (!container) return;

    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Video Analysis Functions
async function analyzeVideo() {
    const urlInput = document.getElementById("video-url");
    const url = urlInput.value.trim();

    if (!url) {
        showNotification("Please enter a YouTube URL", "error");
        return;
    }

    if (!isValidYouTubeUrl(url)) {
        showNotification("Please enter a valid YouTube URL", "error");
        return;
    }

    try {
        showLoading("Extracting video metadata...");
        
        const response = await makeAPIRequest('/extract', {
            method: 'POST',
            body: JSON.stringify({ url: url })
        });

        currentVideoData = response;
        hideLoading();
        displayVideoDetails(response);
        showFormatOptions(response);
        showNotification("Video analyzed successfully!", "success");
        
    } catch (error) {
        hideLoading();
        showNotification(`Analysis failed: ${error.message}`, "error");
        console.error('Video analysis error:', error);
    }
}

async function analyzePlaylist() {
    const urlInput = document.getElementById("playlist-url");
    const url = urlInput.value.trim();

    if (!url) {
        showNotification("Please enter a YouTube playlist URL", "error");
        return;
    }

    if (!isValidYouTubeUrl(url)) {
        showNotification("Please enter a valid YouTube playlist URL", "error");
        return;
    }

    try {
        showLoading("Extracting playlist metadata...");
        
        const response = await makeAPIRequest('/extract', {
            method: 'POST',
            body: JSON.stringify({ url: url })
        });

        currentPlaylistData = response;
        hideLoading();
        displayPlaylistResults(response);
        showNotification(`Playlist analyzed successfully! Found ${response.videos.length} videos.`, "success");
        
    } catch (error) {
        hideLoading();
        showNotification(`Playlist analysis failed: ${error.message}`, "error");
        console.error('Playlist analysis error:', error);
    }
}

async function analyzeBatch() {
    const urls = batchTextarea.value
        .trim()
        .split("\n")
        .filter((line) => line.trim() !== "");
    const validUrls = urls.filter((url) => isValidYouTubeUrl(url.trim()));

    if (validUrls.length === 0) {
        showNotification("Please enter valid YouTube URLs", "error");
        return;
    }

    try {
        showLoading("Analyzing batch URLs...");
        
        const response = await makeAPIRequest('/extract', {
            method: 'POST',
            body: JSON.stringify({ urls: validUrls })
        });

        currentBatchData = response;
        hideLoading();
        displayBatchResults(response);
        showNotification(`Batch analyzed successfully! Found ${response.videos.length} videos.`, "success");
        
    } catch (error) {
        hideLoading();
        showNotification(`Batch analysis failed: ${error.message}`, "error");
        console.error('Batch analysis error:', error);
    }
}

// Display Functions
function displayVideoDetails(data) {
    const video = data.videos[0]; // Single video

    document.getElementById("video-title").textContent = video.title;
    document.getElementById("video-thumb").src = video.thumbnail_url;
    document.getElementById("upload-date").textContent = formatDate(video.publish_date);
    document.getElementById("view-count").textContent = formatNumber(video.view_count) + " views";
    document.getElementById("duration").textContent = formatDuration(video.length);
    document.getElementById("channel-name").textContent = video.uploader;
    document.getElementById("description-text").textContent = video.description;

    // Show subtitle download button if available
    const subtitleBtn = document.getElementById("subtitle-download");
    if (video.has_subtitles) {
        subtitleBtn.style.display = "inline-block";
    } else {
        subtitleBtn.style.display = "none";
    }

    videoDetails.classList.add("active");
}

function showFormatOptions(data) {
    const video = data.videos[0];
    
    // Populate video formats
    const videoGrid = document.getElementById("video-format-grid");
    videoGrid.innerHTML = '';
    
    video.formats.video.forEach(format => {
        const formatCard = createFormatCard(format, 'video');
        videoGrid.appendChild(formatCard);
    });

    // Populate audio formats
    const audioGrid = document.getElementById("audio-format-grid");
    audioGrid.innerHTML = '';
    
    video.formats.audio.forEach(format => {
        const formatCard = createFormatCard(format, 'audio');
        audioGrid.appendChild(formatCard);
    });

    formatTabs.classList.add("active");
    document.getElementById("video-formats").classList.add("active");
}

function createFormatCard(format, type) {
    const card = document.createElement('div');
    card.className = 'format-card';
    
    const requiresRender = format.quality && (
        (type === 'video' && (format.quality.includes('1080p') || format.quality.includes('4K') || format.quality.includes('8K'))) ||
        (type === 'audio' && (format.quality.includes('FLAC') || format.quality.includes('WAV') || format.quality.includes('AAC')))
    );
    
    if (requiresRender) {
        card.setAttribute('data-requires-render', 'true');
    }

    card.innerHTML = `
        <div class="format-info">
            <span class="format-quality">${format.quality}</span>
            <span class="format-details">${format.format} • ${format.quality_note || 'Standard'}</span>
            <span class="format-size">${format.filesize_approx || 'Unknown size'}</span>
        </div>
        <div class="format-actions">
            <button class="download-format-btn ${requiresRender ? 'render-btn' : 'download-btn'}" 
                    data-action="${requiresRender ? 'render' : 'download'}"
                    data-format='${JSON.stringify(format)}'
                    data-type="${type}">
                <i class="fas ${requiresRender ? 'fa-cog' : 'fa-download'}"></i>
                <span>${requiresRender ? 'Render' : 'Download'}</span>
            </button>
        </div>
    `;

    return card;
}

function displayPlaylistResults(data) {
    document.getElementById("playlist-count").textContent = `Found ${data.videos.length} videos in the playlist`;
    
    const playlistVideos = document.getElementById("playlist-videos");
    playlistVideos.innerHTML = '';

    data.videos.forEach((video, index) => {
        const videoItem = createVideoItem(video, index, 'playlist');
        playlistVideos.appendChild(videoItem);
    });

    document.getElementById("playlist-results").classList.add("active");
    document.getElementById("playlist-results").scrollIntoView({ behavior: "smooth" });
}

function displayBatchResults(data) {
    document.getElementById("batch-count").textContent = `Found ${data.videos.length} videos from batch URLs`;
    
    const batchVideos = document.getElementById("batch-videos");
    batchVideos.innerHTML = '';

    data.videos.forEach((video, index) => {
        const videoItem = createVideoItem(video, index, 'batch');
        batchVideos.appendChild(videoItem);
    });

    document.getElementById("batch-results").classList.add("active");
    document.getElementById("batch-results").scrollIntoView({ behavior: "smooth" });
}

function createVideoItem(video, index, type) {
    const videoItem = document.createElement('div');
    videoItem.className = 'video-item';
    videoItem.setAttribute('data-video-id', video.video_id);
    videoItem.setAttribute('data-index', index);

    videoItem.innerHTML = `
        <input type="checkbox" class="${type}-video-checkbox" onchange="updateSelectionCount('${type}')">
        <div class="video-thumbnail-container">
            <img src="${video.thumbnail_url}" alt="Video Thumbnail">
            <button class="video-download-btn" onclick="downloadSingleVideo('${video.video_id}', ${index})">
                <i class="fas fa-download"></i>
            </button>
        </div>
        <h4 class="video-item-title">${video.title}</h4>
        <div class="video-item-meta">
            <div class="video-meta-item">
                <i class="fas fa-clock"></i>
                <span>${formatDuration(video.length)}</span>
            </div>
            <div class="video-meta-item">
                <i class="fas fa-eye"></i>
                <span>${formatNumber(video.view_count)} views</span>
            </div>
            <div class="video-meta-item">
                <i class="fas fa-calendar"></i>
                <span>${formatDate(video.publish_date)}</span>
            </div>
        </div>
        <button class="video-description-toggle" onclick="toggleVideoDescription(this)">
            <i class="fas fa-chevron-down"></i>
            <span>Show Description</span>
        </button>
        <div class="video-description-content">
            <button class="video-copy-description" onclick="copyVideoDescription(this)">
                <i class="fas fa-copy"></i> Copy
            </button>
            <div class="video-description-text">${video.description}</div>
        </div>
    `;

    return videoItem;
}

// Download Functions
document.addEventListener("click", async (e) => {
    if (e.target.closest(".download-format-btn")) {
        e.preventDefault();
        const btn = e.target.closest(".download-format-btn");
        const formatData = JSON.parse(btn.getAttribute("data-format"));
        const type = btn.getAttribute("data-type");
        const action = btn.getAttribute("data-action");

        if (action === "render") {
            await startRenderDownload(formatData, type);
        } else {
            await startDirectDownload(formatData, type);
        }
    }
});

async function startDirectDownload(format, type) {
    if (!currentVideoData) {
        showNotification("No video data available", "error");
        return;
    }

    try {
        const video = currentVideoData.videos[0];
        
        const response = await makeAPIRequest('/download/single', {
            method: 'POST',
            body: JSON.stringify({
                url: video.url,
                quality: format.quality,
                format: format.format,
                download_subtitles: false
            })
        });

        showProgressPanel();
        addProgressItem(response.task_id, video.title, format.quality);
        showNotification(`Download started for ${format.quality}`, "success");
        
    } catch (error) {
        showNotification(`Download failed: ${error.message}`, "error");
        console.error('Download error:', error);
    }
}

async function startRenderDownload(format, type) {
    if (!currentVideoData) {
        showNotification("No video data available", "error");
        return;
    }

    try {
        const video = currentVideoData.videos[0];
        
        const response = await makeAPIRequest('/download/single', {
            method: 'POST',
            body: JSON.stringify({
                url: video.url,
                quality: format.quality,
                format: format.format,
                download_subtitles: false
            })
        });

        showProgressPanel();
        addProgressItem(response.task_id, video.title, format.quality, true);
        showNotification(`Render started for ${format.quality}`, "success");
        
    } catch (error) {
        showNotification(`Render failed: ${error.message}`, "error");
        console.error('Render error:', error);
    }
}

// Playlist Download Functions
async function downloadSelectedPlaylist() {
    const selectedCheckboxes = document.querySelectorAll('.playlist-video-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        showNotification("Please select videos to download", "error");
        return;
    }

    const selectedVideos = Array.from(selectedCheckboxes).map(checkbox => {
        const videoItem = checkbox.closest('.video-item');
        const index = parseInt(videoItem.getAttribute('data-index'));
        return currentPlaylistData.videos[index];
    });

    const quality = document.getElementById('quality-select').value;
    await downloadPlaylistVideos(selectedVideos, quality);
}

async function downloadAllPlaylist() {
    if (!currentPlaylistData) {
        showNotification("No playlist data available", "error");
        return;
    }

    const quality = document.getElementById('quality-select').value;
    await downloadPlaylistVideos(currentPlaylistData.videos, quality);
}

async function downloadPlaylistVideos(videos, quality) {
    try {
        const urls = videos.map(video => video.url);
        
        const response = await makeAPIRequest('/download/playlist', {
            method: 'POST',
            body: JSON.stringify({
                urls: urls,
                quality: quality,
                format: "mp4"
            })
        });

        showProgressPanel();
        addProgressItem(response.task_id, `Playlist (${videos.length} videos)`, quality);
        showNotification(`Playlist download started`, "success");
        
    } catch (error) {
        showNotification(`Playlist download failed: ${error.message}`, "error");
        console.error('Playlist download error:', error);
    }
}

// Batch Download Functions
async function downloadSelectedBatch() {
    const selectedCheckboxes = document.querySelectorAll('.batch-video-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        showNotification("Please select videos to download", "error");
        return;
    }

    const selectedVideos = Array.from(selectedCheckboxes).map(checkbox => {
        const videoItem = checkbox.closest('.video-item');
        const index = parseInt(videoItem.getAttribute('data-index'));
        return currentBatchData.videos[index];
    });

    const quality = document.getElementById('batch-quality-select').value;
    await downloadBatchVideos(selectedVideos, quality);
}

async function downloadAllBatch() {
    if (!currentBatchData) {
        showNotification("No batch data available", "error");
        return;
    }

    const quality = document.getElementById('batch-quality-select').value;
    await downloadBatchVideos(currentBatchData.videos, quality);
}

async function downloadBatchVideos(videos, quality) {
    try {
        const urls = videos.map(video => video.url);
        
        const response = await makeAPIRequest('/download/batch', {
            method: 'POST',
            body: JSON.stringify({
                urls: urls,
                quality: quality,
                format: "mp4"
            })
        });

        showProgressPanel();
        addProgressItem(response.task_id, `Batch (${videos.length} videos)`, quality);
        showNotification(`Batch download started`, "success");
        
    } catch (error) {
        showNotification(`Batch download failed: ${error.message}`, "error");
        console.error('Batch download error:', error);
    }
}

// Thumbnail and Subtitle Downloads
async function downloadThumbnail() {
    if (!currentVideoData) {
        showNotification("No video data available", "error");
        return;
    }

    try {
        const video = currentVideoData.videos[0];
        
        const response = await makeAPIRequest('/thumbnail', {
            method: 'POST',
            body: JSON.stringify({
                url: video.url
            })
        });

        // Create download link
        const link = document.createElement('a');
        link.href = response.download_url;
        link.download = response.filename;
        link.click();
        
        showNotification("Thumbnail download started!", "success");
        
    } catch (error) {
        showNotification(`Thumbnail download failed: ${error.message}`, "error");
        console.error('Thumbnail download error:', error);
    }
}

async function downloadSubtitles() {
    if (!currentVideoData) {
        showNotification("No video data available", "error");
        return;
    }

    try {
        const video = currentVideoData.videos[0];
        
        const response = await makeAPIRequest('/subtitles', {
            method: 'POST',
            body: JSON.stringify({
                url: video.url
            })
        });

        // Create download link
        const link = document.createElement('a');
        link.href = response.download_url;
        link.download = response.filename;
        link.click();
        
        showNotification("Subtitles download started!", "success");
        
    } catch (error) {
        showNotification(`Subtitles download failed: ${error.message}`, "error");
        console.error('Subtitles download error:', error);
    }
}

// Progress Panel Functions
function showProgressPanel() {
    progressPanel.classList.add("active");
}

function hideProgressPanel() {
    progressPanel.classList.remove("active");
}

function addProgressItem(taskId, title, quality, isRender = false) {
    const progressItem = document.createElement('div');
    progressItem.className = 'progress-item';
    progressItem.setAttribute('data-task-id', taskId);

    progressItem.innerHTML = `
        <div class="progress-info">
            <h4>${title}</h4>
            <span class="progress-quality">${quality} • ${isRender ? 'Rendering' : 'Downloading'}</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill"></div>
            <span class="progress-text">0%</span>
        </div>
        <div class="progress-actions">
            <button class="cancel-btn" onclick="cancelDownload('${taskId}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    progressList.appendChild(progressItem);
    activeDownloads.set(taskId, progressItem);
}

async function cancelDownload(taskId) {
    try {
        await makeAPIRequest(`/task/${taskId}`, {
            method: 'DELETE'
        });
        
        const progressItem = activeDownloads.get(taskId);
        if (progressItem) {
            progressItem.remove();
            activeDownloads.delete(taskId);
        }
        
        showNotification("Download cancelled", "info");
        
    } catch (error) {
        showNotification(`Failed to cancel download: ${error.message}`, "error");
        console.error('Cancel download error:', error);
    }
}

// Progress Update Functions
function updateExtractionProgress(taskId, progress, message) {
    updateLoadingProgress(progress, message);
}

function updateDownloadProgress(taskId, progress, message) {
    const progressItem = activeDownloads.get(taskId);
    if (progressItem) {
        const progressBar = progressItem.querySelector('.progress-fill');
        const progressText = progressItem.querySelector('.progress-text');
        
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${Math.round(progress)}%`;
    }
}

function updateRenderProgress(taskId, progress, message) {
    updateDownloadProgress(taskId, progress, message);
}

function handleTaskComplete(taskId, data) {
    const progressItem = activeDownloads.get(taskId);
    if (progressItem) {
        const progressBar = progressItem.querySelector('.progress-fill');
        const progressText = progressItem.querySelector('.progress-text');
        
        progressBar.style.width = '100%';
        progressText.textContent = 'Complete';
        progressItem.classList.add('complete');
        
        // Add download button
        const actions = progressItem.querySelector('.progress-actions');
        actions.innerHTML = `
            <a href="${data.download_url}" download="${data.filename}" class="download-complete-btn">
                <i class="fas fa-download"></i>
            </a>
        `;
        
        showNotification(`Download complete: ${data.filename}`, "success");
        
        // Remove from active downloads after 5 seconds
        setTimeout(() => {
            progressItem.remove();
            activeDownloads.delete(taskId);
        }, 5000);
    }
}

function handleTaskError(taskId, error) {
    const progressItem = activeDownloads.get(taskId);
    if (progressItem) {
        progressItem.classList.add('error');
        const progressText = progressItem.querySelector('.progress-text');
        progressText.textContent = 'Error';
        
        showNotification(`Download failed: ${error}`, "error");
    }
}

// Selection count functions
function updateSelectionCount(type) {
    const checkboxes = document.querySelectorAll(`.${type}-video-checkbox:checked`);
    const count = checkboxes.length;
    const badge = document.getElementById(`${type === 'playlist' ? 'selection' : 'batch-selection'}-count`);
    const button = document.getElementById(`${type === 'playlist' ? 'download-selected' : 'batch-download-selected'}`);
    
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-block';
        button.disabled = false;
    } else {
        badge.style.display = 'none';
        button.disabled = true;
    }
}

// Utility functions
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

// Description functions
function toggleDescription() {
    const descContent = document.getElementById("description-content");
    const toggle = document.querySelector(".description-toggle");
    const icon = toggle.querySelector("i");
    const text = toggle.querySelector("span");

    if (descContent.classList.contains("active")) {
        descContent.classList.remove("active");
        icon.className = "fas fa-chevron-down";
        text.textContent = "Show Description";
    } else {
        descContent.classList.add("active");
        icon.className = "fas fa-chevron-up";
        text.textContent = "Hide Description";
    }
}

function copyDescription() {
    const descText = document.getElementById("description-text").textContent;
    navigator.clipboard
        .writeText(descText)
        .then(() => {
            showNotification("Description copied to clipboard!", "success");
        })
        .catch(() => {
            showNotification("Failed to copy description", "error");
        });
}

function toggleVideoDescription(button) {
    const videoItem = button.closest(".video-item");
    const descContent = videoItem.querySelector(".video-description-content");
    const icon = button.querySelector("i");
    const text = button.querySelector("span");

    if (descContent.classList.contains("active")) {
        descContent.classList.remove("active");
        icon.className = "fas fa-chevron-down";
        text.textContent = "Show Description";
    } else {
        descContent.classList.add("active");
        icon.className = "fas fa-chevron-up";
        text.textContent = "Hide Description";
    }
}

function copyVideoDescription(button) {
    const descText = button.nextElementSibling.textContent;
    navigator.clipboard
        .writeText(descText)
        .then(() => {
            showNotification("Description copied to clipboard!", "success");
        })
        .catch(() => {
            showNotification("Failed to copy description", "error");
        });
}

// Tool popup functions (placeholder)
function openToolPopup() {
    showNotification("Additional tools coming soon!", "info");
}

function openMoreDownloaders() {
    const popup = document.getElementById("more-downloaders-popup");
    popup.classList.add("active");
}

function closeMoreDownloaders() {
    const popup = document.getElementById("more-downloaders-popup");
    popup.classList.remove("active");
}

function searchDownloaders(query) {
    const cards = document.querySelectorAll(".popup-tool-card");
    cards.forEach(card => {
        const title = card.querySelector("h5").textContent.toLowerCase();
        const desc = card.querySelector("p").textContent.toLowerCase();
        const searchTerm = query.toLowerCase();
        
        if (title.includes(searchTerm) || desc.includes(searchTerm)) {
            card.style.display = "block";
        } else {
            card.style.display = "none";
        }
    });
}

// Scroll animations (placeholder)
function handleScrollAnimations() {
    // Add scroll-based animations here if needed
}

console.log('GRABIT Frontend initialized and connected to backend API');