# C-Data ONT Tool API Documentation

This document describes the REST API endpoints available in the C-Data ONT diagnostic tool. The API is hosted on `http://localhost:8000` by default.

## Usage Note (Important)
Because this application uses a single session instance per runtime currently, **you must successfully call the `/api/login` endpoint first** to establish an authenticated session with the ONT device. All subsequent API calls will use this established session.

---

## 1. Authentication (Login)

Establishes a connection and logs into the target ONT device.

- **URL:** `/api/login`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`

### Request Body

```json
{
  "ip": "192.168.1.1",
  "username": "admin",
  "password": "admin"
}
```

### Success Response (200 OK)

```json
{
  "status": "success", 
  "message": "Login successful"
}
```

### Error Response (200 OK status, but logic error)

```json
{
  "status": "error", 
  "message": "Login failed. Check credentials or IP."
}
```

---

## 2. Get Device Status

Retrieves the basic status of the ONT device (firmware version, uptime, LAN port statuses).

- **URL:** `/api/status`
- **Method:** `GET`
- **Headers:** None

### Success Response (200 OK)

Returns a JSON object containing parsed status key-value pairs.

```json
{
  "Device Uptime": "1 days, 2 hours, 30 mins",
  "Firmware Version": "V1.0.0",
  ...
}
```

### Error Response (401 Unauthorized)

If the login was not performed first.

```json
{
  "detail": "Not logged in"
}
```

---

## 3. Get Device Information

Retrieves detailed device information (model, serial number, MAC address).

- **URL:** `/api/info`
- **Method:** `GET`
- **Headers:** None

### Success Response (200 OK)

Returns a JSON object mapping information fields.

```json
{
  "Model": "FD504G-X-R410",
  "MAC Address": "A4:E2:XX:XX:XX:XX",
  ...
}
```

---

## 4. Get PON Information

Retrieves PON optical statuses (TX Power, RX Power, Voltage, Temperature).

- **URL:** `/api/pon`
- **Method:** `GET`
- **Headers:** None

### Success Response (200 OK)

Returns a JSON object describing optical parameters.

```json
{
  "Tx Power": "2.1 dBm",
  "Rx Power": "-18.5 dBm",
  ...
}
```

---

## 5. Network Diagnostic: Ping

Orders the ONT to ping an external IP address. Wait times might vary as polling takes place.

- **URL:** `/api/ping`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`

### Request Body

```json
{
  "target_ip": "8.8.8.8"
}
```

### Success Response (200 OK)

Returns a JSON object containing the ping result string and the status (`ONLINE`, `OFFLINE/RTO`, `DNS ERROR`, `UNKNOWN`).

```json
{
  "status": "ONLINE",
  "output": "PING 8.8.8.8 (8.8.8.8): 56 data bytes\n64 bytes from 8.8.8.8: seq=0 ttl=118 time=8.591 ms\n..."
}
```

---

## 6. Network Diagnostic: Traceroute

Orders the ONT to execute a traceroute command against an external IP address.

- **URL:** `/api/traceroute`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`

### Request Body

```json
{
  "target_ip": "8.8.8.8"
}
```

### Success Response (200 OK)

Returns a JSON object containing the traceroute raw text output.

```json
{
  "status": "SUCCESS",
  "output": "traceroute to 8.8.8.8 (8.8.8.8), 30 hops max, 38 byte packets\n 1  10.0.0.1  1.234 ms  1.567 ms  1.890 ms\n..."
}
```
