import asyncio
import os
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Origins Forge Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL ENGINE STATE ---
engine_state = {
    "node_name": os.getenv("RAILWAY_REPLICA_ID", "local-dev-node"),
    "active_streams": 0,
    "active_jobs": 0,
    "max_capacity": 10, # Max simultaneous builds before queuing
    "total_builds": 0,
    "start_time": time.time()
}

@app.get("/api/runner-status")
async def get_runner_status():
    """Returns the live health of this specific Forge Engine runner."""
    uptime_hours = round((time.time() - engine_state["start_time"]) / 3600, 2)
    
    # Determine health status based on capacity
    capacity_pct = (engine_state["active_jobs"] / engine_state["max_capacity"]) * 100
    if capacity_pct >= 100:
        status = "degraded" # Queue is full
    elif capacity_pct >= 70:
        status = "warning"  # Getting busy
    else:
        status = "healthy"

    return {
        "name": engine_state["node_name"],
        "status": status,
        "active_jobs": engine_state["active_jobs"],
        "max_capacity": engine_state["max_capacity"],
        "active_streams": engine_state["active_streams"],
        "uptime_hours": uptime_hours,
        "gemini_latency_ms": 124 # In a real app, ping the API to get this
    }

@app.get("/")
@app.get("/health")
async def health_check():
    return {"status": "Origins Engine is online"}
    
@app.websocket("/ws/terminal")
async def terminal_endpoint(websocket: WebSocket):
    await websocket.accept()
    engine_state["active_streams"] += 1 # 🟢 Track new connection
    
    await websocket.send_text("\r\n\033[1;32mConnected to Origins Forge Engine\033[0m\r\n$ ")

    try:
        while True:
            command = await websocket.receive_text()
            if not command.strip().startswith("origins "):
                await websocket.send_text("\r\n\033[1;31mError: Sandbox mode active.\033[0m\r\n$ ")
                continue

            engine_state["active_jobs"] += 1 # 🟢 Track active build job
            
            # ... (Your existing subprocess code goes here) ...

            engine_state["active_jobs"] -= 1 # 🔴 Job finished
            engine_state["total_builds"] += 1
            await websocket.send_text("\r\n$ ")

    except WebSocketDisconnect:
        engine_state["active_streams"] -= 1 # 🔴 Track disconnection
    except Exception as e:
        engine_state["active_jobs"] = max(0, engine_state["active_jobs"] - 1)
