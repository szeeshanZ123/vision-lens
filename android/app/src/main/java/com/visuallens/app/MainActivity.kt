package com.visuallens.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.visuallens.app.databinding.ActivityMainBinding
import org.json.JSONObject
import java.util.Locale

/**
 * Visual Lens Native Android WebView Wrapper.
 *
 * Hosts the Visual Lens web application inside a hardware-accelerated WebView,
 * bridging Android hardware permissions (Camera & Audio), Native Text-to-Speech (TTS),
 * and Native Speech-to-Text (STT) to standard Web APIs.
 */
class MainActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    companion object {
        private const val TAG = "VisualLensApp"

        /**
         * Vision Lens Verified Production Deployment URL
         */
        const val WEB_APP_URL = "https://vision-lens-ivory.vercel.app"

        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO
        )
    }

    private lateinit var binding: ActivityMainBinding
    private var pendingPermissionRequest: PermissionRequest? = null

    // Native Android TextToSpeech Engine
    private var textToSpeech: TextToSpeech? = null
    private var isTtsReady = false
    private var pendingSpeechText: String? = null

    // Native Android SpeechRecognizer Engine
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false

    // Android runtime permission requester
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val cameraGranted = permissions[Manifest.permission.CAMERA] ?: false
        val audioGranted = permissions[Manifest.permission.RECORD_AUDIO] ?: false

        if (cameraGranted) {
            // Fulfill pending WebView WebRTC/getUserMedia request if waiting
            pendingPermissionRequest?.let { req ->
                runOnUiThread {
                    req.grant(req.resources)
                    pendingPermissionRequest = null
                }
            }
        } else {
            pendingPermissionRequest?.let { req ->
                runOnUiThread {
                    req.deny()
                    pendingPermissionRequest = null
                }
            }
            Toast.makeText(
                this,
                getString(R.string.permission_camera_rationale),
                Toast.LENGTH_LONG
            ).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Initialize Android Native Text-to-Speech engine
        initTextToSpeech()

        // Initialize Android Native SpeechRecognizer
        initSpeechRecognizer()

        setupBackNavigation()
        setupWebView()
        setupListeners()

        // Preemptively check runtime permissions on launch
        checkAndRequestPermissions()

        // Load the web application
        loadTargetUrl()

        // Handle voice action launch intents
        handleVoiceIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleVoiceIntent(intent)
    }

    private fun handleVoiceIntent(intent: Intent?) {
        val action = intent?.action ?: return
        Log.d(TAG, "Launched with action: $action")
        if (action == Intent.ACTION_VOICE_COMMAND ||
            action == Intent.ACTION_ASSIST ||
            action == "com.google.android.gms.actions.SEARCH_ACTION" ||
            action == android.provider.MediaStore.ACTION_IMAGE_CAPTURE ||
            action == android.provider.MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA
        ) {
            val query = intent.getStringExtra(android.app.SearchManager.QUERY) ?: ""
            val jsonParam = JSONObject.quote(query)
            sendJsCallback("window.onVoiceAppLaunch && window.onVoiceAppLaunch($jsonParam);")
        }
    }

    /**
     * Initializes the Android Native TextToSpeech engine.
     */
    private fun initTextToSpeech() {
        try {
            textToSpeech = TextToSpeech(applicationContext, this)
        } catch (e: Exception) {
            Log.e(TAG, "TTS initialization failed: ${e.message}", e)
        }
    }

    /**
     * Callback received when the TextToSpeech engine completes initialization.
     */
    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val currentLocale = Locale.getDefault()
            val result = textToSpeech?.setLanguage(currentLocale)
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                // Fallback to English US
                textToSpeech?.setLanguage(Locale.US)
            }

            textToSpeech?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    Log.d(TAG, "TTS speaking started")
                    sendJsCallback("window.onTTSStart && window.onTTSStart();")
                }

                override fun onDone(utteranceId: String?) {
                    Log.d(TAG, "TTS speaking finished")
                    sendJsCallback("window.onTTSDone && window.onTTSDone();")
                }

                override fun onError(utteranceId: String?) {
                    Log.e(TAG, "TTS speaking error")
                    sendJsCallback("window.onTTSError && window.onTTSError();")
                }

                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?, errorCode: Int) {
                    Log.e(TAG, "TTS speaking error code: $errorCode")
                    sendJsCallback("window.onTTSError && window.onTTSError();")
                }
            })

            isTtsReady = true
            Log.d(TAG, "TTS initialized")

            // Flush any speech requested prior to initialization finishing
            pendingSpeechText?.let {
                speakText(it)
                pendingSpeechText = null
            }
        } else {
            isTtsReady = false
            Log.e(TAG, "TTS initialization failed")
        }
    }

    /**
     * Speaks text aloud using Android's native offline TTS engine.
     */
    fun speakText(text: String) {
        if (!isTtsReady || textToSpeech == null) {
            Log.w(TAG, "TTS not ready yet, queuing speech request")
            pendingSpeechText = text
            return
        }

        Log.d(TAG, "TTS speak requested: $text")

        textToSpeech?.speak(
            text,
            TextToSpeech.QUEUE_FLUSH,
            null,
            "VisualLens_Utterance_${System.currentTimeMillis()}"
        )
    }

    /**
     * Stops any ongoing TTS speech immediately.
     */
    fun stopSpeaking() {
        textToSpeech?.stop()
    }

    /**
     * Initializes the Android Native SpeechRecognizer on the main thread.
     */
    private fun initSpeechRecognizer() {
        runOnUiThread {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                Log.w(TAG, "Speech recognition is not available on this device.")
                return@runOnUiThread
            }

            try {
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
                    setRecognitionListener(createRecognitionListener())
                }
                Log.d(TAG, "SpeechRecognizer initialized successfully.")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize SpeechRecognizer: ${e.message}", e)
            }
        }
    }

    /**
     * Builds the RecognitionListener callbacks that dispatch events directly to the WebView JS.
     */
    private fun createRecognitionListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                Log.d(TAG, "SpeechRecognizer: Ready for speech")
                sendJsCallback("window.onSpeechReady && window.onSpeechReady();")
            }

            override fun onBeginningOfSpeech() {
                Log.d(TAG, "SpeechRecognizer: Beginning of speech")
                isListening = true
                sendJsCallback("window.onSpeechStart && window.onSpeechStart();")
            }

            override fun onRmsChanged(rmsdB: Float) {
                // Optional volume level feedback if needed
            }

            override fun onBufferReceived(buffer: ByteArray?) {}

            override fun onEndOfSpeech() {
                Log.d(TAG, "SpeechRecognizer: End of speech")
                isListening = false
                sendJsCallback("window.onSpeechEnd && window.onSpeechEnd();")
            }

            override fun onError(error: Int) {
                isListening = false
                val errorMsg = when (error) {
                    SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                    SpeechRecognizer.ERROR_CLIENT -> "Speech recognition client error"
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission required"
                    SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network connection error"
                    SpeechRecognizer.ERROR_NO_MATCH -> "No speech recognized"
                    SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Speech recognizer is busy"
                    SpeechRecognizer.ERROR_SERVER -> "Speech server error"
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech input detected"
                    else -> "Speech recognition error ($error)"
                }
                Log.w(TAG, "SpeechRecognizer onError: $errorMsg ($error)")
                val jsonParam = JSONObject.quote(errorMsg)
                sendJsCallback("window.onSpeechError && window.onSpeechError($jsonParam, $error);")
            }

            override fun onResults(results: Bundle?) {
                isListening = false
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val recognizedText = matches?.firstOrNull() ?: ""
                Log.d(TAG, "SpeechRecognizer result: $recognizedText")
                val jsonParam = JSONObject.quote(recognizedText)
                sendJsCallback("window.onSpeechResult && window.onSpeechResult($jsonParam);")
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val partialText = matches?.firstOrNull()
                if (!partialText.isNullOrBlank()) {
                    val jsonParam = JSONObject.quote(partialText)
                    sendJsCallback("window.onSpeechPartial && window.onSpeechPartial($jsonParam);")
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    /**
     * Safely executes a JavaScript statement on the WebView.
     */
    private fun sendJsCallback(script: String) {
        runOnUiThread {
            try {
                binding.webView.evaluateJavascript(script, null)
            } catch (e: Exception) {
                Log.e(TAG, "Error evaluating JS callback: ${e.message}")
            }
        }
    }

    /**
     * Starts listening for voice commands using Android Native SpeechRecognizer.
     */
    fun startListening() {
        runOnUiThread {
            // Stop any ongoing TTS before listening so it doesn't transcribe itself
            stopSpeaking()

            // Verify audio recording permission
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                permissionLauncher.launch(arrayOf(Manifest.permission.RECORD_AUDIO))
                val jsonParam = JSONObject.quote("Microphone permission required")
                sendJsCallback("window.onSpeechError && window.onSpeechError($jsonParam, 9);")
                return@runOnUiThread
            }

            try {
                // Safely destroy and recreate recognizer for fresh recognition session
                try {
                    speechRecognizer?.cancel()
                    speechRecognizer?.destroy()
                } catch (_: Exception) {}

                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
                    setRecognitionListener(createRecognitionListener())
                }

                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                    putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
                }
                speechRecognizer?.startListening(intent)
                isListening = true
                Log.d(TAG, "SpeechRecognizer startListening initiated with fresh instance.")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start speech recognition: ${e.message}", e)
                val jsonParam = JSONObject.quote("Failed to start speech recognizer: ${e.message}")
                sendJsCallback("window.onSpeechError && window.onSpeechError($jsonParam, 0);")
            }
        }
    }

    /**
     * Stops listening for speech.
     */
    fun stopListening() {
        runOnUiThread {
            try {
                speechRecognizer?.stopListening()
                isListening = false
            } catch (e: Exception) {
                Log.e(TAG, "Failed to stop speech recognizer: ${e.message}")
            }
        }
    }

    /**
     * Secure JavaScript Interface exposed to the WebView as `window.AndroidTTS`.
     */
    inner class AndroidTTSInterface {
        @JavascriptInterface
        fun speak(text: String?) {
            Log.d(TAG, "TTS speak requested")
            if (text.isNullOrBlank()) return
            runOnUiThread {
                speakText(text)
            }
        }

        @JavascriptInterface
        fun stop() {
            Log.d(TAG, "TTS stop requested")
            runOnUiThread {
                stopSpeaking()
            }
        }

        @JavascriptInterface
        fun isAvailable(): Boolean {
            return isTtsReady
        }
    }

    /**
     * Secure JavaScript Interface exposed to the WebView as `window.AndroidSpeech`.
     */
    inner class AndroidSpeechInterface {
        @JavascriptInterface
        fun startListening() {
            Log.d(TAG, "AndroidSpeech startListening called from JS")
            this@MainActivity.startListening()
        }

        @JavascriptInterface
        fun stopListening() {
            Log.d(TAG, "AndroidSpeech stopListening called from JS")
            this@MainActivity.stopListening()
        }

        @JavascriptInterface
        fun isAvailable(): Boolean {
            return SpeechRecognizer.isRecognitionAvailable(this@MainActivity)
        }
    }

    /**
     * Secure JavaScript Interface exposed to the WebView as `window.AndroidHaptics`.
     */
    inner class AndroidHapticsInterface {
        private val vibrator: android.os.Vibrator? by lazy {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                val vibratorManager = getSystemService(android.content.Context.VIBRATOR_MANAGER_SERVICE) as? android.os.VibratorManager
                vibratorManager?.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                getSystemService(android.content.Context.VIBRATOR_SERVICE) as? android.os.Vibrator
            }
        }

        @JavascriptInterface
        fun vibrate(milliseconds: Long) {
            try {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    vibrator?.vibrate(
                        android.os.VibrationEffect.createOneShot(
                            milliseconds,
                            android.os.VibrationEffect.DEFAULT_AMPLITUDE
                        )
                    )
                } else {
                    @Suppress("DEPRECATION")
                    vibrator?.vibrate(milliseconds)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Vibration failed: ${e.message}")
            }
        }

        @JavascriptInterface
        fun targetCenteredPulse() {
            // Rapid double pulse to signal object is centered
            try {
                val pattern = longArrayOf(0, 40, 60, 40)
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    vibrator?.vibrate(
                        android.os.VibrationEffect.createWaveform(pattern, -1)
                    )
                } else {
                    @Suppress("DEPRECATION")
                    vibrator?.vibrate(pattern, -1)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Haptic pulse failed: ${e.message}")
            }
        }

        @JavascriptInterface
        fun hazardAlertPulse() {
            // Strong warning pulse for urgent hazards
            try {
                val pattern = longArrayOf(0, 120, 80, 120, 80, 120)
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    vibrator?.vibrate(
                        android.os.VibrationEffect.createWaveform(pattern, -1)
                    )
                } else {
                    @Suppress("DEPRECATION")
                    vibrator?.vibrate(pattern, -1)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Hazard vibration failed: ${e.message}")
            }
        }

        @JavascriptInterface
        fun isAvailable(): Boolean {
            return vibrator?.hasVibrator() == true
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val webView = binding.webView
        val settings = webView.settings

        // Core HTML5 & JavaScript features
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true

        // Multimedia & Speech: allow audio playback without explicit touch gesture requirement
        settings.mediaPlaybackRequiresUserGesture = false

        // File and caching optimizations - disable local file access for defense-in-depth
        settings.allowFileAccess = false
        settings.allowContentAccess = false
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // Enable zoom controls if needed by user accessibility
        settings.setSupportZoom(true)
        settings.builtInZoomControls = false
        settings.displayZoomControls = false

        // Mixed content configuration (enforces strict HTTPS)
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW

        // Register Native JavaScript Bridges: TTS, STT, and Haptics
        webView.addJavascriptInterface(AndroidTTSInterface(), "AndroidTTS")
        webView.addJavascriptInterface(AndroidSpeechInterface(), "AndroidSpeech")
        webView.addJavascriptInterface(AndroidHapticsInterface(), "AndroidHaptics")

        // WebChromeClient: Handles browser permissions (Camera/Mic for WebRTC/getUserMedia) & progress
        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    val requestedResources = request.resources
                    var needsCamera = false
                    var needsAudio = false

                    for (resource in requestedResources) {
                        if (resource == PermissionRequest.RESOURCE_VIDEO_CAPTURE) {
                            needsCamera = true
                        }
                        if (resource == PermissionRequest.RESOURCE_AUDIO_CAPTURE) {
                            needsAudio = true
                        }
                    }

                    val hasCameraPermission = ContextCompat.checkSelfPermission(
                        this@MainActivity,
                        Manifest.permission.CAMERA
                    ) == PackageManager.PERMISSION_GRANTED

                    val hasAudioPermission = ContextCompat.checkSelfPermission(
                        this@MainActivity,
                        Manifest.permission.RECORD_AUDIO
                    ) == PackageManager.PERMISSION_GRANTED

                    if ((!needsCamera || hasCameraPermission) && (!needsAudio || hasAudioPermission)) {
                        request.grant(requestedResources)
                    } else {
                        pendingPermissionRequest = request
                        val permissionsToRequest = mutableListOf<String>()
                        if (needsCamera && !hasCameraPermission) {
                            permissionsToRequest.add(Manifest.permission.CAMERA)
                        }
                        if (needsAudio && !hasAudioPermission) {
                            permissionsToRequest.add(Manifest.permission.RECORD_AUDIO)
                        }
                        permissionLauncher.launch(permissionsToRequest.toTypedArray())
                    }
                }
            }

            override fun onPermissionRequestCanceled(request: PermissionRequest) {
                super.onPermissionRequestCanceled(request)
                if (pendingPermissionRequest == request) {
                    pendingPermissionRequest = null
                }
            }

            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress < 100) {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.progressBar.progress = newProgress
                } else {
                    binding.progressBar.visibility = View.GONE
                }
            }
        }

        // WebViewClient: Handles navigation inside app & connection error pages safely
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val targetUri = request?.url ?: return false
                val host = targetUri.host?.lowercase(Locale.ROOT) ?: ""
                val scheme = targetUri.scheme?.lowercase(Locale.ROOT) ?: ""

                // Verify if scheme is web HTTP/S
                if (scheme != "http" && scheme != "https") {
                    return true
                }

                // Whitelist trusted app hosts (Vercel deployment domain, localhost, or LAN Wi-Fi testing)
                val targetUrlHost = android.net.Uri.parse(WEB_APP_URL).host?.lowercase(Locale.ROOT) ?: ""
                val isTrustedHost = host == targetUrlHost ||
                    host.endsWith(".vercel.app") ||
                    host == "localhost" ||
                    host == "127.0.0.1" ||
                    host == "10.0.2.2" ||
                    host.startsWith("192.168.") ||
                    host.startsWith("10.")

                if (isTrustedHost) {
                    return false // Load in WebView with native JavaScript bridge intact
                }

                // If navigating to an untrusted external third-party site, open safely in system browser
                try {
                    val browserIntent = Intent(Intent.ACTION_VIEW, targetUri)
                    startActivity(browserIntent)
                } catch (e: Exception) {
                    Log.w(TAG, "Could not open external URL in browser: ${e.message}")
                }
                return true
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                super.onPageStarted(view, url, favicon)
                binding.errorContainer.visibility = View.GONE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                binding.swipeRefreshLayout.isRefreshing = false
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                // Only display full error view if the main frame failed to load
                if (request?.isForMainFrame == true) {
                    showError()
                }
            }

            override fun onReceivedHttpError(
                view: WebView?,
                request: WebResourceRequest?,
                errorResponse: WebResourceResponse?
            ) {
                super.onReceivedHttpError(view, request, errorResponse)
                if (request?.isForMainFrame == true && (errorResponse?.statusCode ?: 200) >= 500) {
                    showError()
                }
            }
        }
    }

    private fun setupListeners() {
        // Swipe to refresh
        binding.swipeRefreshLayout.setOnRefreshListener {
            binding.webView.reload()
        }

        // Retry button on error screen
        binding.btnRetry.setOnClickListener {
            binding.errorContainer.visibility = View.GONE
            binding.webView.visibility = View.VISIBLE
            loadTargetUrl()
        }
    }

    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (binding.webView.canGoBack()) {
                    binding.webView.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })
    }

    private fun checkAndRequestPermissions() {
        val missingPermissions = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missingPermissions.isNotEmpty()) {
            permissionLauncher.launch(missingPermissions.toTypedArray())
        }
    }

    private fun loadTargetUrl() {
        binding.errorContainer.visibility = View.GONE
        binding.webView.visibility = View.VISIBLE
        binding.webView.loadUrl(WEB_APP_URL)
    }

    private fun showError() {
        binding.swipeRefreshLayout.isRefreshing = false
        binding.progressBar.visibility = View.GONE
        binding.webView.visibility = View.GONE
        binding.errorContainer.visibility = View.VISIBLE
    }

    override fun onDestroy() {
        // Safely shutdown native SpeechRecognizer
        speechRecognizer?.let {
            it.cancel()
            it.destroy()
        }
        speechRecognizer = null

        // Safely shutdown native TextToSpeech
        textToSpeech?.let {
            it.stop()
            it.shutdown()
        }
        textToSpeech = null

        binding.webView.destroy()
        super.onDestroy()
    }
}
