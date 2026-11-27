# 📱 BlueChat — Offline Bluetooth Messenger

> **Language**: **English** | [Arabic Version (العربية)](README_AR.md)

**BlueChat** is a fast, lightweight peer-to-peer (P2P) messaging application that works completely **offline** without internet over Bluetooth RFCOMM channels, redesigned with the modern **Telegram Blue** theme and aesthetics.

---

## 🎨 Interface Preview (Telegram Blue UI)

```text
+-------------------------------------------------------+
| (BC) BlueChat                      [Listen] [Devices] |
|      online                                           |
+-------------------------------------------------------+
|                                                       |
|  +-------------------------------------------------+  |
|  | Hello! Connecting via Bluetooth SPP             |  |
|  |                                           12:00 |  |
|  +-------------------------------------------------+  |
|                                                       |
|       +--------------------------------------------+  |
|       | Hey! Check out this voice note & picture:  |  |
|       |                                      12:01 |  |
|       +--------------------------------------------+  |
|                                                       |
|       +--------------------------------------------+  |
|       | (Play)  Voice Message         00:15        |  |
|       |                               12:01   Read |  |
|       +--------------------------------------------+  |
|                                                       |
|  +-------------------------------------------------+  |
|  | [VIDEO] sample_clip.mp4 (4.5 MB)                |  |
|  | [████████████████████ 100%]                     |  |
|  | [               Play Video                    ] |  |
|  |                                           12:02 |  |
|  +-------------------------------------------------+  |
|                                                       |
+-------------------------------------------------------+
| (+)  [ Message...                        ] (Mic) (Send)|
+-------------------------------------------------------+
```

---

## ✨ Modern Telegram Features

| Feature | Description |
| :--- | :--- |
| **🔷 Telegram Blue Theme** | Signature Telegram Sky Blue header (`#239ED8`), cloud chat background (`#E0E9F0`), and soft blue outgoing bubbles (`#D2EBFB`). |
| **👤 Telegram Circular Avatar** | Clean circular badge with initials and live status (`online` / `offline` / `typing...`). |
| **✍️ Live Typing Indicator** | Displays `typing...` in real-time when the remote partner types in the message field. |
| **🎙️ Voice Messages** | Circular play button (`#28A7E5`) with inline duration timer. |
| **🖼️ Photo & Video Sharing** | Full inline picture previews, video transfer with speed display (`KB/s`), and CRC32 verification. |
| **📡 Dual Mode** | One device acts as **Server** (`Listen`), the other acts as **Client** (`Devices`). |
| **❤️ Keep-Alive Heartbeat** | Automatic ping/pong every 10 seconds to keep RFCOMM sockets active. |

---

## 🚀 Quick Start (Testing on PC)

### 1. Requirements
Ensure Python 3.11 is used:
```bash
py -3.11 -m pip install -r requirements.txt
```

### 2. Run Host (Instance 1)
```bash
py -3.11 main.py --port 8888
```
👉 Click **`Listen`** on the top bar.

### 3. Run Partner (Instance 2)
In a second terminal:
```bash
py -3.11 main.py --port 8889
```
👉 Click **`Devices`** and select **`Simulated Partner A (Port 8888)`**.

---

## 📱 Building Android APK
Pushing to GitHub triggers an automated build via GitHub Actions in [.github/workflows/build_apk.yml](.github/workflows/build_apk.yml). The compiled APK is saved in the **Artifacts** section!
