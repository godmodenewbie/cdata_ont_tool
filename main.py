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

import re

def extract_ping_data(raw_output: str) -> Dict[str, Optional[float]]:
    loss = None
    latency = None
    if not raw_output:
        return {"loss": loss, "latency": latency}
    
    loss_match = re.search(r'(\d+)% packet loss', raw_output)
    if loss_match:
        loss = float(loss_match.group(1))
        
    time_match = re.search(r'min/avg/max = [^/]+/([^/]+)/', raw_output)
    if time_match:
        latency = float(time_match.group(1))
    else:
        time_str_matches = re.findall(r'time=(\d+\.?\d*) ms', raw_output)
        if time_str_matches:
            latency = float(time_str_matches[-1])
            
    return {"loss": loss, "latency": latency}

@app.get("/api/diagnosis")
async def run_full_diagnosis():
    global driver_instance
    if not driver_instance:
        raise HTTPException(status_code=401, detail="Not logged in")
        
    results = {"steps": {}, "overall": {"score": 0, "status": "", "recommendations": []}}
    scores = {"step1": 0, "step2": 0, "step3": 0, "step4": 0}
    recs = []
    
    # Step 1: PON Info
    try:
        pon_data = driver_instance.get_pon_info()
        rx = float(pon_data.get('rxPower', 0)) if pon_data.get('rxPower') not in ['LOS', None] else 0
        if pon_data.get('rxPower') == 'LOS': rx = 0
            
        if -25 <= rx <= -15:
            scores["step1"] = 100
            status = "Normal"
        elif -28 <= rx < -25:
            scores["step1"] = 50
            status = "Warning"
            recs.append("Periksa kabel fiber optik, redaman kurang ideal. Pastikan tidak ada lekukan tajam.")
        elif rx < -28 or rx == 0:
            scores["step1"] = 0
            status = "Abnormal"
            recs.append("Redaman optik Sangat Buruk (LOS). Kabel fiber putus atau redaman terlalu ekstrem.")
        else:
            scores["step1"] = 80
            status = "Warning"
            
        results["steps"]["physical"] = {"data": pon_data, "score": scores["step1"], "status": status}
    except Exception as e:
        results["steps"]["physical"] = {"error": str(e), "score": 0, "status": "Error"}
        recs.append(f"Gagal mengambil data PON: {str(e)}")

    # Step 2: System Resource
    try:
        info_data = driver_instance.get_device_info()
        status_data = driver_instance.get_device_status()
        uptime = int(info_data.get('uptime', 0))
        cpu = int(status_data.get('CPU_Usage', 0))
        
        if cpu > 90:
            scores["step2"] = 0
            status = "Abnormal"
            recs.append("CPU ONT Overload (>90%). Router akan terasa sangat lambat. Coba restart router.")
        elif uptime < 86400:
            scores["step2"] = 50
            status = "Warning"
            recs.append("Router baru saja menyala (Uptime < 24 Jam). Jika sebelumnya mati mendadak, cek adaptor daya stabil atau tidak.")
        else:
            scores["step2"] = 100
            status = "Normal"
            
        results["steps"]["resource"] = {"info": info_data, "status": status_data, "score": scores["step2"], "status_text": status}
    except Exception as e:
        results["steps"]["resource"] = {"error": str(e), "score": 0, "status": "Error"}
        recs.append(f"Gagal mengambil data sistem: {str(e)}")

    # Step 3: Internet (Ping)
    try:
        ping1 = driver_instance.ping("8.8.8.8")
        ping2 = driver_instance.ping("google.com")
        
        stat1 = extract_ping_data(ping1.get("raw_output", ""))
        is_dns_ok = ping2.get("status") not in ['DNS ERROR', 'ERROR'] and "bad address" not in (ping2.get("raw_output") or "")
        
        if ping1.get("status") == 'OFFLINE/RTO' or stat1["loss"] == 100:
            scores["step3"] = 0
            status = "Abnormal"
            recs.append("Koneksi terputus (100% RTO). Internet dari ISP bermasalah atau otentikasi PPPoE gagal.")
        elif not is_dns_ok:
            scores["step3"] = 0
            status = "Abnormal"
            recs.append("DNS Gagal meresolve domain. Koneksi IP ada tapi server DNS bermasalah.")
        elif (stat1["loss"] or 0) > 5 or (stat1["latency"] or 0) > 100:
            scores["step3"] = 50
            status = "Warning"
            recs.append("Koneksi Lambat. Ada packet loss atau ping membengkak (>100ms). Cek traffic penuh atau redaman kabel.")
        else:
            scores["step3"] = 100
            status = "Normal"
            
        results["steps"]["internet"] = {"ping_8888": ping1, "ping_google": ping2, "score": scores["step3"], "status": status}
    except Exception as e:
        results["steps"]["internet"] = {"error": str(e), "score": 0, "status": "Error"}
        recs.append(f"Gagal melakukan Ping Test: {str(e)}")

    # Step 4: Local Network
    try:
        status_data = driver_instance.get_device_status()
        led_lan = status_data.get("led_status", {}).get("lan", [])
        active_lans = [f"Port {i+1}" for i, state in enumerate(led_lan) if state == "on"]
        
        if active_lans:
            scores["step4"] = 100
            status = "Normal"
        else:
            scores["step4"] = 50
            status = "Warning"
            recs.append("Tidak ada kabel LAN terhubung. Pastikan jaringan WiFi dalam jangkauan baik.")
            
        results["steps"]["local_network"] = {"active_lans": active_lans, "score": scores["step4"], "status": status}
    except Exception as e:
        results["steps"]["local_network"] = {"error": str(e), "score": 0, "status": "Error"}
        recs.append(f"Gagal mengecek status jaringan lokal: {str(e)}")

    # Final Calculation
    avg_score = round(sum(scores.values()) / 4)
    if avg_score > 80:
        final_status = "Koneksi Normal"
        if avg_score == 100:
            recs.append("Tidak ditemukan indikasi kendala teknis pada platform router. Jika user masih lambat, periksa batasan FUP Bandwidth atau kemacetan frekuensi WiFi di rumah.")
    elif avg_score >= 50:
        final_status = "Ada Gangguan Ringan"
    else:
        final_status = "Koneksi Bermasalah / Mati"
        
    results["overall"] = {
        "score": avg_score,
        "status": final_status,
        "recommendations": recs
    }
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
