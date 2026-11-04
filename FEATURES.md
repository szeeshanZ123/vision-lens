# ✨ Vision Lens — Feature Matrix

This document provides a clear, honest distinction between features that are fully implemented and verified, partially implemented, and planned for future releases.

---

## 🟢 Implemented Features (Verified in Codebase)

### 1. Mobile Camera Capture & WebRTC Streaming
- High-frame-rate live video viewfinder using `navigator.mediaDevices.getUserMedia`.
- Front / rear camera switching (`environment` vs `user` facing).
- Dynamic client-side downscaling (max 800px) and quality compression (JPEG 0.75) for fast network transmission.
- Dark theme camera reticle overlay with visual scan animation.

### 2. Multimodal Spatial Reasoning Pipeline
- Official Google GenAI SDK (`google-genai`) integration with `gemini-2.5-flash` model.
- 7-zone horizontal positioning engine (`far_left`, `left`, `slightly_left`, `center`, `slightly_right`, `right`, `far_right`).
- 12-hour clock face direction assignment (e.g., *12 o'clock*, *2 o'clock*, *9 o'clock*).
- Path clearance analysis (`clear`, `partially_blocked`, `blocked`, `uncertain`).
- Approximate metric distance tiers based on object physical scale priors and bounding box dimensions.

### 3. Voice-First Interaction & Multi-Tier TTS
- Non-blocking state machine preventing TTS / STT audio feedback loops.
- Universal watchdog timer recovering automatically from dropped speech events.
- Bi-directional Android native `TextToSpeech` and `SpeechRecognizer` bridge via WebView interfaces.
- Web Speech API fallback for standard mobile and desktop browsers.
- Manual speech replay button (`Speak Response`) and pause/stop control.

### 4. Interactive Guidance & Quick Actions
- Quick query suggestion chips:
  - 👁️ Describe Scene (*"What do you see?"*)
  - 🔑 Find Keys (*"Find my keys"*)
  - 💧 Find Bottle (*"Find my water bottle"*)
  - 🚶 Check Path (*"Is path clear?"*)
  - 📖 Read Text Prompt (*"Read this text"*)
- Target finding mode with HUD reticle centering indicators (pan left, pan right, target centered).
- Audio beacon tone cues (spatial left/center/right stereo audio synthesizer).
- Hardware haptic pulses via Android native vibrator bridge (`AndroidHaptics`).

### 5. Native Android Studio Project
- Clean standalone Android project: `VisionLens-Hackathon-Android/`.
- Pre-configured with verified production URL: `https://vision-lens-ivory.vercel.app`.
- Full runtime permission handling for `CAMERA` and `RECORD_AUDIO`.
- Verified debug APK generation via Gradle.

---

## 🟡 Partially Implemented Features

### 1. Text Reading / Verbatim Transcription
- **Current State**: Uses Gemini Vision multimodal prompt adaptation to read visible signs, labels, or large headings in the captured frame.
- **Limitation**: Does not feature a dedicated offline OCR pipeline (e.g., Tesseract or ML Kit on-device text recognition). Performance is dependent on cloud Gemini image resolution and network connectivity.

### 2. Continuous Spatial Guidance Loop
- **Current State**: Supports hands-free interval scanning with a 3.5-second anti-repetition speech cooldown and client-side HUD arrows.
- **Limitation**: Runs frame-by-frame snapshot analysis over HTTP rather than an edge-computed video stream or continuous WebRTC video pipeline.

### 3. Obstacle Collision Warnings
- **Current State**: Evaluates bounding box vertical ground positions to classify objects as walking path obstacles.
- **Limitation**: Relies on 2D monocular estimation without hardware LiDAR or ToF (Time-of-Flight) depth sensors.

---

## 🔴 Planned Future Features (Not Implemented)

### 1. On-Device Offline Medicine Recognition
- Dedicated packaging barcode / NDC lookup database for identifying prescription and OTC medications offline.

### 2. Turn-by-Turn Indoor / Outdoor GPS Navigation
- Integration with OpenStreetMap, Google Maps, or indoor BLE beacon navigation for walking routes.

### 3. Real-Time On-Device Object Detection (YOLO / MediaPipe)
- Local edge model execution on Android NPU for sub-50ms obstacle detection without internet access.

### 4. Currency Recognition & denomination reading
- Specialized banknote classification engine for paper currency denominations.

