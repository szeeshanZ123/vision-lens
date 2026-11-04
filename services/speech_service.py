"""Speech Service providing Python-side Text-To-Speech (pyttsx3) integration.

Provides a fallback audio engine on the server alongside client-side browser SpeechSynthesis.
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger("speech_service")


class SpeechService:
    """Manages Python-side Text-to-Speech synthesis with lazy initialization."""

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._initialized = False

    def _ensure_engine(self):
        if self._initialized:
            return self._engine
        with self._lock:
            if not self._initialized:
                try:
                    import pyttsx3
                    self._engine = pyttsx3.init()
                    self._engine.setProperty("rate", 160)
                    self._engine.setProperty("volume", 1.0)
                    logger.info("Python pyttsx3 TTS engine initialized successfully.")
                except Exception as e:
                    logger.warning(
                        f"Python pyttsx3 TTS could not initialize (client browser SpeechSynthesis will be used): {e}"
                    )
                    self._engine = None
                finally:
                    self._initialized = True
        return self._engine

    def speak(self, text: str, block: bool = False) -> bool:
        """
        Speaks text through the local system audio output if available.
        
        Args:
            text: Text to speak aloud
            block: If True, blocks until speech finishes. If False, runs in background thread.
            
        Returns:
            bool indicating if speech command was dispatched
        """
        engine = self._ensure_engine()
        if not text or not engine:
            return False

        def _run():
            with self._lock:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as err:
                    logger.error(f"Error during pyttsx3 speech synthesis: {err}")

        if block:
            _run()
        else:
            thread = threading.Thread(target=_run, daemon=True)
            thread.start()

        return True
