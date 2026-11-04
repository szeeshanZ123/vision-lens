# Visual Lens - Android Native Shell

A minimal native Android wrapper (Kotlin + WebView) for the **Gemini Visual Lens** web application.

---

## 1. Quick Setup & Configuration

Open [`android/app/src/main/java/com/visuallens/app/MainActivity.kt`](file:///c:/Users/ASUS/OneDrive/vision/android/app/src/main/java/com/visuallens/app/MainActivity.kt) and set your deployed Vercel URL:

```kotlin
companion object {
    /**
     * PASTE YOUR DEPLOYED VERCEL URL HERE
     */
    const val WEB_APP_URL = "https://visionlens-gamma.vercel.app"
    ...
}
```

> **Local Wi-Fi Testing**: If you are testing locally before deploying to Vercel, you can set `WEB_APP_URL` to `http://<YOUR_COMPUTER_LOCAL_IP>:8000` (e.g. `http://192.168.1.10:8000`).

---

## 2. Opening in Android Studio

1. Open **Android Studio**.
2. Select **Open** and navigate to the `android/` folder inside this repository.
3. Allow Gradle to sync dependencies automatically.
4. Connect an Android device (via USB with USB debugging enabled) or start an Android emulator.
5. Click **Run ('app')** (Green play button) or build the APK via **Build > Build Bundle(s) / APK(s) > Build APK(s)**.

---

## 3. Architecture & Features

```text
Android App (Visual Lens)
     ↓
Hardware-Accelerated WebView
     ↓
WebChromeClient (WebRTC & Camera Permission Bridge)
     ↓
Existing Vercel Web Application
     ↓
Existing Backend (Python / FastAPI)
     ↓
Google Gemini 3.5 Flash Multimodal API
```

- **Hardware Camera Bridge**: `WebChromeClient.onPermissionRequest` bridges standard HTML5 `navigator.mediaDevices.getUserMedia()` to native Android runtime permissions.
- **Audio & TTS**: Unrestricted audio playback enables smooth Web Speech API / TTS spoken feedback.
- **Offline / Error Handling**: Displays a native retry screen if the network is disconnected or server is offline.
- **Security**: No Gemini API keys or sensitive backend credentials exist in the Android client.
