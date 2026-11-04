/**
 * Gemini Visual Lens - Client-Side Camera, Voice-First Interaction,
 * Object Finder, Continuous Guidance & Spatial Audio/Haptic Navigation Bridge
 * 
 * Phase 3 Capabilities:
 * 1. Target-Specific Object Finding ("Find my keys", "Where is my cup?")
 * 2. Continuous Hands-Free Spatial Guidance Loop with anti-repetition speech
 * 3. Web Audio API Synthesizer Spatial Beacon (pitch & stereo panning)
 * 4. Android Native Haptics Bridge (window.AndroidHaptics) + Web Vibration API
 * 5. Urgent Obstacle & Hazard Alert System with priority audio/haptic cues
 * 6. Clock-face directions (e.g., "10 o'clock", "12 o'clock", "2 o'clock")
 */

(function () {
  'use strict';

  // DOM Elements - Core
  const video = document.getElementById('cameraVideo');
  const canvas = document.getElementById('captureCanvas');
  const captureBtn = document.getElementById('captureBtn');
  const voiceBtn = document.getElementById('voiceBtn');
  const voiceBtnText = document.getElementById('voiceBtnText');
  const voiceIcon = document.getElementById('voiceIcon');
  const voiceWave = document.getElementById('voiceWave');
  const voiceEngineBadge = document.getElementById('voiceEngineBadge');
  const voiceCommandCard = document.getElementById('voiceCommandCard');
  const voiceFeedbackTitle = document.getElementById('voiceFeedbackTitle');
  const voiceCommandText = document.getElementById('voiceCommandText');

  // DOM Elements - Phase 3 & Web Query Additions
  const queryForm = document.getElementById('queryForm');
  const queryInput = document.getElementById('queryInput');
  const sendQueryBtn = document.getElementById('sendQueryBtn');
  const quickChips = document.querySelectorAll('.quick-chip');

  const continuousGuidanceBtn = document.getElementById('continuousGuidanceBtn');
  const guidanceBtnText = document.getElementById('guidanceBtnText');
  const guidanceIcon = document.getElementById('guidanceIcon');
  const continuousModeBadge = document.getElementById('continuousModeBadge');
  const audioBeaconToggle = document.getElementById('audioBeaconToggle');

  const hazardBanner = document.getElementById('hazardBanner');
  const hazardTitle = document.getElementById('hazardTitle');
  const hazardMessage = document.getElementById('hazardMessage');

  const targetSearchBanner = document.getElementById('targetSearchBanner');
  const targetSearchTitle = document.getElementById('targetSearchTitle');
  const targetSearchStatus = document.getElementById('targetSearchStatus');
  const cancelTargetBtn = document.getElementById('cancelTargetBtn');

  const centerReticle = document.getElementById('centerReticle');
  const leftGuideArrow = document.getElementById('leftGuideArrow');
  const rightGuideArrow = document.getElementById('rightGuideArrow');
  const targetLockedPill = document.getElementById('targetLockedPill');

  const guidanceCard = document.getElementById('guidanceCard');
  const guidanceDirectionText = document.getElementById('guidanceDirectionText');

  const switchCameraBtn = document.getElementById('switchCameraBtn');
  const cameraPlaceholder = document.getElementById('cameraPlaceholder');
  const grantCameraBtn = document.getElementById('grantCameraBtn');
  const cameraStatusText = document.getElementById('cameraStatusText');
  const statusPill = document.getElementById('statusPill');
  const statusText = document.getElementById('statusText');
  const scanLine = document.getElementById('scanLine');

  const errorBanner = document.getElementById('errorBanner');
  const errorTitle = document.getElementById('errorTitle');
  const errorMessage = document.getElementById('errorMessage');
  const dismissErrorBtn = document.getElementById('dismissErrorBtn');

  const resultsSection = document.getElementById('resultsSection');
  const spokenSummary = document.getElementById('spokenSummary');
  const processingTimeBadge = document.getElementById('processingTimeBadge');
  const uncertaintyCard = document.getElementById('uncertaintyCard');
  const uncertaintyText = document.getElementById('uncertaintyText');
  const objectsList = document.getElementById('objectsList');
  const speakBtn = document.getElementById('speakBtn');
  const stopSpeakBtn = document.getElementById('stopSpeakBtn');
  const autoSpeakToggle = document.getElementById('autoSpeakToggle');
  const zeroTapToggle = document.getElementById('zeroTapToggle');

  // Application State
  let currentStream = null;
  let currentFacingMode = 'environment';
  let isAnalyzing = false;
  let isListening = false;
  let isSpeaking = false;
  let isZeroTapActive = true;
  let zeroTapLoopTimer = null;
  let currentAppState = 'READY'; // "READY" | "LISTENING" | "ANALYZING" | "SPEAKING"
  let hasGreeted = false;
  let lastGuidanceSpeechTime = 0;
  let lastGuidanceText = '';
  let lastResultText = '';
  let lastSpokenSummary = '';
  let feedbackTimeout = null;

  // Phase 3 State
  let isContinuousGuidanceActive = false;
  let continuousTimer = null;
  let activeSearchTarget = null; // e.g. "keys", "water bottle"
  let activeMode = 'standard'; // "standard" | "find_target" | "continuous_guidance" | "text_reading"

  // Web Audio Context for Spatial Synthesizer Beacon
  let audioCtx = null;

  function getAudioContext() {
    if (!audioCtx) {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (AudioCtxClass) {
        audioCtx = new AudioCtxClass();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }
    return audioCtx;
  }

  /**
   * Spatial Synthesizer Audio Beacon
   */
  function playSpatialAudioBeacon(position = 'center', distance = 'near') {
    if (!audioBeaconToggle || !audioBeaconToggle.checked) return;

    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;

      // Frequency based on distance / centering
      let freq = 520; // Default center
      if (position === 'center') {
        freq = distance === 'very_close' ? 880 : 660; // High pitch when on target
      } else if (position === 'left') {
        freq = 440;
      } else {
        freq = 480;
      }

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);

      // Stereo Pan (-1 = full left, 0 = center, 1 = full right)
      if (pan) {
        const panValue = position === 'left' ? -0.8 : position === 'right' ? 0.8 : 0.0;
        pan.pan.setValueAtTime(panValue, ctx.currentTime);
      }

      // Quick pleasant pulse envelope (120ms)
      gain.gain.setValueAtTime(0.01, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);

      if (pan) {
        osc.connect(pan);
        pan.connect(gain);
      } else {
        osc.connect(gain);
      }
      gain.connect(ctx.destination);

      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.13);
    } catch (e) {
      console.warn('Audio beacon error:', e);
    }
  }

  /**
   * Urgent Hazard Chime
   */
  function playHazardChime() {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(750, now);
      osc.frequency.exponentialRampToValueAtTime(320, now + 0.25);

      gain.gain.setValueAtTime(0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.26);
    } catch (e) {
      console.warn('Hazard chime error:', e);
    }
  }

  /**
   * Target Located Success Chime
   */
  function playTargetLocatedChime() {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      [523.25, 659.25, 783.99].forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const start = now + idx * 0.08;

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.15, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.15);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(start);
        osc.stop(start + 0.16);
      });
    } catch (e) {
      console.warn('Target located chime error:', e);
    }
  }

  /**
   * Haptic Feedback Dispatcher (Native Android Bridge with Web API Fallback)
   */
  function triggerHapticPulse(type = 'center') {
    // 1. Android Native Haptics Bridge (MainActivity.kt)
    if (typeof AndroidHaptics !== 'undefined' && AndroidHaptics.isAvailable && AndroidHaptics.isAvailable()) {
      if (type === 'center') {
        AndroidHaptics.targetCenteredPulse();
      } else if (type === 'hazard') {
        AndroidHaptics.hazardAlertPulse();
      } else {
        AndroidHaptics.vibrate(50);
      }
      return;
    }

    // 2. Standard Web Vibration API Fallback
    if ('vibrate' in navigator) {
      try {
        if (type === 'center') {
          navigator.vibrate([40, 60, 40]);
        } else if (type === 'hazard') {
          navigator.vibrate([120, 80, 120, 80, 120]);
        } else {
          navigator.vibrate(50);
        }
      } catch (e) {
        console.warn('Vibration API error:', e);
      }
    }
  }

  // Speech Recognition (Web Fallback)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let webRecognizer = null;
  let speechSessionActive = false;
  let accumulatedTranscript = '';
  let speechProcessed = false;

  // Initialize Web Speech Synthesis (Browser fallback)
  const synth = window.speechSynthesis;
  let currentUtterance = null;

  // Pre-fetch browser TTS voices
  let cachedVoices = [];
  function updateVoiceList() {
    if (synth) {
      try {
        cachedVoices = synth.getVoices() || [];
      } catch (_) {}
    }
  }
  if (synth) {
    updateVoiceList();
    if (synth.onvoiceschanged !== undefined) {
      synth.onvoiceschanged = updateVoiceList;
    }
  }

  /**
   * Determine available Speech Recognition Engine (Android Native or Web API)
   */
  function initSpeechEngine() {
    if (typeof AndroidSpeech !== 'undefined' && AndroidSpeech.startListening) {
      if (voiceEngineBadge) voiceEngineBadge.textContent = 'Voice: Android Native';
      return 'android';
    } else if (SpeechRecognition) {
      if (voiceEngineBadge) voiceEngineBadge.textContent = 'Voice: Web Speech Ready';
      return 'web';
    }

    if (voiceEngineBadge) voiceEngineBadge.textContent = 'Voice: Type / Quick';
    return 'none';
  }

  /**
   * Updates application status pill and visual indicators
   */
  function updateStatus(text, type = 'ready') {
    if (statusText) statusText.textContent = text;
    if (statusPill) {
      const dot = statusPill.querySelector('.status-dot');
      if (dot) {
        dot.className = `status-dot ${type}`;
      }
    }
  }

  /**
   * Sets unified application state across UI indicators
   * States: "READY" | "LISTENING" | "ANALYZING" | "SPEAKING"
   */
  function setAppState(state, customLabel = null) {
    currentAppState = state;
    const label = customLabel || `● ${state}`;

    if (state === 'READY') {
      updateStatus(label, 'ready');
      if (voiceBtnText) voiceBtnText.textContent = 'Tap & Speak';
      if (voiceBtn) voiceBtn.classList.remove('listening');
      if (voiceWave) voiceWave.classList.add('hidden');
      if (scanLine) scanLine.classList.add('hidden');
    } else if (state === 'LISTENING') {
      updateStatus(label, 'listening');
      if (voiceBtnText) voiceBtnText.textContent = 'Listening... (Tap to Cancel)';
      if (voiceBtn) voiceBtn.classList.add('listening');
      if (voiceWave) voiceWave.classList.remove('hidden');
      if (scanLine) scanLine.classList.add('hidden');
    } else if (state === 'ANALYZING') {
      updateStatus(label, 'analyzing');
      if (voiceBtnText) voiceBtnText.textContent = 'Analyzing Scene...';
      if (voiceBtn) voiceBtn.classList.remove('listening');
      if (voiceWave) voiceWave.classList.add('hidden');
      if (scanLine) scanLine.classList.remove('hidden');
    } else if (state === 'SPEAKING') {
      updateStatus(label, 'speaking');
      if (voiceBtnText) voiceBtnText.textContent = 'Speaking Response...';
      if (voiceBtn) voiceBtn.classList.remove('listening');
      if (voiceWave) voiceWave.classList.add('hidden');
      if (scanLine) scanLine.classList.add('hidden');
    }
  }

  /**
   * Factory function to create a fresh SpeechRecognition instance on every session.
   * Reusing a stopped SpeechRecognition instance in WebKit/Chromium causes InvalidStateError.
   */
  function createWebSpeechRecognizer() {
    if (!SpeechRecognition) return null;
    try {
      const recognizer = new SpeechRecognition();
      recognizer.continuous = false;
      recognizer.interimResults = true;
      recognizer.lang = 'en-US';
      recognizer.maxAlternatives = 1;

      recognizer.onstart = () => {
        speechSessionActive = true;
        speechProcessed = false;
        accumulatedTranscript = '';
        setListeningUI(true);
        showVoiceFeedback('Listening...', 'Say "Find my bottle", "What do you see?", or "Start guidance"');
      };

      recognizer.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item && item[0]) {
            if (item.isFinal) {
              finalTranscript += item[0].transcript;
            } else {
              interimTranscript += item[0].transcript;
            }
          }
        }

        const currentText = (finalTranscript || interimTranscript).trim();
        if (currentText) {
          accumulatedTranscript = currentText;
          showVoiceFeedback('Hearing...', `"${currentText}"`);
          if (queryInput) queryInput.value = currentText;
        }

        if (finalTranscript && finalTranscript.trim()) {
          speechProcessed = true;
          onVoiceCommandRecognized(finalTranscript.trim());
        }
      };

      recognizer.onerror = (event) => {
        console.warn('Web Speech Recognition error:', event.error);
        speechSessionActive = false;
        setListeningUI(false);
        
        if (event.error === 'no-speech') {
          // In Zero-Tap mode, re-arm listening quietly after silence without annoying alert
          if (isZeroTapActive && !isAnalyzing && !isSpeaking && !isContinuousGuidanceActive) {
            scheduleZeroTapReArm(800);
            return;
          }
        }

        let msg = "I couldn't hear you. Please try again or type in the box below.";
        if (event.error === 'not-allowed') {
          msg = 'Microphone permission blocked. Please enable mic access in your browser or type your question below.';
        } else if (event.error === 'network') {
          msg = 'Speech recognition network error. Please try again or type below.';
        } else if (event.error === 'no-speech') {
          msg = 'No voice detected. Tap and speak or type your question.';
        }

        if (!isZeroTapActive) {
          handleVoiceError(msg);
        } else if (isZeroTapActive && !isAnalyzing && !isSpeaking) {
          scheduleZeroTapReArm(1500);
        }
      };

      recognizer.onend = () => {
        speechSessionActive = false;
        setListeningUI(false);

        // Fallback: if interim audio was heard but isFinal wasn't explicitly triggered before silence
        if (!speechProcessed && accumulatedTranscript && accumulatedTranscript.trim().length > 1) {
          speechProcessed = true;
          onVoiceCommandRecognized(accumulatedTranscript.trim());
          return;
        }

        // In Zero-Tap mode, if no command was processed and we are not busy, return to listening
        if (!speechProcessed && isZeroTapActive && !isAnalyzing && !isSpeaking && !isContinuousGuidanceActive) {
          scheduleZeroTapReArm(800);
        }
      };

      return recognizer;
    } catch (e) {
      console.warn('Could not instantiate SpeechRecognition:', e);
      return null;
    }
  }

  /**
   * Schedules a return to listening in Zero-Tap mode after a short conversational pause
   */
  function scheduleZeroTapReArm(delayMs = 800) {
    if (zeroTapLoopTimer) {
      clearTimeout(zeroTapLoopTimer);
      zeroTapLoopTimer = null;
    }
    if (!isZeroTapActive || isAnalyzing || isSpeaking || isContinuousGuidanceActive) {
      return;
    }
    zeroTapLoopTimer = setTimeout(() => {
      if (isZeroTapActive && !isListening && !isAnalyzing && !isSpeaking && !isContinuousGuidanceActive) {
        startVoiceListening();
      }
    }, delayMs);
  }

  /**
   * Android Native Speech Callbacks (Invoked from MainActivity.kt)
   */
  window.onSpeechReady = function () {
    setListeningUI(true);
    showVoiceFeedback('Listening...', 'Say "Find my bottle", "What do you see?", or "Start guidance"');
  };

  window.onSpeechStart = function () {
    setListeningUI(true);
  };

  window.onSpeechPartial = function (partialText) {
    if (partialText) {
      showVoiceFeedback('Hearing...', `"${partialText}"`);
      if (queryInput) queryInput.value = partialText;
    }
  };

  window.onSpeechResult = function (recognizedText) {
    setListeningUI(false);
    if (queryInput) queryInput.value = recognizedText;
    onVoiceCommandRecognized(recognizedText);
  };

  window.onSpeechError = function (errorMsg, errorCode) {
    setListeningUI(false);
    console.warn('[Android Native STT Error]:', errorMsg, errorCode);

    // Silence / No-match / Timeout in Zero-Tap mode: re-arm listening after brief pause
    if (isZeroTapActive && !isAnalyzing && !isSpeaking && !isContinuousGuidanceActive) {
      scheduleZeroTapReArm(800);
      return;
    }

    let friendly = "I couldn't hear you. Please try again or type below.";
    if (errorMsg && errorMsg.includes('permission')) {
      friendly = 'Microphone permission is required.';
      handleVoiceError(friendly);
    } else if (!isZeroTapActive) {
      handleVoiceError(friendly);
    }
  };

  window.onSpeechEnd = function () {
    setListeningUI(false);
    if (isZeroTapActive && !isAnalyzing && !isSpeaking && !isContinuousGuidanceActive) {
      scheduleZeroTapReArm(800);
    }
  };

  /**
   * Android Native TTS Bridge Callbacks (Invoked from MainActivity.kt)
   */
  window.onTTSStart = function () {
    isSpeaking = true;
    setAppState('SPEAKING');
    if (speakBtn) speakBtn.classList.add('hidden');
    if (stopSpeakBtn) stopSpeakBtn.classList.remove('hidden');
  };

  window.onTTSDone = function () {
    onSpeechFinished();
  };

  window.onTTSError = function () {
    onSpeechFinished();
  };

  /**
   * Android Voice App Launch Callback
   */
  window.onVoiceAppLaunch = function (query) {
    console.log('[Voice Launch Intent received]:', query);
    unlockAudioAndTTS();
    if (query && query.trim()) {
      if (queryInput) queryInput.value = query.trim();
      onVoiceCommandRecognized(query.trim());
    } else {
      setTimeout(() => {
        startVoiceListening();
      }, 700);
    }
  };

  /**
   * Called when Text-to-Speech completes speaking
   */
  function onSpeechFinished() {
    isSpeaking = false;
    if (speakWatchdogTimer) {
      clearTimeout(speakWatchdogTimer);
      speakWatchdogTimer = null;
    }
    if (speakBtn) speakBtn.classList.remove('hidden');
    if (stopSpeakBtn) stopSpeakBtn.classList.add('hidden');
    window._activeUtterance = null;
    currentUtterance = null;

    if (isContinuousGuidanceActive) {
      setAppState('READY', 'Continuous Guidance Active');
    } else if (isZeroTapActive && !isAnalyzing) {
      setAppState('READY');
      scheduleZeroTapReArm(700);
    } else {
      setAppState('READY');
    }
  }

  /**
   * Triggers the zero-tap startup greeting safely
   */
  function triggerStartupGreeting(playAudio = false) {
    if (hasGreeted) return;
    hasGreeted = true;
    const greeting = "Vision Lens is ready. What can I help you with?";
    showVoiceFeedback("Vision Lens Ready", greeting);
    if (playAudio && isZeroTapActive) {
      speak(greeting);
    }
  }

  /**
   * Starts Listening for Voice Commands
   */
  function startVoiceListening() {
    // If speaking, stop speech first
    if (isSpeaking) {
      stopSpeech();
    }
    if (isAnalyzing && !isContinuousGuidanceActive) return;

    if (zeroTapLoopTimer) {
      clearTimeout(zeroTapLoopTimer);
      zeroTapLoopTimer = null;
    }

    // Stop ongoing speech so microphone doesn't pick up the app's own voice
    stopSpeech();

    // Unlock Web Audio context on user gesture
    unlockAudioAndTTS();

    if (isListening || speechSessionActive) {
      stopVoiceListening();
      return;
    }

    // 1. Android Native App Bridge
    if (typeof AndroidSpeech !== 'undefined' && AndroidSpeech.startListening) {
      try {
        AndroidSpeech.startListening();
        setListeningUI(true);
        return;
      } catch (e) {
        console.warn('AndroidSpeech failed, falling back to Web Speech:', e);
      }
    }

    // 2. Web Speech API (with fresh instance recreation)
    if (SpeechRecognition) {
      try {
        if (webRecognizer) {
          try { webRecognizer.abort(); } catch (_) {}
          webRecognizer = null;
        }

        webRecognizer = createWebSpeechRecognizer();
        if (webRecognizer) {
          webRecognizer.start();
          return;
        }
      } catch (err) {
        console.warn('SpeechRecognition start error:', err);
        setListeningUI(false);
        if (queryInput) queryInput.focus();
        handleVoiceError('Voice recognition error. You can type in the box below.');
        return;
      }
    }

    // 3. Fallback for browsers without Web Speech Recognition (e.g. Firefox, HTTP origins)
    showVoiceFeedback('Type Your Request', 'Voice recognition is unavailable in this browser. Use the input box below.', true);
    if (queryInput) queryInput.focus();
  }

  /**
   * Stops Listening for Voice Commands
   */
  function stopVoiceListening() {
    if (zeroTapLoopTimer) {
      clearTimeout(zeroTapLoopTimer);
      zeroTapLoopTimer = null;
    }
    if (typeof AndroidSpeech !== 'undefined' && AndroidSpeech.stopListening) {
      try { AndroidSpeech.stopListening(); } catch (_) {}
    }
    if (webRecognizer) {
      try { webRecognizer.stop(); } catch (_) {}
      try { webRecognizer.abort(); } catch (_) {}
      webRecognizer = null;
    }
    speechSessionActive = false;
    setListeningUI(false);
  }

  /**
   * Updates Voice Button and Listening UI
   */
  function setListeningUI(listening) {
    isListening = listening;
    if (listening) {
      setAppState('LISTENING');
    } else {
      if (!isAnalyzing && !isSpeaking) {
        setAppState('READY', isContinuousGuidanceActive ? 'Continuous Guidance Active' : '● READY');
      }
    }
  }

  /**
   * Displays Recognized Command Feedback Card
   */
  function showVoiceFeedback(title, message, isError = false) {
    if (!voiceCommandCard) return;

    if (feedbackTimeout) {
      clearTimeout(feedbackTimeout);
      feedbackTimeout = null;
    }

    voiceCommandCard.classList.remove('hidden');
    if (isError) {
      voiceCommandCard.classList.add('error');
    } else {
      voiceCommandCard.classList.remove('error');
    }

    if (voiceFeedbackTitle) voiceFeedbackTitle.textContent = title;
    if (voiceCommandText) voiceCommandText.textContent = message;

    feedbackTimeout = setTimeout(() => {
      voiceCommandCard.classList.add('hidden');
    }, 6000);
  }

  function handleVoiceError(friendlyMessage) {
    showVoiceFeedback('Voice Notice', friendlyMessage, true);
    speak(friendlyMessage);
  }

  /**
   * Enhanced Voice Command Routing Layer (Phase 3)
   */
  function parseVoiceCommand(rawCommand) {
    if (!rawCommand) return { intent: 'SCENE_DESCRIPTION', query: 'What do you see?', mode: 'standard' };
    
    const text = rawCommand.trim().toLowerCase().replace(/[.,!?;:]/g, '');

    // 0. Zero-Tap / Hands-Free Voice Control
    if (text.includes('disable zero tap') || text.includes('turn off zero tap') || text.includes('manual mode')) {
      return { intent: 'DISABLE_ZEROTAP', query: rawCommand, mode: 'standard' };
    }
    if (text.includes('enable zero tap') || text.includes('turn on zero tap') || text.includes('zero tap mode') || text.includes('hands free mode') || text.includes('hands free')) {
      return { intent: 'ENABLE_ZEROTAP', query: rawCommand, mode: 'standard' };
    }

    // 1. System Commands (Repeat, Cancel)
    if (text === 'repeat' || text.includes('repeat that') || text.includes('say that again') || text.includes('say again')) {
      return { intent: 'SYSTEM_REPEAT', query: rawCommand, mode: 'standard' };
    }

    // 2. Stop / Cancel Guidance Commands (High Priority, Phonetic & Multi-phrase tolerance)
    const isStopOrCancel = text === 'stop' || text === 'cancel' || text === 'quit' || text === 'pause' || text === 'halt' || text === 'end';
    const hasStopWord = /\b(stop|end|quit|pause|halt|cancel|turn\s*off|disable|exit)\b/i.test(text);
    const hasGuidanceWord = /\b(guidance|guide|guiding|navigation|navigate|continuous|continues|continue|continual|loop|mode|scan|tracking)\b/i.test(text);

    if (
      (isContinuousGuidanceActive && (isStopOrCancel || hasStopWord)) ||
      (hasStopWord && hasGuidanceWord) ||
      text.includes('stop continuous') ||
      text.includes('stop continues') ||
      text.includes('stop continue') ||
      text.includes('stop guidance') ||
      text.includes('stop guiding') ||
      text.includes('stop navigation') ||
      text.includes('stop search') ||
      text.includes('exit guidance') ||
      text.includes('cancel guidance') ||
      text.includes('turn off guidance') ||
      text.includes('disable guidance') ||
      text.includes('end guidance') ||
      text.includes('cancel search')
    ) {
      return { intent: 'STOP_GUIDANCE', query: rawCommand, mode: 'standard' };
    }

    if (text === 'cancel' || text.includes('go back to listening')) {
      return { intent: 'SYSTEM_CANCEL', query: rawCommand, mode: 'standard' };
    }

    // 3. Start Continuous Guidance Control
    if (
      text.includes('start continuous guidance') ||
      text.includes('start continues guidance') ||
      text.includes('start continue guidance') ||
      text.includes('start guidance') ||
      text.includes('start navigation') ||
      text.includes('continuous mode') ||
      text.includes('continues mode') ||
      text.includes('guide me') ||
      text.includes('keep guiding') ||
      text.includes('enable guidance') ||
      text.includes('begin guidance')
    ) {
      return { intent: 'START_GUIDANCE', query: rawCommand, mode: 'continuous_guidance' };
    }

    // 4. Text Reading & OCR Intent ("Read this", "Read the bottle", "What does this say?", "What is written?")
    const textReadingPatterns = [
      /\bread\b/i,
      /\breading\b/i,
      /\bocr\b/i,
      /\bwritten\b/i,
      /\bwhat\s*(does|is)\s*(this|it|that)\s*(say|written)\b/i,
      /\bwhat's\s*(written|on|the text)\b/i,
      /\bcan you read\b/i,
      /\bread\s*(the|this|all|my)?\s*(text|sign|label|bottle|document|book|page|paper|menu|screen|words|packaging)\b/i,
      /\bread\s*(aloud|out\s*loud|out)\b/i
    ];

    const isTextReading = textReadingPatterns.some((pat) => pat.test(text));
    if (isTextReading) {
      return { intent: 'TEXT_READING', query: rawCommand, mode: 'text_reading' };
    }

    // 5. Targeted Object Finding Intent ("Find my bottle", "Where is my cup?", "Locate the door")
    const findPatterns = [
      /^(?:find|locate|spot|search for)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+)$/i,
      /^(?:where is|where are)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+)$/i,
      /^(?:help me find)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+)$/i,
    ];

    for (const pattern of findPatterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        const targetItem = match[1].trim();
        // Ignore generic query words
        if (!['text', 'sign', 'words', 'written', 'this', 'anything', 'something'].includes(targetItem.toLowerCase())) {
          return {
            intent: 'TARGET_FIND',
            query: rawCommand,
            mode: 'find_target',
            targetObject: targetItem
          };
        }
      }
    }

    // 6. Scene Description Intent ("What do you see?", "Describe my surroundings", "What is ahead?")
    if (
      text.includes('what do you see') ||
      text.includes('describe this') ||
      text.includes('describe my surroundings') ||
      text.includes('describe the scene') ||
      text.includes('what is in front of me') ||
      text.includes("what's in front of me") ||
      text.includes('what is ahead') ||
      text.includes("what's ahead") ||
      text.includes('look around') ||
      text.includes('what is here')
    ) {
      return { intent: 'SCENE_DESCRIPTION', query: rawCommand, mode: 'standard' };
    }

    // 7. Default Query
    return { intent: 'IMAGE_ANALYSIS', query: rawCommand, mode: 'standard' };
  }

  /**
   * Executes Vision Analysis triggered by Voice Command
   */
  async function onVoiceCommandRecognized(commandText) {
    if (!commandText || !commandText.trim()) {
      handleVoiceError("I didn't hear that. Please try again.");
      return;
    }

    showVoiceFeedback('Command Heard', `"${commandText}"`);
    if (spokenSummary) {
      spokenSummary.textContent = `Analyzing scene for: "${commandText}"...`;
    }
    if (resultsSection) {
      resultsSection.classList.remove('hidden');
    }

    const parsed = parseVoiceCommand(commandText);
    console.log(`[Voice Router] Intent: ${parsed.intent} | Mode: ${parsed.mode} | Target: ${parsed.targetObject || 'None'}`);

    if (parsed.intent === 'DISABLE_ZEROTAP') {
      isZeroTapActive = false;
      if (zeroTapToggle) zeroTapToggle.checked = false;
      speak('Manual mode enabled. Tap any button to interact.');
      return;
    }

    if (parsed.intent === 'ENABLE_ZEROTAP') {
      isZeroTapActive = true;
      if (zeroTapToggle) zeroTapToggle.checked = true;
      speak('Zero-tap hands-free mode enabled. I am listening.');
      return;
    }

    if (parsed.intent === 'SYSTEM_REPEAT') {
      speak(lastResultText || 'No recent scene description to repeat.');
      return;
    }

    if (parsed.intent === 'STOP_GUIDANCE') {
      stopContinuousGuidance();
      cancelTargetSearch();
      showVoiceFeedback('Guidance Stopped', 'Continuous guidance stopped.');
      speak('Guidance stopped. Ready for next command.');
      return;
    }

    if (parsed.intent === 'SYSTEM_CANCEL') {
      cancelTargetSearch();
      if (isContinuousGuidanceActive) stopContinuousGuidance();
      speak('Cancelled. I am listening.');
      return;
    }

    if (parsed.intent === 'START_GUIDANCE') {
      startContinuousGuidance();
      return;
    }

    if (parsed.intent === 'TARGET_FIND') {
      setTargetSearchMode(parsed.targetObject, parsed.query);
      return;
    }

    if (parsed.intent === 'TEXT_READING') {
      showVoiceFeedback('Reading Text', 'Scanning for visible text in view...');
      await executeAnalysis({
        query: parsed.query || 'Read all visible text',
        mode: 'text_reading'
      });
      return;
    }

    // Single query execution
    showVoiceFeedback('Analyzing Scene', parsed.query ? `Analyzing: "${parsed.query}"` : 'Analyzing visible environment...');
    await executeAnalysis({
      query: parsed.query,
      mode: parsed.mode
    });
  }

  /**
   * Target Search Mode Handler
   */
  function setTargetSearchMode(targetName, originalQuery) {
    activeSearchTarget = targetName;
    activeMode = 'find_target';

    if (targetSearchBanner) {
      targetSearchTitle.textContent = `Searching: ${targetName}`;
      targetSearchStatus.textContent = 'Scanning scene... Point camera around.';
      targetSearchBanner.classList.remove('hidden');
    }

    showVoiceFeedback(`Finding ${targetName}`, `Searching for ${targetName} in camera view...`);
    executeAnalysis({
      query: originalQuery || `Find ${targetName}`,
      mode: 'find_target',
      targetObject: targetName
    });
  }

  function cancelTargetSearch() {
    activeSearchTarget = null;
    activeMode = isContinuousGuidanceActive ? 'continuous_guidance' : 'standard';
    if (targetSearchBanner) {
      targetSearchBanner.classList.add('hidden');
    }
    clearDirectionalHUD();
  }

  /**
   * Continuous Hands-Free Guidance Loop
   */
  function startContinuousGuidance() {
    if (isContinuousGuidanceActive) return;

    isContinuousGuidanceActive = true;
    activeMode = 'continuous_guidance';

    if (continuousGuidanceBtn) {
      continuousGuidanceBtn.classList.add('active');
      guidanceBtnText.textContent = 'Stop Guidance';
      guidanceIcon.textContent = '⏹️';
    }

    if (continuousModeBadge) {
      continuousModeBadge.classList.remove('hidden');
    }

    speak('Starting continuous guidance.');
    updateStatus('Continuous Guidance Active', 'ready');

    // Run first scan immediately, then queue loop
    runContinuousGuidanceStep();
  }

  function stopContinuousGuidance() {
    isContinuousGuidanceActive = false;
    activeMode = activeSearchTarget ? 'find_target' : 'standard';

    if (continuousTimer) {
      clearTimeout(continuousTimer);
      continuousTimer = null;
    }

    if (continuousGuidanceBtn) {
      continuousGuidanceBtn.classList.remove('active');
      guidanceBtnText.textContent = 'Start Guidance';
      guidanceIcon.textContent = '🧭';
    }

    if (continuousModeBadge) {
      continuousModeBadge.classList.add('hidden');
    }

    clearDirectionalHUD();
    updateStatus('Ready', 'ready');
  }

  async function runContinuousGuidanceStep() {
    if (!isContinuousGuidanceActive) return;

    if (!isAnalyzing) {
      await executeAnalysis({
        query: activeSearchTarget ? `Locate ${activeSearchTarget}` : 'Continuous guidance scan',
        mode: activeSearchTarget ? 'find_target' : 'continuous_guidance',
        targetObject: activeSearchTarget,
        isContinuous: true
      });
    }

    if (isContinuousGuidanceActive) {
      continuousTimer = setTimeout(runContinuousGuidanceStep, 1200);
    }
  }

  /**
   * Request and initialize device camera stream with progressive fallbacks
   */
  async function initCamera(facingMode = 'environment') {
    updateStatus('Connecting Camera...', 'busy');
    hideError();

    if (currentStream) {
      currentStream.getTracks().forEach((track) => track.stop());
      currentStream = null;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showError(
        'Camera Not Supported',
        'Your browser does not support camera access. Please use Chrome, Safari, or Edge over HTTPS or localhost.'
      );
      showPlaceholder('Camera API unavailable in this browser.');
      return;
    }

    const constraintOptions = [
      // 1. Ideal constraints with resolution
      {
        audio: false,
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      },
      // 2. Ideal facingMode only
      {
        audio: false,
        video: {
          facingMode: { ideal: facingMode },
        },
      },
      // 3. Basic video fallback
      {
        audio: false,
        video: true,
      },
    ];

    let stream = null;
    let lastError = null;

    for (const constraints of constraintOptions) {
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        if (stream) break;
      } catch (err) {
        lastError = err;
        console.warn('Camera constraint failed, trying fallback...', err);
      }
    }

    if (!stream) {
      console.error('Camera initialization error:', lastError);
      handleCameraError(lastError || new Error('Could not access camera'));
      return;
    }

    try {
      currentStream = stream;
      currentFacingMode = facingMode;

      video.onloadedmetadata = () => {
        video.play().catch((e) => console.warn('Autoplay error:', e));
        hidePlaceholder();
        if (!isContinuousGuidanceActive) {
          setAppState('READY', '● READY');
        }
        if (isZeroTapActive && !isContinuousGuidanceActive) {
          if (!hasGreeted) {
            triggerStartupGreeting();
          } else if (!isListening && !isAnalyzing && !isSpeaking) {
            scheduleZeroTapReArm(800);
          }
        }
      };

      video.onloadeddata = () => {
        hidePlaceholder();
        if (isZeroTapActive && !isContinuousGuidanceActive && !isListening && !isAnalyzing && !isSpeaking) {
          if (!hasGreeted) {
            triggerStartupGreeting();
          } else {
            scheduleZeroTapReArm(800);
          }
        }
      };

      video.srcObject = stream;
      await video.play().catch(() => {});
      hidePlaceholder();
      if (!isContinuousGuidanceActive) {
        setAppState('READY', '● READY');
      }
      if (isZeroTapActive && !isContinuousGuidanceActive && !isListening && !isAnalyzing && !isSpeaking) {
        if (!hasGreeted) {
          triggerStartupGreeting();
        } else {
          scheduleZeroTapReArm(800);
        }
      }
    } catch (playErr) {
      console.warn('Video play error:', playErr);
      hidePlaceholder();
    }
  }

  function handleCameraError(err) {
    let title = 'Camera Access Issue';
    let msg = err.message || 'Could not access device camera.';

    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      title = 'Camera Permission Denied';
      msg = 'Please allow camera access in your browser settings to use Gemini Visual Lens.';
    } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
      title = 'Camera Not Found';
      msg = 'No camera hardware detected on this device.';
    }

    showError(title, msg);
    showPlaceholder(msg);
    setAppState('READY', 'Camera Inactive');
    speak("I can't access the camera.");
  }

  function switchCamera() {
    const nextMode = currentFacingMode === 'environment' ? 'user' : 'environment';
    initCamera(nextMode);
  }

  /**
   * Frame Capture helper
   */
  function captureFrame() {
    if (!video || !video.videoWidth || !video.videoHeight) {
      throw new Error('Camera is not active or ready to capture.');
    }

    const maxDim = 800;
    let w = video.videoWidth;
    let h = video.videoHeight;

    if (w > maxDim || h > maxDim) {
      if (w > h) {
        h = Math.round((h * maxDim) / w);
        w = maxDim;
      } else {
        w = Math.round((w * maxDim) / h);
        h = maxDim;
      }
    }

    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, w, h);

    return canvas.toDataURL('image/jpeg', 0.75);
  }

  /**
   * Core Analysis Execution
   */
  async function executeAnalysis(options = {}) {
    if (isAnalyzing) return;

    const query = typeof options === 'string' ? options : (options.query || null);
    const mode = options.mode || activeMode;
    const targetObject = options.targetObject || activeSearchTarget;
    const isContinuous = !!options.isContinuous;

    // If stream is active but video metadata is still loading, wait a moment for dimensions
    if (currentStream && video && (!video.videoWidth || !video.videoHeight)) {
      await new Promise((resolve) => {
        let elapsed = 0;
        const checkInterval = setInterval(() => {
          elapsed += 100;
          if ((video.videoWidth && video.videoHeight) || elapsed >= 1200) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 100);
      });
    }

    // Check if camera stream is active; if not, attempt initialization
    if (!currentStream || !video || !video.videoWidth || !video.videoHeight) {
      if (!isContinuous) {
        showError('Camera Not Ready', 'Please grant camera access or wait for camera to start.');
      }
      return;
    }

    try {
      hideError();
      const base64Image = captureFrame();

      setAnalyzingState(true);
      setAppState('ANALYZING', isContinuous ? 'Continuous Scanning...' : '● ANALYZING');

      const payload = {
        image: base64Image,
        query: query || null,
        mode: mode,
        target_object: targetObject || null
      };

      let response;
      try {
        response = await fetch('/api/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
        if (response.status === 404) {
          response = await fetch('/analyze', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
          });
        }
      } catch (fetchErr) {
        response = await fetch('/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
      }

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || `Server responded with status ${response.status}`);
      }

      displayResults(result.data, result.processing_time_ms, isContinuous);

    } catch (err) {
      console.error('Analysis error:', err);
      if (!isContinuous) {
        showError('Analysis Notice', err.message || 'Failed to analyze camera frame.');
        setAppState('READY', '● READY');
      } else {
        setAppState('ANALYZING', 'Guidance Active (Scanning...)');
      }
      if (isZeroTapActive && !isContinuousGuidanceActive) {
        scheduleZeroTapReArm(2500);
      }
    } finally {
      setAnalyzingState(false);
    }
  }

  /**
   * Clear HUD Directional Arrows and Lock Cues
   */
  function clearDirectionalHUD() {
    if (leftGuideArrow) leftGuideArrow.classList.add('hidden');
    if (rightGuideArrow) rightGuideArrow.classList.add('hidden');
    if (targetLockedPill) targetLockedPill.classList.add('hidden');
  }

  /**
   * Update HUD Directional Overlays
   */
  function updateDirectionalHUD(directionText, targetFound, objects) {
    clearDirectionalHUD();
    if (!directionText) return;

    const dLower = directionText.toLowerCase();

    if (dLower.includes('left') || dLower.includes('9 o\'clock') || dLower.includes('10 o\'clock')) {
      if (leftGuideArrow) leftGuideArrow.classList.remove('hidden');
      playSpatialAudioBeacon('left', 'near');
    } else if (dLower.includes('right') || dLower.includes('2 o\'clock') || dLower.includes('3 o\'clock')) {
      if (rightGuideArrow) rightGuideArrow.classList.remove('hidden');
      playSpatialAudioBeacon('right', 'near');
    } else if (dLower.includes('center') || dLower.includes('forward') || dLower.includes('reach') || targetFound) {
      if (targetLockedPill) targetLockedPill.classList.remove('hidden');
      playSpatialAudioBeacon('center', 'very_close');
      triggerHapticPulse('center');
    }
  }

  /**
   * Renders the structured Gemini response onto the UI (Phase 3)
   */
  function displayResults(data, processingTimeMs, isContinuous = false) {
    if (!data) return;

    if (resultsSection) {
      resultsSection.classList.remove('hidden');
    }
    if (!isContinuous && resultsSection) {
      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // 1. Urgent Hazard Alert
    if (data.hazard_alert) {
      if (hazardBanner) {
        hazardTitle.textContent = 'Hazard Alert';
        hazardMessage.textContent = data.hazard_alert;
        hazardBanner.classList.remove('hidden');
      }
      playHazardChime();
      triggerHapticPulse('hazard');
    } else {
      if (hazardBanner) hazardBanner.classList.add('hidden');
    }

    // 2. Target Search Status update
    if (activeSearchTarget) {
      if (data.target_found) {
        targetSearchStatus.textContent = `Found! ${data.guidance_direction || 'In view'}`;
        playTargetLocatedChime();
      } else {
        targetSearchStatus.textContent = data.guidance_direction || `Searching for ${activeSearchTarget}...`;
      }
    }

    // 3. Spatial Guidance Card & Path Status
    const guidanceText = data.guidance || data.guidance_direction;
    if (guidanceText || data.path_status) {
      if (guidanceCard) {
        guidanceCard.classList.remove('hidden');
        guidanceDirectionText.textContent = guidanceText || (data.path_status === 'clear' ? 'Path appears clear ahead.' : 'Caution in path ahead.');
        
        // Update or inject Path Status Badge
        let pathStatusBadge = document.getElementById('pathStatusBadge');
        if (!pathStatusBadge) {
          pathStatusBadge = document.createElement('span');
          pathStatusBadge.id = 'pathStatusBadge';
          const headerEl = guidanceCard.querySelector('.guidance-content');
          if (headerEl) headerEl.insertBefore(pathStatusBadge, guidanceDirectionText);
        }
        
        const pathSt = (data.path_status || 'clear').toLowerCase().replace(' ', '_');
        pathStatusBadge.className = `badge badge-path-${pathSt}`;
        pathStatusBadge.textContent = `PATH: ${pathSt.replace('_', ' ').toUpperCase()}`;
      }
      updateDirectionalHUD(guidanceText, data.target_found, data.objects);
    } else {
      if (guidanceCard) guidanceCard.classList.add('hidden');
      clearDirectionalHUD();
    }

    // 4. Spoken Summary Text (Written AI Output)
    const sceneSummaryText = data.scene_summary || data.summary || 'Visual scene analyzed.';
    spokenSummary.textContent = sceneSummaryText;
    lastResultText = sceneSummaryText;

    // 5. Processing Latency Badge
    if (processingTimeBadge && processingTimeMs) {
      processingTimeBadge.textContent = `${processingTimeMs} ms`;
    }

    // 6. Uncertainty Banner
    if (data.uncertainty) {
      uncertaintyCard.classList.remove('hidden');
      uncertaintyText.textContent = data.uncertainty;
    } else {
      uncertaintyCard.classList.add('hidden');
    }

    // 7. Detected Objects Grid with Clock Badges & Obstacle Indicators
    objectsList.innerHTML = '';
    const objects = data.objects || [];

    if (objects.length === 0) {
      const emptyNotice = document.createElement('p');
      emptyNotice.className = 'text-muted';
      emptyNotice.style.fontSize = '0.95rem';
      emptyNotice.style.padding = '0.75rem 0';
      emptyNotice.textContent = 'No significant objects or obstacles detected in the visible area.';
      objectsList.appendChild(emptyNotice);
    } else {
      objects.forEach((obj) => {
        const item = createObjectElement(obj);
        objectsList.appendChild(item);
      });
    }

    // 8. Spoken Feedback Dispatch (Automatic TTS)
    if ((autoSpeakToggle && autoSpeakToggle.checked) || isZeroTapActive) {
      let textToSpeak = data.voice_response || sceneSummaryText;

      // Priority hazard preamble
      if (data.hazard_alert && !textToSpeak.toLowerCase().includes('warning')) {
        textToSpeak = `Warning: ${data.hazard_alert}. ${textToSpeak}`;
      }

      // Continuous mode anti-chatter filter & smart debounce
      if (isContinuous) {
        const now = Date.now();
        const isHazard = Boolean(data.hazard_alert);
        const isTargetFound = Boolean(data.target_found);
        const textChanged = !lastGuidanceText || lastGuidanceText !== textToSpeak;
        const cooldownElapsed = (now - lastGuidanceSpeechTime) > 3500;

        if (isHazard || isTargetFound || (textChanged && cooldownElapsed)) {
          lastGuidanceText = textToSpeak;
          lastGuidanceSpeechTime = now;
          lastSpokenSummary = textToSpeak;
          speak(textToSpeak);
        }
      } else {
        lastSpokenSummary = textToSpeak;
        speak(textToSpeak);
      }
    } else {
      if (!isContinuousGuidanceActive) {
        setAppState('READY');
      }
    }
  }

  /**
   * Helper to map object names to intuitive visual icons
   */
  function getObjectIcon(name) {
    const n = (name || '').toLowerCase();
    if (n.includes('chair') || n.includes('seat') || n.includes('sofa') || n.includes('couch')) return '🪑';
    if (n.includes('table') || n.includes('desk')) return '🪵';
    if (n.includes('bottle') || n.includes('cup') || n.includes('mug') || n.includes('glass')) return '🧴';
    if (n.includes('person') || n.includes('human') || n.includes('man') || n.includes('woman')) return '👤';
    if (n.includes('bag') || n.includes('backpack') || n.includes('purse')) return '🎒';
    if (n.includes('laptop') || n.includes('computer') || n.includes('screen') || n.includes('monitor')) return '💻';
    if (n.includes('phone') || n.includes('cell')) return '📱';
    if (n.includes('key')) return '🔑';
    if (n.includes('door')) return '🚪';
    if (n.includes('wall')) return '🧱';
    if (n.includes('stair') || n.includes('step')) return '🪜';
    if (n.includes('book')) return '📖';
    if (n.includes('car') || n.includes('vehicle') || n.includes('bike')) return '🚗';
    return '📦';
  }

  /**
   * Creates DOM element for an individual detected object with Clock Directions & Obstacle Details
   */
  function createObjectElement(obj) {
    const card = document.createElement('div');
    card.className = `object-item ${obj.is_obstacle ? 'object-item-obstacle' : ''}`;

    const header = document.createElement('div');
    header.className = 'object-item-header';

    const nameEl = document.createElement('span');
    nameEl.className = 'object-name';
    const icon = getObjectIcon(obj.name);
    nameEl.textContent = `${icon} ${obj.name.charAt(0).toUpperCase() + obj.name.slice(1)}`;

    const confEl = document.createElement('span');
    confEl.className = 'object-confidence';
    confEl.textContent = `${Math.round((obj.confidence || 0.9) * 100)}%`;

    header.appendChild(nameEl);
    header.appendChild(confEl);
    card.appendChild(header);

    const tagsContainer = document.createElement('div');
    tagsContainer.className = 'object-tags';

    // Clock direction badge (e.g. 12 o'clock, 2 o'clock)
    if (obj.clock_position) {
      const clockTag = document.createElement('span');
      clockTag.className = 'tag tag-clock';
      clockTag.textContent = `🕒 ${obj.clock_position.toUpperCase()}`;
      tagsContainer.appendChild(clockTag);
    }

    // Direction / Horizontal Position tag
    const dirPhrase = obj.direction || (obj.horizontal_position || obj.position || 'center').replace('_', ' ');
    const posTag = document.createElement('span');
    posTag.className = `tag tag-pos-${(obj.horizontal_position || 'center').replace(' ', '_')}`;
    let posIcon = '⏺️';
    if (dirPhrase.includes('left')) posIcon = '⬅️';
    else if (dirPhrase.includes('right')) posIcon = '➡️';
    else if (dirPhrase.includes('ahead') || dirPhrase.includes('center')) posIcon = '⬆️';
    posTag.textContent = `${posIcon} ${dirPhrase.toUpperCase()}`;
    tagsContainer.appendChild(posTag);

    // Approximate Metric Distance badge (e.g. ~1.5 m or ~2 m)
    const distText = obj.distance_display || obj.distance || '~1.5 meters';
    const metricTag = document.createElement('span');
    metricTag.className = 'tag tag-dist-metric';
    metricTag.textContent = `📏 ${distText.toUpperCase()}`;
    tagsContainer.appendChild(metricTag);

    // Obstacle badge if applicable
    if (obj.is_obstacle) {
      const obsTag = document.createElement('span');
      obsTag.className = 'tag tag-obstacle';
      obsTag.textContent = '⚠️ OBSTACLE';
      tagsContainer.appendChild(obsTag);
    }

    // Surface / Landmark context tag
    if (obj.landmark) {
      const landmarkTag = document.createElement('span');
      landmarkTag.className = 'tag tag-landmark';
      landmarkTag.textContent = `📍 ${obj.landmark.toUpperCase()}`;
      tagsContainer.appendChild(landmarkTag);
    }

    card.appendChild(tagsContainer);

    // Individual spatial instruction sentence if available
    if (obj.spatial_instruction) {
      const instrEl = document.createElement('p');
      instrEl.className = 'object-spatial-instruction';
      instrEl.textContent = obj.spatial_instruction;
      card.appendChild(instrEl);
    }

    return card;
  }

  /**
   * Helper to unlock Web Speech Synthesis and Web Audio on any user gesture
   */
  function unlockAudioAndTTS() {
    getAudioContext();
    if (synth) {
      try {
        if (synth.paused) synth.resume();
      } catch (e) {}
    }
  }

  let speakWatchdogTimer = null;

  /**
   * Text-to-Speech using Android native TTS (if in APK), browser SpeechSynthesis, or server pyttsx3 fallback
   */
  function speak(text) {
    if (!text) {
      onSpeechFinished();
      return;
    }

    // Clean text for speech: remove markdown syntax and special chars
    const cleanSpeechText = text
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/`/g, '')
      .replace(/#/g, '')
      .replace(/\[.*?\]\(.*?\)/g, '')
      .replace(/~/g, 'approximately ')
      .trim();

    if (!cleanSpeechText) {
      onSpeechFinished();
      return;
    }

    // 1. Stop any currently active speech first
    stopSpeech();

    // 2. Setup universal safety watchdog timer for both Android & Web TTS
    const wordCount = cleanSpeechText.split(/\s+/).length;
    const maxExpectedMs = Math.min(15000, Math.max(3000, wordCount * 380 + 2000));
    speakWatchdogTimer = setTimeout(() => {
      if (isSpeaking) {
        console.warn('[TTS Watchdog] Speech timed out, safely concluding speaking state');
        onSpeechFinished();
      }
    }, maxExpectedMs);

    isSpeaking = true;
    setAppState('SPEAKING');
    if (speakBtn) speakBtn.classList.add('hidden');
    if (stopSpeakBtn) stopSpeakBtn.classList.remove('hidden');

    // 3. Android Native TTS Bridge (in Android APK)
    if (typeof AndroidTTS !== 'undefined' && AndroidTTS.speak) {
      try {
        AndroidTTS.speak(cleanSpeechText);
        return;
      } catch (err) {
        console.warn('AndroidTTS error, falling back to browser speech:', err);
      }
    }

    // 4. Browser Web Speech Synthesis API
    if (synth) {
      try {
        if (synth.paused) {
          synth.resume();
        }

        const utterance = new SpeechSynthesisUtterance(cleanSpeechText);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        utterance.lang = 'en-US';

        if (!cachedVoices.length) {
          try {
            cachedVoices = synth.getVoices() || [];
          } catch (_) {}
        }

        const selectedVoice = cachedVoices.find(
          (v) => v.lang && v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Enhanced') || v.name.includes('Samantha') || v.name.includes('David'))
        ) || cachedVoices.find((v) => v.lang && v.lang.startsWith('en'));

        if (selectedVoice) {
          utterance.voice = selectedVoice;
        }

        utterance.onstart = () => {
          isSpeaking = true;
          setAppState('SPEAKING');
          if (speakBtn) speakBtn.classList.add('hidden');
          if (stopSpeakBtn) stopSpeakBtn.classList.remove('hidden');
        };

        utterance.onend = () => {
          onSpeechFinished();
        };

        utterance.onerror = (e) => {
          onSpeechFinished();
          if (e && e.error && e.error !== 'interrupted' && e.error !== 'canceled') {
            console.warn('SpeechSynthesis error, falling back to server TTS:', e.error);
            fallbackServerSpeak(cleanSpeechText);
          }
        };

        // Keep window-level reference to prevent GC disposal mid-speech in Chromium
        window._activeUtterance = utterance;
        currentUtterance = utterance;
        synth.speak(utterance);
        return;
      } catch (e) {
        console.warn('Browser speech synthesis error, trying server TTS:', e);
      }
    }

    // 5. Server-side TTS Fallback (/api/speak or /speak)
    fallbackServerSpeak(cleanSpeechText);
  }

  function fallbackServerSpeak(textToSpeak) {
    try {
      fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: textToSpeak }),
      }).catch(() => {
        fetch('/speak', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: textToSpeak }),
        }).catch((e) => console.warn('Server TTS dispatch error:', e));
      });
    } catch (err) {
      console.warn('Could not dispatch server TTS:', err);
    }
  }

  function stopSpeech() {
    isSpeaking = false;
    if (speakWatchdogTimer) {
      clearTimeout(speakWatchdogTimer);
      speakWatchdogTimer = null;
    }
    if (typeof AndroidTTS !== 'undefined' && AndroidTTS.stop) {
      try { AndroidTTS.stop(); } catch (_) {}
    }
    if (synth) {
      try {
        if (synth.speaking || synth.pending) {
          synth.cancel();
        }
      } catch (_) {}
    }
    if (speakBtn) speakBtn.classList.remove('hidden');
    if (stopSpeakBtn) stopSpeakBtn.classList.add('hidden');
    window._activeUtterance = null;
    currentUtterance = null;
  }

  function setAnalyzingState(busy) {
    isAnalyzing = busy;
    captureBtn.disabled = busy;
    if (sendQueryBtn) sendQueryBtn.disabled = busy;
    if (busy) {
      scanLine.classList.remove('hidden');
    } else {
      scanLine.classList.add('hidden');
    }
  }

  function showError(title, message) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorBanner.classList.remove('hidden');
  }

  function hideError() {
    errorBanner.classList.add('hidden');
  }

  function showPlaceholder(msg) {
    cameraStatusText.textContent = msg;
    cameraPlaceholder.classList.remove('hidden');
  }

  function hidePlaceholder() {
    cameraPlaceholder.classList.add('hidden');
  }

  /**
   * Handle text query submission
   */
  function handleQuerySubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (!queryInput) return;
    const text = queryInput.value.trim();
    if (!text) return;
    onVoiceCommandRecognized(text);
  }

  // Event Listeners
  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      unlockAudioAndTTS();
      startVoiceListening();
    });
  }

  if (queryForm) {
    queryForm.addEventListener('submit', handleQuerySubmit);
  }

  if (sendQueryBtn) {
    sendQueryBtn.addEventListener('click', handleQuerySubmit);
  }

  // Quick Action Suggestion Chips
  if (quickChips) {
    quickChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        unlockAudioAndTTS();
        const cmd = chip.getAttribute('data-cmd');
        if (cmd) {
          if (queryInput) queryInput.value = cmd;
          onVoiceCommandRecognized(cmd);
        }
      });
    });
  }

  if (continuousGuidanceBtn) {
    continuousGuidanceBtn.addEventListener('click', () => {
      unlockAudioAndTTS();
      if (isContinuousGuidanceActive) {
        stopContinuousGuidance();
      } else {
        startContinuousGuidance();
      }
    });
  }

  if (cancelTargetBtn) {
    cancelTargetBtn.addEventListener('click', cancelTargetSearch);
  }

  if (captureBtn) {
    captureBtn.addEventListener('click', () => {
      unlockAudioAndTTS();
      executeAnalysis({ query: null, mode: 'standard' });
    });
  }

  if (zeroTapToggle) {
    zeroTapToggle.addEventListener('change', (e) => {
      isZeroTapActive = e.target.checked;
      unlockAudioAndTTS();
      if (isZeroTapActive) {
        showVoiceFeedback('Zero-Tap Mode Active', 'Hands-free voice loop enabled. Speak any command.');
        scheduleZeroTapReArm(400);
      } else {
        showVoiceFeedback('Manual Mode Active', 'You can tap any button to interact.');
        if (isListening) {
          stopVoiceListening();
        }
      }
    });
  }

  if (switchCameraBtn) {
    switchCameraBtn.addEventListener('click', switchCamera);
  }

  if (grantCameraBtn) {
    grantCameraBtn.addEventListener('click', () => initCamera(currentFacingMode));
  }

  if (dismissErrorBtn) {
    dismissErrorBtn.addEventListener('click', hideError);
  }

  if (speakBtn) {
    speakBtn.addEventListener('click', () => {
      unlockAudioAndTTS();
      if (lastResultText) speak(lastResultText);
    });
  }

  if (stopSpeakBtn) {
    stopSpeakBtn.addEventListener('click', stopSpeech);
  }

  // Global user gesture unlock for audio & speech synthesis
  document.addEventListener('click', () => {
    unlockAudioAndTTS();
    if (!hasGreeted && isZeroTapActive && currentStream) {
      triggerStartupGreeting();
    }
  }, { passive: true });

  document.addEventListener('touchstart', () => {
    unlockAudioAndTTS();
    if (!hasGreeted && isZeroTapActive && currentStream) {
      triggerStartupGreeting();
    }
  }, { passive: true });

  // Initialize speech recognition & camera on page load
  window.addEventListener('DOMContentLoaded', () => {
    initSpeechEngine();
    initCamera('environment');
    showVoiceFeedback("Vision Lens Ready", "Point camera and tap Capture or use voice commands.");
  });
})();
