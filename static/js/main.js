/**
 * People Counter Application
 * Frontend JavaScript for visualizing detection, tracking, and counting data
 */

// Global variables
let updateFrequency = 300; // Default update frequency in milliseconds
let confidenceThreshold = 0.5; // Default confidence threshold
let lastUpdateTime = null;
let updateIntervalId = null;

// Person tracking data
let trackedPeople = [];
let countingLine = { x: 320 }; // Default line position
let totalCount = 0;

// Canvas dimensions (based on detection output)
const canvasWidth = 640;
const canvasHeight = 480;

// Colors for visualization
const colors = {
    detectionBox: '#2ecc71',
    trackingPath: '#3498db',
    countingLine: '#e74c3c',
    crossedPerson: '#f1c40f'
};

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCanvas();
    initializeChart();
    initializeControls();
    
    // Set up the animation loop
    requestAnimationFrame(renderLoop);
    
    // Start fetching data
    startDataUpdates();
});

/**
 * Start periodic data updates
 */
function startDataUpdates() {
    // Fetch data immediately
    fetchData();
    
    // Set up interval for periodic updates
    updateIntervalId = setInterval(fetchData, updateFrequency);
}

/**
 * Fetch data from the API
 */
function fetchData() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            handleDataUpdate(data);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
            updateConnectionStatus('Error', false);
        });
}

/**
 * Initialize the detection canvas
 */
function initializeCanvas() {
    detectionCanvas = document.getElementById('detection-canvas');
    detectionCtx = detectionCanvas.getContext('2d');
    
    // Set canvas dimensions to match the actual detection area (640x480)
    detectionCanvas.width = canvasWidth;
    detectionCanvas.height = canvasHeight;
    
    // Adjust canvas sizing based on container
    function resizeCanvas() {
        const container = detectionCanvas.parentElement;
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        
        // Calculate aspect ratio
        const canvasRatio = canvasWidth / canvasHeight;
        const containerRatio = containerWidth / containerHeight;
        
        // Adjust canvas display size to maintain aspect ratio
        if (containerRatio > canvasRatio) {
            // Container is wider than canvas aspect ratio
            detectionCanvas.style.height = '100%';
            detectionCanvas.style.width = 'auto';
        } else {
            // Container is taller than canvas aspect ratio
            detectionCanvas.style.width = '100%';
            detectionCanvas.style.height = 'auto';
        }
    }
    
    // Initial resize
    resizeCanvas();
    
    // Add window resize listener
    window.addEventListener('resize', resizeCanvas);
}

/**
 * Initialize the counting chart
 */
function initializeChart() {
    const ctx = document.getElementById('counting-chart').getContext('2d');
    
    countingChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'People Count per Minute',
                data: [],
                backgroundColor: 'rgba(52, 152, 219, 0.7)',
                borderColor: 'rgba(52, 152, 219, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0 // Only show integers
                    },
                    title: {
                        display: true,
                        text: 'Count'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time (minute)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Count: ${context.parsed.y}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize the control elements
 */
function initializeControls() {
    // Update frequency slider
    const updateFrequencySlider = document.getElementById('update-frequency');
    const updateFrequencyValue = document.getElementById('update-frequency-value');
    
    updateFrequencySlider.addEventListener('input', function() {
        updateFrequency = parseInt(this.value);
        updateFrequencyValue.textContent = updateFrequency;
        
        // Restart interval with new frequency
        if (updateIntervalId) {
            clearInterval(updateIntervalId);
        }
        updateIntervalId = setInterval(fetchData, updateFrequency);
        
        // Send updated settings to the server
        updateSettings();
    });
    
    // Confidence threshold slider
    const confidenceThresholdSlider = document.getElementById('confidence-threshold');
    const confidenceThresholdValue = document.getElementById('confidence-threshold-value');
    
    confidenceThresholdSlider.addEventListener('input', function() {
        confidenceThreshold = parseFloat(this.value);
        confidenceThresholdValue.textContent = confidenceThreshold.toFixed(2);
        
        // Send updated settings to the server
        updateSettings();
    });
    
    // Reset count button
    const resetCountButton = document.getElementById('reset-count');
    
    resetCountButton.addEventListener('click', function() {
        fetch('/api/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                totalCount = 0;
                updateTotalCount();
                // Immediately fetch fresh data
                fetchData();
            }
        })
        .catch(error => console.error('Error resetting count:', error));
    });
}

