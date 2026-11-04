# 👁️ Vision Lens — Hackathon Edition

> **AI-Powered, Voice-First Visual Assistant for Visually Impaired Users**  
> *Combining Real-Time Computer Vision, Gemini Multimodal Spatial Intelligence, and Native Android Accessibility.*

[![Live Web Application](https://img.shields.io/badge/Vercel-Live%20App-00f0ff?style=flat-square&logo=vercel)](https://vision-lens-ivory.vercel.app)
[![Android APK](https://img.shields.io/badge/Android-APK%20v1.2.0-06d6a0?style=flat-square&logo=android)](https://vision-lens-ivory.vercel.app/download)
[![Gemini Vision](https://img.shields.io/badge/Google%20GenAI-Gemini%202.5%20Flash-ffb703?style=flat-square&logo=google)](https://aistudio.google.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.115+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)

---

## 📋 Table of Contents
1. [Overview](#-overview)
2. [Verified Production Deployment](#-verified-production-deployment)
3. [Key Capabilities](#-key-capabilities)
4. [System Architecture](#-system-architecture)
5. [Android Studio Project](#-android-studio-project)
6. [Quickstart & Local Setup](#-quickstart--local-setup)
7. [Project Documentation Links](#-project-documentation-links)

---

## 🎯 Overview

Vision Lens transforms any standard smartphone into an intelligent spatial guide. By pairing hardware camera access with Google's Gemini Vision multimodal models and an offline-capable spatial reasoning engine, Vision Lens helps visually impaired users perceive their immediate environment:

- **What's in front of me?**: Detailed scene summaries with spatial placement context.
- **Where are my items?**: Targeted search for keys, bottles, and personal items with HUD directional guidance (*pan left*, *pan right*, *target centered*).
- **Is my path clear?**: 7-zone horizontal positioning and obstacle categorization with clock-face bearings (*12 o'clock*, *2 o'clock*).
- **Hands-Free Voice First**: Zero-tap continuous voice loop with non-blocking Text-to-Speech synthesis.

---

## 🌐 Verified Production Deployment

- **Production Application URL**: [https://vision-lens-ivory.vercel.app](https://vision-lens-ivory.vercel.app)
- **APK Download Portal**: [https://vision-lens-ivory.vercel.app/download](https://vision-lens-ivory.vercel.app/download)
- **Backend Health Check**: [https://vision-lens-ivory.vercel.app/api/health](https://vision-lens-ivory.vercel.app/api/health)
- **Vercel Project Dashboard**: [https://vercel.com/szeeshanz123s-projects/vision-lens/6kwDAURymHAeSX8a8jAU654tFfdy](https://vercel.com/szeeshanz123s-projects/vision-lens/6kwDAURymHAeSX8a8jAU654tFfdy)
- **Canonical GitHub Repository**: [https://github.com/szeeshanZ123/vision-lens](https://github.com/szeeshanZ123/vision-lens)

---

## 💡 Key Capabilities

| Feature | Status | Implementation Details |
|---|---|---|
| **Live Camera Viewfinder** | 🟢 Implemented | WebRTC `getUserMedia`, front/rear switching, canvas downscaling (max 800px) |
| **Scene Description** | 🟢 Implemented | Gemini 2.5 Flash via official `google-genai` Python SDK |
| **7-Zone Spatial Positioning** | 🟢 Implemented | Fine-grained zoning: far-left, left, slightly-left, center, slightly-right, right, far-right |
| **Clock-Face Directions** | 🟢 Implemented | Maps object coordinates to intuitive bearings (e.g., *12 o'clock*, *2 o'clock*) |
| **Voice State Machine & Watchdog** | 🟢 Implemented | Universal watchdog preventing TTS lockups; mutual exclusion between STT & TTS |
| **Android Native Bridges** | 🟢 Implemented | `window.AndroidTTS`, `window.AndroidSpeech`, `window.AndroidHaptics` |
| **Target Finding & Audio Beacon** | 🟢 Implemented | Dynamic stereo synthesizer cues and target-centered haptic vibration |
| **Continuous Spatial Guidance** | 🟡 Partial | Snapshot interval guidance with anti-repetition speech cooldown |
| **Text Reading Prompt** | 🟡 Partial | Gemini Vision multimodal text extraction prompt (non-offline OCR) |
| **On-Device Offline ML & LiDAR** | 🔴 Planned | Quantized TFLite edge models, ARCore depth sensing (see [FUTURE_SCOPE.md](FUTURE_SCOPE.md)) |

---

## 🏛️ System Architecture

```
vision-lens/
├── app.py                           # FastAPI server, security headers & API routes
├── api/index.py                     # Vercel Serverless Function entry point
├── vercel.json                      # Vercel deployment routing configuration
├── requirements.txt                 # Backend Python dependencies
├── .env.example                     # Environment configuration template
│
├── services/
│   ├── gemini_service.py            # Google GenAI SDK integration with Gemini 2.5 Flash
│   ├── spatial_reasoning.py         # 7-zone horizontal positioning & clock-face math
│   ├── depth_estimation.py          # Bounding box scale & physical priors estimation
│   ├── vision_service.py            # Base64 decoding, Pillow/OpenCV validation
│   └── speech_service.py            # Lazy-initialized server-side pyttsx3 fallback
│
├── models/
│   └── vision_result.py             # Pydantic schemas: DetectedObject, VisionResult
│
├── static/
│   ├── camera.js                    # WebRTC streaming, non-blocking TTS & Android bridge
│   ├── style.css                    # Accessible high-contrast mobile dark theme
│   └── vision-lens.apk              # Pre-compiled latest Android release package
│
├── templates/
│   ├── index.html                   # Accessible camera & voice assistant interface
│   └── download.html                # APK download portal & dynamic QR code
│
└── VisionLens-Hackathon-Android/    # Clean, standalone Android Studio project
    ├── app/src/main/java/.../       # MainActivity.kt with WebView & native hardware bridges
    └── build.gradle.kts             # Gradle build configuration (Target SDK 34)
```

---

## 📱 Android Studio Project

The dedicated Android Studio project is located in:
```
VisionLens-Hackathon-Android/
```

- **Loads Verified Production URL**: `https://vision-lens-ivory.vercel.app`
- **Application ID**: `com.visuallens.app`
- **Compiled Debug APK**: `VisionLens-Hackathon-Android/app/build/outputs/apk/debug/app-debug.apk`
- To open and build in Android Studio, follow the instructions in [ANDROID_SETUP.md](ANDROID_SETUP.md).

---

## 🚀 Quickstart & Local Setup

### 1. Configure Credentials
```bash
cp .env.example .env
```
Edit `.env` and set your `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/app/apikey):
```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here...
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Local Server
```bash
python app.py
```
Open `http://localhost:8000` in your web browser.

---

## 📚 Project Documentation Links

- 🏛️ [ARCHITECTURE.md](ARCHITECTURE.md) — Comprehensive technical architecture and data flow.
- 🔄 [WORKFLOW.md](WORKFLOW.md) — State machines, speech lifecycle, and interaction flows.
- ✨ [FEATURES.md](FEATURES.md) — Implemented vs. partially implemented vs. planned features.
- 📱 [ANDROID_SETUP.md](ANDROID_SETUP.md) — Step-by-step Android Studio setup and APK building.
- 🚀 [DEPLOYMENT.md](DEPLOYMENT.md) — Vercel serverless deployment and environment variables guide.
- 🔭 [FUTURE_SCOPE.md](FUTURE_SCOPE.md) — Post-hackathon roadmap and planned capabilities.
