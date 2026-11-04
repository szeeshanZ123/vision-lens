# 📱 Vision Lens — Android Setup & Build Guide

## 1. Project Location

The verified, standalone Android Studio project is located in:
```
VisionLens-Hackathon-Android/
```

- **Application Package / ID**: `com.visuallens.app`
- **Minimum SDK**: Android 7.0 (API Level 24)
- **Target / Compile SDK**: Android 14 (API Level 34)
- **Programming Language**: Kotlin 2.x
- **Build System**: Gradle 9.x / Android Gradle Plugin 8.6+

---

## 2. Prerequisites

1. **Android Studio**: Android Studio Jellyfish (2023.3.1) / Koala (2024.1.1) or newer.
2. **Java Development Kit**: JDK 17 (shipped natively with Android Studio under `<Android Studio Install Dir>/jbr`).
3. **Android SDK Platform 34**: Installed via Android Studio SDK Manager.

---

## 3. Opening the Project in Android Studio

1. Launch Android Studio.
2. Select **File -> Open...** (or click **Open** on the Welcome screen).
3. Navigate to and select the `VisionLens-Hackathon-Android` folder inside your repository.
4. Allow Android Studio to sync Gradle dependencies.

---

## 4. Configuration Check (`MainActivity.kt`)

In `VisionLens-Hackathon-Android/app/src/main/java/com/visuallens/app/MainActivity.kt`:

```kotlin
companion object {
    /**
     * Vision Lens Verified Production Deployment URL
     */
    const val WEB_APP_URL = "https://vision-lens-ivory.vercel.app"
    ...
}
```

- **Production Mode**: Uses the verified production Vercel deployment URL (`https://vision-lens-ivory.vercel.app`).
- **Local Testing Mode**: If testing a local server on the same Wi-Fi network, replace `WEB_APP_URL` with `http://<YOUR_COMPUTER_LOCAL_IP>:8000`.

---

## 5. Building the Debug APK from Command Line

To build the APK from terminal:

```powershell
# Set JAVA_HOME to Android Studio's bundled JDK
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

# Navigate to project and assemble
cd VisionLens-Hackathon-Android
.\gradlew.bat assembleDebug
```

The compiled APK will be created at:
```
VisionLens-Hackathon-Android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 6. Installing on a Physical Android Device

1. Enable **Developer Options** on your Android device (Settings -> About Phone -> tap "Build Number" 7 times).
2. Enable **USB Debugging** in Developer Options.
3. Connect your device via USB.
4. Verify the device is recognized:
   ```powershell
   adb devices
   ```
5. Install the APK:
   ```powershell
   adb install -r VisionLens-Hackathon-Android/app/build/outputs/apk/debug/app-debug.apk
   ```
6. Grant Camera and Audio permissions when prompted on first launch.

