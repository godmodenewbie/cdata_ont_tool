import hashlib
import time
import requests
from typing import Dict, Union, List, Optional, Any

class CDataJsonDriver:
    """
    Driver for C-Data ONT devices using hidden JSON API.
    """

    def __init__(self, ip: str, username: str, password: str):
        """
        Initialize the driver with device credentials.
        
        Args:
            ip: IP address of the ONT device.
            username: Login username.
            password: Login password.
        """
        self.base_url = f"http://{ip}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        # Minimal headers might be safer.
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/json",
            # Try pointing to internal page or root with explicit filename
            "Referer": self.base_url + "/index.html"
        })
        self.token = None

    def _encrypt_password(self) -> str:
        """
        Encrypt the password using MD5.
        
        Returns:
            MD5 hash of the password as a hex string.
        """
        return hashlib.md5(self.password.encode('utf-8')).hexdigest()

    def login(self) -> bool:
        """
        Perform login to the ONT device.
        
        Returns:
            True if login is successful (code 0), False otherwise.
        """
        url = f"{self.base_url}/post.json"
        # The API expects md5 hash of the password
        encrypted_password = self._encrypt_password()
        
        payload = {
            "module": "login",
            "username": self.username,
            "encryPassword": encrypted_password
        }

        print(f"DEBUG: Original Password: {self.password}")
        print(f"DEBUG: Encrypted Password (MD5): {encrypted_password}")
        print(f"DEBUG: Sending Payload to {url}: {payload}")
        print(f"DEBUG: Session Headers: {self.session.headers}")

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            print(f"DEBUG: Response from device: {data}")

            # Check for success code if present in login response
            # Based on user spec, we look for code 0
            if data.get("code") == 0:
                # Capture token if present
                self.token = data.get("token")
                if self.token:
                    print(f"DEBUG: Captured token: {self.token}")
                    # Validated via screenshot: Device uses Authorization header
                    self.session.headers.update({"Authorization": self.token})
                return True
            return False

        except requests.RequestException as e:
            print(f"Login failed due to network error: {e}")
            return False
        except ValueError as e:
            print(f"Login failed due to invalid JSON response: {e}")
            return False
        except Exception as e:
            print(f"Login failed due to unexpected error: {e}")
            return False

    def get_wan_interface(self) -> int:
        """
        Fetch the WAN interface index for ping.
        Returns the first available ifindex or 65535 if none/error.
        """
        url = f"{self.base_url}/get.json?module=wan_interface"
        try:
            print(f"DEBUG: Fetching WAN interface from {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(f"DEBUG: WAN Interface response: {data}")
            
            ipv4_list = data.get("ipv4_interface_list", [])
            if ipv4_list:
                # Return the ifindex of the first interface found
                return ipv4_list[0].get("ifindex", 65535)
            return 65535 # Default fallback
            
        except Exception as e:
            print(f"DEBUG: Error fetching WAN interface: {e}")
            return 65535

    def ping(self, target_ip: str) -> Dict[str, str]:
        """
        Execute ping test on the ONT device.
        """
        # 1. Get WAN Interface
        wan_ifindex = self.get_wan_interface()
        
        start_url = f"{self.base_url}/post.json"
        result_url = f"{self.base_url}/get.json?module=ping_result"
        
        start_payload = {
            "module": "ping_ipv4",
            "protocol": 0,
            "host_address": target_ip,
            "wan_interface": wan_ifindex
        }

        try:
            # 2. Trigger Ping
            print(f"DEBUG: Starting ping to {target_ip} with wan_interface={wan_ifindex}...")
            response = self.session.post(start_url, json=start_payload, timeout=10)
            response.raise_for_status()
            print(f"DEBUG: Ping start response: {response.json()}")
            
            # 3. Polling Loop
            max_retries = 30
            poll_interval = 2 # seconds
            
            # We don't accumulate because the device returns the full buffer each time (based on user's duplicate report)
            # We will just take the latest result.
            latest_results = []
            
            for attempt in range(max_retries):
                time.sleep(poll_interval)
                
                poll_response = self.session.get(result_url, timeout=10)
                poll_response.raise_for_status()
                data = poll_response.json()
                print(f"DEBUG: Poll attempt {attempt+1}/{max_retries} response: {data}")
                
                # Update latest results
                current_results = data.get("ping_result", [])
                if current_results:
                    latest_results = current_results
                
                # Check finish flag
                # Per user: "until finish_flag = 0" -> 0 means Done.
                finish_flag = data.get("finish_flag")
                
                if finish_flag == 0:
                    # Done
                    raw_output = "\n".join(latest_results)
                    status = "UNKNOWN"
                    
                    if "0% packet loss" in raw_output:
                        status = "ONLINE"
                    elif "100% packet loss" in raw_output:
                        status = "OFFLINE/RTO"
                    elif "bad address" in raw_output:
                        status = "DNS ERROR"
                    else:
                         # Fallback heuristic
                        if "bytes from" in raw_output and "packet loss" in raw_output:
                             pass
                        if "bytes from" in raw_output:
                            status = "ONLINE"

                    return {
                        "target": target_ip,
                        "status": status,
                        "raw_output": raw_output
                    }
            
            # If loop finishes without finish_flag == 0
            # Return partial results if we have any
            if latest_results:
                 raw_output = "\n".join(latest_results)
                 return {
                    "target": target_ip,
                    "status": "TIMEOUT/PARTIAL",
                    "raw_output": raw_output + "\n\n(Timed out waiting for finish_flag=0)"
                }

            return {
                "target": target_ip,
                "status": "TIMEOUT",
                "raw_output": "Timeout: Ping did not finish within expected time."
            }

        except requests.RequestException as e:
            return {
                "target": target_ip,
                "status": "ERROR",
                "raw_output": f"Network error during ping: {str(e)}"
            }
        except ValueError as e:
            return {
                "target": target_ip,
                "status": "ERROR",
                "raw_output": f"JSON parsing error: {str(e)}"
            }
        except Exception as e:
            return {
                "target": target_ip,
                "status": "ERROR",
                "raw_output": f"Unexpected error: {str(e)}"
            }

    def traceroute(self, target_ip: str) -> Dict[str, str]:
        """
        Execute traceroute on the ONT device.
        """
        # 1. Get WAN Interface
        # Previously hardcoded 65535, but Ping uses the fetched one (e.g. 65536) and works.
        # Switching to fetched interface to ensure correct routing.
        wan_ifindex = self.get_wan_interface()
        
        start_url = f"{self.base_url}/post.json"
        result_url = f"{self.base_url}/get.json?module=tracert_result"
        
        start_payload = {
            "module": "tracert_ipv4",
            "protocol": 0,
            "host_address": target_ip,
            "number_of_tries": 3,
            "time_out": 1,
            "data_size": 56,
            "dscp": 0,
            "max_hop_count": 30,
            "wan_interface": wan_ifindex
        }

        try:
            # 2. Trigger Traceroute
            print(f"DEBUG: Starting traceroute to {target_ip} with wan_interface={wan_ifindex}...")
            response = self.session.post(start_url, json=start_payload, timeout=10)
            response.raise_for_status()
            print(f"DEBUG: Traceroute start response: {response.json()}")
            
            # 3. Polling Loop
            # Traceroute takes longer, so more retries/timeout needed
            max_retries = 60 
            poll_interval = 2 # seconds
            latest_results = []
            
            for attempt in range(max_retries):
                time.sleep(poll_interval)
                
                poll_response = self.session.get(result_url, timeout=10)
                poll_response.raise_for_status()
                data = poll_response.json()
                print(f"DEBUG: Poll attempt {attempt+1}/{max_retries} response: {data}")
                
                # Update latest results
                # Key difference: "tracert_result" instead of "ping_result"
                current_results = data.get("tracert_result", [])
                if current_results:
                    latest_results = current_results
                
                finish_flag = data.get("finish_flag")
                
                if finish_flag == 0:
                    # Done
                    raw_output = "\n".join(latest_results)
                    return {
                        "target": target_ip,
                        "status": "DONE",
                        "raw_output": raw_output
                    }
            
            # Timeout case
            # Return partial results
            if latest_results:
                 raw_output = "\n".join(latest_results)
                 return {
                    "target": target_ip,
                    "status": "TIMEOUT/PARTIAL",
                    "raw_output": raw_output + "\n\n(Timed out waiting for finish_flag=0)"
                }

            return {
                "target": target_ip,
                "status": "TIMEOUT",
                "raw_output": "Timeout: Traceroute did not finish within expected time."
            }

        except Exception as e:
             return {
                "target": target_ip,
                "status": "ERROR",
                "raw_output": f"Error during traceroute: {str(e)}"
            }

    def get_device_status(self) -> Dict[str, Any]:
        """
        Fetch device status.
        URL: /get.json?module=dev_status&refresh_login_timer=0
        """
        url = f"{self.base_url}/get.json?module=dev_status&refresh_login_timer=0"
        try:
            print(f"DEBUG: Fetching Device Status from {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"DEBUG: Error fetching device status: {e}")
            return {"error": str(e)}

    def get_device_info(self) -> Dict[str, Any]:
        """
        Fetch device info.
        URL: /get.json?module=dev_info&refresh_login_timer=0
        """
        url = f"{self.base_url}/get.json?module=dev_info&refresh_login_timer=0"
        try:
            print(f"DEBUG: Fetching Device Info from {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"DEBUG: Error fetching device info: {e}")
            return {"error": str(e)}

    def get_pon_info(self) -> Dict[str, Any]:
        """
        Fetch PON info.
        URL: /get.json?module=pon_info&refresh_login_timer=0
        """
        url = f"{self.base_url}/get.json?module=pon_info&refresh_login_timer=0"
        try:
            print(f"DEBUG: Fetching PON Info from {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"DEBUG: Error fetching PON info: {e}")
            return {"error": str(e)}
