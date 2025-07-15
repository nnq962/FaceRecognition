from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import random
from typing import List
from utils.logger_config import LOGGER
from database_config import config

app = FastAPI(title="Student Check-in WebSocket API", version="1.0.0")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        LOGGER.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        LOGGER.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                LOGGER.error(f"Error sending message to connection: {e}")
                disconnected_connections.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected_connections:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

def generate_mock_checkin_data():
    """Generate mock check-in data"""
    student_names = [
        "Nguyễn Văn A", "Trần Thị B", "Lê Văn C", "Phạm Thị D", "Hoàng Văn E",
        "Vũ Thị F", "Đặng Văn G", "Bùi Thị H", "Dương Văn I", "Lý Thị K",
        None  # Sometimes name can be null
    ]
    
    # Generate random student data
    student_id = random.randint(100, 999)
    student_code = f"PUPIL_{random.randint(100000000, 999999999)}"
    student_name = random.choice(student_names)
    check_in_time = config.get_vietnam_time()
    
    return {
        "id": student_id,
        "code": student_code,
        "name": student_name,
        "check_in_time": check_in_time,
        "active_status": True
    }

async def send_periodic_checkin():
    """Send periodic check-in notifications every 10 seconds"""
    while True:
        if manager.active_connections:
            # Generate mock data
            checkin_data = generate_mock_checkin_data()
            
            # Create notification message
            notification = {
                "type": "student_checkin",
                "timestamp": config.get_vietnam_time(),
                "message": "New student check-in detected",
                "data": checkin_data
            }
            
            message = json.dumps(notification, ensure_ascii=False)
            LOGGER.info(f"Broadcasting check-in notification: {checkin_data['code']}")
            
            await manager.broadcast(message)
        
        # Wait for 10 seconds
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    """Start the periodic check-in notification task"""
    LOGGER.info("Starting WebSocket server and periodic check-in notifications")
    asyncio.create_task(send_periodic_checkin())

