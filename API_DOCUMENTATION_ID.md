# Dokumentasi API C-Data ONT Tool

Dokumen ini menjelaskan daftar *endpoint* REST API yang tersedia di aplikasi C-Data ONT *diagnostic tool*. API berjalan pada `http://localhost:8000` secara *default*.

## Catatan Penggunaan (Penting)
Karena aplikasi ini (sementara waktu) hanya mendukung satu *session instance* per runtime, **Anda diwajibkan untuk memanggil _endpoint_ `/api/login` terlebih dahulu** sebelum memanggil API lainnya. Kesuksesan login akan menyiapkan koneksi ke perangkat ONT target. Semua API lanjutan akan menggunakan *session* tersebut.

---

## 1. Autentikasi (Login)

Merintis koneksi ke jaringan target dan melakukan proses *login* ke antarmuka perangkat ONT.

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

### Response Berhasil (200 OK)

```json
{
  "status": "success", 
  "message": "Login successful"
}
```

### Response Gagal (Status 200 OK, Logika HTTP atau Kredensial Salah)

```json
{
  "status": "error", 
  "message": "Login failed. Check credentials or IP."
}
```

---

## 2. Dapatkan Status Perangkat (Get Device Status)

Mengambil parameter *runtime* dari ONT, seperti versi *firmware*, waktu aktif *device* (uptime), dan status koneksi LAN Port.

- **URL:** `/api/status`
- **Method:** `GET`
- **Headers:** Kosong (None)

### Response Berhasil (200 OK)

Mengembalikan objek JSON berbentuk *key-value/dictionary*.

```json
{
  "Device Uptime": "1 days, 2 hours, 30 mins",
  "Firmware Version": "V1.0.0",
  ...
}
```

### Response Gagal (401 Unauthorized)

Jika _session_ login ke _device_ target tidak ditemukan.

```json
{
  "detail": "Not logged in"
}
```

---

## 3. Dapatkan Info Perangkat (Get Device Info)

Mengambil status perangkat lunak pasif pada perangkat, seperti Nomor Seri, Model, dan *MAC Address*.

- **URL:** `/api/info`
- **Method:** `GET`
- **Headers:** Kosong (None)

### Response Berhasil (200 OK)

Mengembalikan objek deskriptif JSON.

```json
{
  "Model": "FD504G-X-R410",
  "MAC Address": "A4:E2:XX:XX:XX:XX",
  ...
}
```

---

## 4. Dapatkan Info PON (Get PON Info)

Melakukan _scraping_ informasi sinyal dan suhu modul optik PON ONT. 

- **URL:** `/api/pon`
- **Method:** `GET`
- **Headers:** Kosong (None)

### Response Berhasil (200 OK)

Mengembalikan objek informatif JSON tentang optik *fiber*.

```json
{
  "Tx Power": "2.1 dBm",
  "Rx Power": "-18.5 dBm",
  ...
}
```

---

## 5. Diagnostik Jaringan: Tes Ping

Memerintahkan perangkat ONT untuk menjalankan *command* `ping` ke alamat IP terluar (Internet / Local target IP). Waktu tunggu (Latency Delay) bergantung pada lamanya *device* membalas *log* di web.

- **URL:** `/api/ping`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`

### Request Body

```json
{
  "target_ip": "8.8.8.8"
}
```

### Response Berhasil (200 OK)

Mengembalikan objek JSON yang mendeskripsikan ringkasan akhir (`ONLINE`, `OFFLINE/RTO`, `DNS ERROR`, `UNKNOWN`) beserta _output baris Command Line Interface (CLI)_-nya.

```json
{
  "status": "ONLINE",
  "output": "PING 8.8.8.8 (8.8.8.8): 56 data bytes\n64 bytes from 8.8.8.8: seq=0 ttl=118 time=8.591 ms\n..."
}
```

---

## 6. Diagnostik Jaringan: Tes Traceroute

Memerintahkan ONT untuk menjalankan _tracing_ paket jaringan `traceroute` ke IP internet atau target secara estafet loncatan data, kemudian memberikan *raw output*-nya kembali.

- **URL:** `/api/traceroute`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`

### Request Body

```json
{
  "target_ip": "8.8.8.8"
}
```

### Response Berhasil (200 OK)

Mengembalikan parameter *raw output* perintah *traceroute* hasil konsol ONT.

```json
{
  "status": "SUCCESS",
  "output": "traceroute to 8.8.8.8 (8.8.8.8), 30 hops max, 38 byte packets\n 1  10.0.0.1  1.234 ms  1.567 ms  1.890 ms\n..."
}
```
