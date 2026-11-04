"""Speech Service providing Python-side Text-To-Speech (pyttsx3) integration.

Provides a fallback audio engine on the server alongside client-side browser SpeechSynthesis.
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger("speech_service")

class SpeechService:
    """Manages Python-side Text-to-Speech synthesis."""

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            # Set speech rate and volume for clear accessibility
            self._engine.setProperty("rate", 160)
            self._engine.setProperty("volume", 1.0)
            logger.info("Python pyttsx3 TTS engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Python pyttsx3 TTS could not initialize (client browser SpeechSynthesis will be used): {e}")
            self._engine = None

    def speak(self, text: str, block: bool = False) -> bool:
        """
        Speaks text through the local system audio output if available.
        
        Args:
            text: Text to speak aloud
            block: If True, blocks until speech finishes. If False, runs in background thread.
            
        Returns:
            bool indicating if speech command was dispatched
        """
        if not text or not self._engine:
            return False

        def _run():
            with self._lock:
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception as err:
                    logger.error(f"Error during pyttsx3 speech synthesis: {err}")

        if block:
            _run()
        else:
            thread = threading.Thread(target=_run, daemon=True)
            thread.start()

        return True
