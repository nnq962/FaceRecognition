import { showToast } from '../utils/toast.js';

// DOM Elements
const roomInput = document.getElementById('roomInput');
const connectBtn = document.getElementById('connectBtn');
const status = document.getElementById('status');
const statusIndicator = document.getElementById('statusIndicator');
const dataDisplay = document.getElementById('dataDisplay');

// WebSocket instance
let ws = null;
let currentRoom = null;
let isConnecting = false;

// Connection states
const ConnectionState = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting', 
    CONNECTED: 'connected',
    ERROR: 'error'
};

// Initialize app
function init() {
    setupEventListeners();
    roomInput.focus();
}

// Setup all event listeners
function setupEventListeners() {
    // Room input enter key
    roomInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleConnectClick();
        }
    });

    // Connect button click (works for both desktop and mobile)
    connectBtn.addEventListener('click', (e) => {
        e.preventDefault();
        handleConnectClick();
    });

    // Page visibility change
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && ws && ws.readyState !== WebSocket.OPEN && currentRoom) {
            showToast('Cảnh báo', 'Kết nối bị mất, vui lòng thử kết nối lại', 'warning');
        }
    });

    // Handle page unload
    window.addEventListener('beforeunload', () => {
        if (ws) {
            ws.close(1000, 'Page unload');
        }
    });
}

// Handle connect button click
function handleConnectClick() {
    if (isConnecting) return;

    const connectionState = ws?.readyState;
    
    if (connectionState === WebSocket.OPEN) {
        // Currently connected - disconnect
        disconnect();
    } else {
        // Not connected - connect
        connectToRoom();
    }
}

// Connect to room
function connectToRoom() {
    const roomId = roomInput.value.trim();
    
    if (!roomId) {
        showToast('Lỗi kết nối', 'Vui lòng nhập ID phòng', 'error');
        roomInput.focus();
        return;
    }

    if (isConnecting) return;

    // Close existing connection if any
    if (ws) {
        ws.close(1000, 'Reconnecting');
    }

    isConnecting = true;
    currentRoom = roomId;
    setConnectionState(ConnectionState.CONNECTING);

    // Create WebSocket connection
    const wsUrl = `ws://${window.location.host}/ws/${roomId}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        isConnecting = false;
        setConnectionState(ConnectionState.CONNECTED, roomId);
        showToast('Kết nối thành công', `Đã kết nối đến phòng ${roomId}`, 'success');
    };

    ws.onmessage = (event) => {
        handleIncomingData(event.data);
    };

    ws.onclose = (event) => {
        isConnecting = false;
        
        if (event.code === 1000) {
            // Normal closure - user initiated
            setConnectionState(ConnectionState.DISCONNECTED);
        } else {
            // Unexpected closure
            setConnectionState(ConnectionState.ERROR);
            if (currentRoom) {
                showToast('Mất kết nối', 'Kết nối với server đã bị ngắt', 'error');
            }
        }
        
        currentRoom = null;
    };

    ws.onerror = () => {
        isConnecting = false;
        setConnectionState(ConnectionState.ERROR);
        showToast('Lỗi WebSocket', 'Không thể kết nối đến server', 'error');
        currentRoom = null;
    };
}

// Disconnect from room
function disconnect() {
    if (ws) {
        currentRoom = null;
        ws.close(1000, 'User disconnected');
    }
    setConnectionState(ConnectionState.DISCONNECTED);
    showEmptyState();
}

// Set connection state and update UI
function setConnectionState(state, roomId = null) {
    switch (state) {
        case ConnectionState.DISCONNECTED:
            status.textContent = 'Chưa kết nối';
            statusIndicator.className = 'w-3 h-3 rounded-full bg-red-500 transition-colors duration-300';
            connectBtn.textContent = 'Kết nối';
            connectBtn.disabled = false;
            break;
            
        case ConnectionState.CONNECTING:
            status.textContent = 'Đang kết nối...';
            statusIndicator.className = 'w-3 h-3 rounded-full bg-yellow-500 animate-pulse transition-colors duration-300';
            connectBtn.textContent = 'Đang kết nối...';
            connectBtn.disabled = true;
            break;
            
        case ConnectionState.CONNECTED:
            status.textContent = `Đã kết nối đến phòng ${roomId}`;
            statusIndicator.className = 'w-3 h-3 rounded-full bg-green-500 transition-colors duration-300';
            connectBtn.textContent = 'Ngắt kết nối';
            connectBtn.disabled = false;
            break;
            
        case ConnectionState.ERROR:
            status.textContent = 'Lỗi kết nối';
            statusIndicator.className = 'w-3 h-3 rounded-full bg-red-500 animate-pulse transition-colors duration-300';
            connectBtn.textContent = 'Thử lại';
            connectBtn.disabled = false;
            break;
    }
}

// Handle incoming WebSocket data
function handleIncomingData(rawData) {
    try {
        const data = JSON.parse(rawData);
        displayData(data);
        
        // Log data type for debugging
        console.log(`Received ${data.type} data:`, data);
    } catch (e) {
        console.error('Error parsing data:', e);
        displayRawData(rawData);
    }
}

// Display structured data
function displayData(data) {
    const displayData = {
        ...data,
        received_at: new Date().toLocaleString('vi-VN')
    };
    
    const formattedJson = JSON.stringify(displayData, null, 2);
    
    dataDisplay.innerHTML = `
        <div class="space-y-2">
            <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span>Loại dữ liệu: <span class="font-semibold text-blue-600 dark:text-blue-400">${data.type}</span></span>
                <span>Nhận lúc: ${displayData.received_at}</span>
            </div>
            <pre class="whitespace-pre-wrap text-sm leading-relaxed">${formattedJson}</pre>
        </div>
    `;
    
    // Subtle animation
    dataDisplay.style.opacity = '0.7';
    setTimeout(() => {
        dataDisplay.style.opacity = '1';
    }, 100);
}

// Display raw data when JSON parsing fails
function displayRawData(rawData) {
    dataDisplay.innerHTML = `
        <div class="space-y-2">
            <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span>Dữ liệu thô (Raw Data)</span>
                <span>Nhận lúc: ${new Date().toLocaleString('vi-VN')}</span>
            </div>
            <pre class="whitespace-pre-wrap text-sm leading-relaxed">${rawData}</pre>
        </div>
    `;
}

// Show empty state
function showEmptyState() {
    dataDisplay.innerHTML = `
        <div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <div class="text-center">
                <div class="w-16 h-16 mx-auto mb-3 opacity-30">
                    <svg fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                    </svg>
                </div>
                <p>Thông tin sẽ hiển thị ở đây khi có dữ liệu...</p>
            </div>
        </div>
    `;
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);