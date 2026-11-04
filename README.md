
# 👁️ Gemini Visual Lens

A minimal, accessible, mobile-first computer-vision prototype that turns your phone's camera into an intelligent spatial visual assistant for visually impaired users. Built using **Python 3.11+**, **FastAPI**, and the official **Google GenAI SDK (Gemini Vision)**.

---

## 🎯 What it Does

1. **Opens in any mobile or desktop browser** with live camera access (`navigator.mediaDevices.getUserMedia`).
2. **Captures the camera frame** in real-time when "Capture & Analyze" is tapped.
3. **Validates & optimizes the image** in Python using **Pillow** and **OpenCV**.
4. **Queries Google Gemini 2.5 Flash** with a spatial prompt for scene understanding (identifies objects, relative distances: *very close*, *near*, *medium*, *far*, and positions: *left*, *center*, *right*).
5. **Returns validated structured JSON** via **Pydantic**.
6. **Displays accessible high-contrast cards** and **speaks the description aloud** using text-to-speech.

---

## 📁 Project Architecture & File Breakdown

```
vision/
├── app.py                      # FastAPI server routes, health check & orchestrator
├── requirements.txt            # Python dependencies (FastAPI, Google GenAI SDK, OpenCV, Pillow, Pydantic)
├── .env                        # Local secrets (GEMINI_API_KEY) — never exposed to client
├── .env.example                # Configuration template
├── .gitignore                  # Ignores .env and Python cache files
│
├── services/
│   ├── gemini_service.py       # Google GenAI SDK integration with spatial prompt & schema validation
│   ├── vision_service.py       # OpenCV & Pillow image decoding, validation, resizing, and blur check
│   └── speech_service.py       # Python-side Text-To-Speech service (pyttsx3 fallback)
│
├── models/
│   └── vision_result.py        # Pydantic schemas (DetectedObject, VisionResult, AnalyzeRequest)
│
├── static/
│   ├── style.css               # Accessible high-contrast mobile design system
│   └── camera.js               # Minimal JavaScript: getUserMedia(), frame capture, POST /api/analyze
│
└── templates/
    └── index.html              # Mobile-first semantic HTML5 interface
```

### Role of Each File

- **`app.py`**: The central FastAPI application. Serves the web interface, mounts static assets, and exposes `/api/analyze` and `/api/health`.
- **`services/gemini_service.py`**: Communicates securely with Google's Gemini Vision model using the official `google-genai` Python SDK. Enforces structured JSON output and handles prompt engineering.
- **`services/vision_service.py`**: Safely decodes base64 camera frames, validates image dimensions, downscales oversized frames for fast network transfer, and measures blur/lighting using OpenCV and Pillow.
- **`services/speech_service.py`**: Thread-safe audio speech synthesis using `pyttsx3` for Python-side speech generation.
- **`models/vision_result.py`**: Strongly typed Pydantic models ensuring every Gemini response conforms to the expected `{ summary, objects: [...], uncertainty }` schema.
- **`static/camera.js`**: **Minimal client-side script strictly limited to hardware access**: streams video from camera, paints frame onto hidden canvas on button press, sends base64 image to FastAPI, and triggers browser SpeechSynthesis.
- **`static/style.css`**: Accessible dark-mode design with high-contrast amber/cyan accents, large touch targets (64px buttons), and responsive layout.
- **`templates/index.html`**: Clean semantic HTML5 page with camera viewfinder, reticle overlay, status indicator, and dynamic result cards.

---

## 🔄 How the Phone Camera Communicates with FastAPI

```
Phone Browser (HTML5/JS)
  │
  ├─ 1. getUserMedia() streams camera video to <video> element
  ├─ 2. User taps "Capture & Analyze"
  ├─ 3. Video frame is painted to hidden <canvas> and converted to Base64 JPEG
  └─ 4. fetch('/api/analyze', { method: 'POST', body: { image: base64 } })
         │
         ▼
FastAPI Backend (Python)
  │
  ├─ 5. app.py receives payload and passes to vision_service.py
  ├─ 6. Pillow & OpenCV decode, check quality, and optimize image
  ├─ 7. gemini_service.py sends image + spatial prompt to Gemini API
  ├─ 8. Gemini returns structured JSON (objects, distances, positions)
  ├─ 9. Pydantic models/vision_result.py validates payload
  └─ 10. HTTP 200 JSON returned to Phone Browser
         │
         ▼
Phone Browser (HTML5/JS)
  │
  ├─ 11. Renders high-contrast detection cards (Left / Center / Right, Distance)
  └─ 12. window.speechSynthesis automatically speaks the summary aloud
```

---

## 🚀 Quickstart Guide

### 1. Get a Gemini API Key
1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Sign in with your Google account and click **"Create API key"**.
3. Copy your API key.

### 2. Configure Environment Variables
Open `.env` in the project directory and paste your API key:
```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here...
HOST=0.0.0.0
PORT=8000
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the Application
Run the Python application:
```bash
python app.py
```
Or with uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📱 Testing on your Phone

1. Ensure your phone and computer are connected to the **same Wi-Fi network**.
2. Find your computer's local IP address:
   - On Windows: Run `ipconfig` in CMD/PowerShell (look for IPv4 Address, e.g. `192.168.1.15`).
   - On macOS/Linux: Run `ifconfig` or `ip a`.
3. Open your mobile browser (Chrome / Safari) and navigate to:
   ```
   http://<YOUR_LOCAL_IP>:8000
   ```
   *(e.g., `http://192.168.1.15:8000`)*
4. Allow camera permissions when prompted.
5. Tap **"Capture & Analyze"** to test live scene detection and audio speech output!

---

## 🔒 Security & Scope

- **API Key Security**: The `GEMINI_API_KEY` is loaded strictly on the Python backend via `python-dotenv`. No client-side JavaScript or HTML ever has access to your credentials.
- **Pure Python Logic**: All validation, AI communication, Pydantic schemas, and data processing are managed exclusively by Python.
- **Future Expansion Ready**: The architecture is decoupled and modular, ready to integrate voice commands ("Find my keys"), target-specific object detection, and continuous spatial guidance.
