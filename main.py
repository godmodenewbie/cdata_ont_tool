from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict
import os

# Import the driver class
# Assuming cdata_driver.py is in the same directory
from cdata_driver import CDataJsonDriver

app = FastAPI()

# In-memory storage for the driver instance per session/user
# For a simple local tool, a global variable is acceptable but not thread-safe for multiple concurrent users targeting different ONTs.
# To keep it simple as requested:
driver_instance: Optional[CDataJsonDriver] = None

class LoginRequest(BaseModel):
    ip: str
    username: str
    password: str

class PingRequest(BaseModel):
    target_ip: str

# Serve static files
# We will create a 'static' directory for the frontend
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    # Serve the index.html on root
    return FileResponse("static/index.html")

@app.get("/diagnosis")
async def read_diagnosis():
    # Serve the diagnosis.html
    return FileResponse("static/diagnosis.html")

@app.post("/api/login")
async def login(request: LoginRequest):
    global driver_instance
    
    try:
        # Initialize the driver
        driver = CDataJsonDriver(request.ip, request.username, request.password)
        
        # Attempt login
        if driver.login():
            driver_instance = driver
            return {"status": "success", "message": "Login successful"}
        else:
            return {"status": "error", "message": "Login failed. Check credentials or IP."}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ping")
async def ping(request: PingRequest):
    global driver_instance
    
    if not driver_instance:
        raise HTTPException(status_code=401, detail="Not logged in. Please login first.")
    
    try:
        result = driver_instance.ping(request.target_ip)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TracerouteRequest(BaseModel):
    target_ip: str

@app.post("/api/traceroute")
async def traceroute(request: TracerouteRequest):
    global driver_instance
    
    if not driver_instance:
        raise HTTPException(status_code=401, detail="Not logged in. Please login first.")
    
    try:
        result = driver_instance.traceroute(request.target_ip)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    global driver_instance
    if not driver_instance:
        raise HTTPException(status_code=401, detail="Not logged in")
    return driver_instance.get_device_status()

@app.get("/api/info")
async def get_info():
    global driver_instance
    if not driver_instance:
        raise HTTPException(status_code=401, detail="Not logged in")
    return driver_instance.get_device_info()

@app.get("/api/pon")
async def get_pon():
    global driver_instance
    if not driver_instance:
        raise HTTPException(status_code=401, detail="Not logged in")
    return driver_instance.get_pon_info()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