/**
 * Send updated settings to the server
 */
function updateSettings() {
    fetch('/api/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            update_frequency: updateFrequency,
            confidence_threshold: confidenceThreshold
        })
    })
    .then(response => response.json())
    .catch(error => console.error('Error updating settings:', error));
}

/**
 * Update the connection status display
 */
function updateConnectionStatus(status, isConnected) {
    const connectionStatus = document.getElementById('connection-status');
    connectionStatus.textContent = status;
    
    if (isConnected) {
        connectionStatus.classList.add('connected');
        connectionStatus.classList.remove('disconnected');
    } else {
        connectionStatus.classList.add('disconnected');
        connectionStatus.classList.remove('connected');
    }
}

/**
 * Handle data update from the API
 */
function handleDataUpdate(data) {
    // Update detection and tracking data
    if (data.detections) {
        handleDetectionUpdate(data);
    }
    
    // Update count history if available
    if (data.history) {
        handleCountUpdate(data.history);
    }
    
    // Update connection status
    updateConnectionStatus('Connected', true);
    
    // Update last update time
    lastUpdateTime = new Date();
    document.getElementById('last-update').textContent = formatTime(lastUpdateTime);
    
    // Update active tracks count
    document.getElementById('active-tracks').textContent = data.active_tracks || 0;
}

/**
 * Handle detection update data
 */
function handleDetectionUpdate(data) {
    // Store the tracked people data
    trackedPeople = data.tracks || [];
    
    // Update the counting line position if changed
    if (data.line_x) {
        countingLine.x = data.line_x;
    }
    
    // Update total count if changed
    if (data.crossing_count !== undefined && data.crossing_count !== totalCount) {
        totalCount = data.crossing_count;
        updateTotalCount();
    }
}

/**
 * Handle count update data
 */
function handleCountUpdate(historyData) {
    // Update chart data
    updateCountingChart(historyData.labels, historyData.counts);
}

/**
 * Update the displayed total count
 */
function updateTotalCount() {
    document.getElementById('total-count').textContent = totalCount;
}

/**
 * Update the counting chart with new data
 */
function updateCountingChart(labels, counts) {
    if (!countingChart || !labels || !counts) {
        return;
    }
    
    countingChart.data.labels = labels;
    countingChart.data.datasets[0].data = counts;
    countingChart.update();
}

/**
 * Format time for display
 */