@app.websocket("/ws/checkin")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for check-in notifications"""
    await manager.connect(websocket)
    
    # Send welcome message
    welcome_message = {
        "type": "connection",
        "timestamp": config.get_vietnam_time(),
        "message": "Connected to check-in notification service",
        "data": {
            "status": "connected",
            "interval": "10 seconds"
        }
    }
    
    await manager.send_personal_message(
        json.dumps(welcome_message, ensure_ascii=False), 
        websocket
    )
    
    try:
        while True:
            # Keep connection alive and listen for any client messages
            data = await websocket.receive_text()
            LOGGER.info(f"Received message from client: {data}")
            
            # Echo back client message (optional)
            response = {
                "type": "echo",
                "timestamp": config.get_vietnam_time(),
                "message": "Message received",
                "data": {"received": data}
            }
            
            await manager.send_personal_message(
                json.dumps(response, ensure_ascii=False), 
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        LOGGER.info("Client disconnected from check-in notifications")

@app.websocket("/ws/checkin/{client_id}")
async def websocket_endpoint_with_id(websocket: WebSocket, client_id: str):
    """WebSocket endpoint with client ID for check-in notifications"""
    await manager.connect(websocket)
    
    # Send welcome message with client ID
    welcome_message = {
        "type": "connection",
        "timestamp": config.get_vietnam_time(),
        "message": f"Client {client_id} connected to check-in notification service",
        "data": {
            "client_id": client_id,
            "status": "connected",
            "interval": "10 seconds"
        }
    }
    
    await manager.send_personal_message(
        json.dumps(welcome_message, ensure_ascii=False), 
        websocket
    )
    
    try:
        while True:
            data = await websocket.receive_text()
            LOGGER.info(f"Received message from client {client_id}: {data}")
            
            response = {
                "type": "echo",
                "timestamp": config.get_vietnam_time(),
                "message": f"Message received from {client_id}",
                "data": {"client_id": client_id, "received": data}
            }
            
            await manager.send_personal_message(
                json.dumps(response, ensure_ascii=False), 
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        LOGGER.info(f"Client {client_id} disconnected from check-in notifications")

@app.get("/")
async def get():
    """Serve a simple HTML page to test WebSocket"""
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Student Check-in WebSocket Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .message { 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 5px; 
            background-color: #f0f0f0;
        }
        .checkin { background-color: #d4edda; border-left: 4px solid #28a745; }
        .connection { background-color: #d1ecf1; border-left: 4px solid #17a2b8; }
        .echo { background-color: #fff3cd; border-left: 4px solid #ffc107; }
        button { 
            padding: 10px 20px; 
            margin: 5px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer;
        }
        .connect { background-color: #28a745; color: white; }
        .disconnect { background-color: #dc3545; color: white; }
        .send { background-color: #007bff; color: white; }
        input { padding: 8px; margin: 5px; width: 100px; }
        #status { font-weight: bold; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Student Check-in WebSocket Test</h1>
        <div id="status">Status: Disconnected</div>
        
        <div>
            <button class="connect" onclick="connect()">Connect</button>
            <button class="disconnect" onclick="disconnect()">Disconnect</button>
        </div>
        
        <div>
            <input type="text" id="messageInput" placeholder="Enter message to send">
            <button class="send" onclick="sendMessage()">Send Message</button>
        </div>
        
        <h3>Messages:</h3>
        <div id="messages"></div>
    </div>

    <script>
        var ws = null;
        
        function connect() {
            if (ws !== null) return;
            
            ws = new WebSocket("ws://localhost:8001/ws/checkin");
            document.getElementById("status").innerHTML = "Status: Connecting...";
            
            ws.onopen = function(event) {
                document.getElementById("status").innerHTML = "Status: Connected";
                addMessage("Connected to WebSocket", "connection");
            };
            
            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                var messageType = data.type;
                var content = JSON.stringify(data, null, 2);
                addMessage(content, messageType);
            };
            
            ws.onclose = function(event) {
                document.getElementById("status").innerHTML = "Status: Disconnected";
                addMessage("Disconnected from WebSocket", "connection");
                ws = null;
            };
            
            ws.onerror = function(error) {
                document.getElementById("status").innerHTML = "Status: Error";
                addMessage("WebSocket error: " + error, "connection");
            };
        }
        
        function disconnect() {
            if (ws !== null) {
                ws.close();
            }
        }
        
        function sendMessage() {
            if (ws !== null && ws.readyState === WebSocket.OPEN) {
                var message = document.getElementById("messageInput").value;
                ws.send(message);
                document.getElementById("messageInput").value = "";
            } else {
                alert("WebSocket is not connected");
            }
        }
        
        function addMessage(message, type) {
            var messages = document.getElementById("messages");
            var messageElement = document.createElement("div");
            messageElement.className = "message " + type;
            messageElement.innerHTML = "<pre>" + message + "</pre>";
            messages.appendChild(messageElement);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Allow sending message with Enter key
        document.getElementById("messageInput").addEventListener("keypress", function(e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    </script>
</body>
</html>
    """)

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "success",
        "message": "WebSocket server is healthy",
        "timestamp": config.get_vietnam_time(),
        "data": {
            "service": "Student Check-in WebSocket",
            "version": "1.0.0",
            "active_connections": len(manager.active_connections),
            "notification_interval": "10 seconds"
        }
    }

@app.post("/trigger-checkin")
def trigger_manual_checkin():
    """Manually trigger a check-in notification (for testing)"""
    if manager.active_connections:
        checkin_data = generate_mock_checkin_data()
        
        notification = {
            "type": "student_checkin",
            "timestamp": config.get_vietnam_time(),
            "message": "Manual check-in triggered",
            "data": checkin_data
        }
        
        message = json.dumps(notification, ensure_ascii=False)
        
        # Send to all connected clients
        asyncio.create_task(manager.broadcast(message))
        
        return {
            "status": "success",
            "message": "Check-in notification sent",
            "timestamp": config.get_vietnam_time(),
            "data": checkin_data
        }
    else:
        return {
            "status": "error",
            "message": "No active WebSocket connections",
            "timestamp": config.get_vietnam_time(),
            "data": None
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)