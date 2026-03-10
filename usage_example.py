from cdata_driver import CDataJsonDriver

def main():
    # Example Configuration
    ONT_IP = "192.168.1.1" # Replace with actual ONT IP
    USERNAME = "admin"     # Replace with actual username
    PASSWORD = "password"  # Replace with actual password
    TARGET_IP = "8.8.8.8"  # Google DNS
    
    print(f"Connecting to ONT at {ONT_IP}...")
    driver = CDataJsonDriver(ONT_IP, USERNAME, PASSWORD)
    
    print("Logging in...")
    if driver.login():
        print("Login Successful!")
        
        print(f"Starting Ping Test to {TARGET_IP}...")
        result = driver.ping(TARGET_IP)
        
        print("\n--- Ping Result ---")
        print(f"Target: {result['target']}")
        print(f"Status: {result['status']}")
        print(f"Raw Output:\n{result['raw_output']}")
        print("-------------------")
        
    else:
        print("Login Failed! Check credentials or network connection.")

if __name__ == "__main__":
    main()