function formatTime(date) {
    if (!date) return '-';
    
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/**
 * Main rendering loop
 */
function renderLoop() {
    // Clear the canvas
    detectionCtx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // Draw background (camera frame simulation)
    detectionCtx.fillStyle = '#eaeaea'; // やや濃いめの背景色
    detectionCtx.fillRect(0, 0, canvasWidth, canvasHeight);
    
    // Draw the counting line
    drawCountingLine();
    
    // Draw tracked people
    trackedPeople.forEach(person => drawPerson(person));
    
    // Schedule the next frame
    requestAnimationFrame(renderLoop);
}

/**
 * Draw the vertical counting line
 */
function drawCountingLine() {
    // Draw a direction arrow first (pointing from left to right)
    const arrowY = canvasHeight / 2;
    const arrowLength = 100; // より長い矢印
    const arrowHeadSize = 20; // より大きな矢印の先端
    const arrowX = countingLine.x - 150; // ラインからより離して目立つように
    
    // 矢印をより見えるように描画
    detectionCtx.globalAlpha = 0.6; // 不透明度を上げる
    detectionCtx.beginPath();
    
    // Arrow shaft
    detectionCtx.moveTo(arrowX, arrowY);
    detectionCtx.lineTo(arrowX + arrowLength, arrowY);
    
    // Arrow head
    detectionCtx.lineTo(arrowX + arrowLength - arrowHeadSize, arrowY - arrowHeadSize);
    detectionCtx.moveTo(arrowX + arrowLength, arrowY);
    detectionCtx.lineTo(arrowX + arrowLength - arrowHeadSize, arrowY + arrowHeadSize);
    
    // より太く目立つ線に
    detectionCtx.strokeStyle = '#FF4500'; // オレンジレッド色で目立たせる
    detectionCtx.lineWidth = 6;
    detectionCtx.stroke();
    
    // Draw "Count Direction" text
    detectionCtx.font = 'bold 16px Arial';
    detectionCtx.fillStyle = '#FF4500';
    detectionCtx.fillText('Count Direction', arrowX, arrowY - 25);
    
    // Reset transparency
    detectionCtx.globalAlpha = 1.0;
    
    // Draw the counting line
    detectionCtx.beginPath();
    detectionCtx.moveTo(countingLine.x, 0);
    detectionCtx.lineTo(countingLine.x, canvasHeight);
    detectionCtx.strokeStyle = colors.countingLine;
    detectionCtx.lineWidth = 2;
    detectionCtx.setLineDash([5, 5]);
    detectionCtx.stroke();
    detectionCtx.setLineDash([]);
    
    // Draw label
    detectionCtx.fillStyle = colors.countingLine;
    detectionCtx.font = '14px Arial';
    detectionCtx.fillText('Counting Line', countingLine.x + 5, 20);
}

/**
 * Draw a tracked person
 */
function drawPerson(person) {
    // Set color based on crossing status
    const color = person.crossed_line ? colors.crossedPerson : colors.detectionBox;
    
    // Get bounding box coordinates
    const x = person.bbox[0];
    const y = person.bbox[1];
    const width = person.bbox[2] - person.bbox[0];
    const height = person.bbox[3] - person.bbox[1];
    
    // Draw bounding box
    detectionCtx.strokeStyle = color;
    detectionCtx.lineWidth = 2;
    detectionCtx.strokeRect(x, y, width, height);
    
    // Prepare label text
    const labelText = `ID: ${person.id} (${(person.confidence * 100).toFixed(0)}%)`;
    const labelPadding = 2;
    
    // Calculate text metrics
    detectionCtx.font = '12px Arial';
    const textMetrics = detectionCtx.measureText(labelText);
    const textWidth = textMetrics.width;
    const textHeight = 12; // Approximate font height
    
    // Check if the label would go outside the canvas if placed above
    // If so, place it inside the box at the top
    const labelY = (y < textHeight + labelPadding) ? y + textHeight + labelPadding : y - 5;
    const labelX = x;
    
    // Add a background rectangle for better readability
    detectionCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    if (y < textHeight + labelPadding) {
        // Draw inside the box at the top
        detectionCtx.fillRect(labelX, y + labelPadding, textWidth + 2 * labelPadding, textHeight + labelPadding);
    } else {
        // Draw above the box
        detectionCtx.fillRect(labelX - labelPadding, labelY - textHeight, textWidth + 2 * labelPadding, textHeight + labelPadding);
    }
    
    // Draw label
    detectionCtx.fillStyle = 'white';
    detectionCtx.fillText(labelText, labelX, labelY);
    
    // Draw tracking path
    if (person.path && person.path.length > 1) {
        detectionCtx.beginPath();
        detectionCtx.moveTo(person.path[0][0], person.path[0][1]);
        
        for (let i = 1; i < person.path.length; i++) {
            detectionCtx.lineTo(person.path[i][0], person.path[i][1]);
        }
        
        detectionCtx.strokeStyle = colors.trackingPath;
        detectionCtx.lineWidth = 2;
        detectionCtx.stroke();
    }
}