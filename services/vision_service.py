"""Vision and Image Processing Service using Pillow and NumPy (with optional OpenCV).

Handles decoding base64 image streams from the browser, validating integrity,
resizing for optimal Gemini API transmission latency, and format conversions.
Serverless-ready for Vercel, AWS Lambda, Docker, and local development.
"""

import base64
import io
from typing import Tuple
import numpy as np
from PIL import Image

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class VisionProcessingError(Exception):
    """Raised when an image payload cannot be decoded or is invalid."""
    pass


class VisionService:
    """Provides image validation, decoding, resizing, and preparation for AI vision."""

    MAX_DIMENSION: int = 800
    JPEG_QUALITY: int = 75
    MAX_PAYLOAD_CHARS: int = 20 * 1024 * 1024  # 20MB max base64 string length

    @classmethod
    def decode_base64_image(cls, image_data: str) -> Image.Image:
        """
        Decodes a base64-encoded image string (with or without data URL prefix) into a PIL Image.
        
        Args:
            image_data: Base64 string from browser canvas.toDataURL()
            
        Returns:
            PIL.Image.Image in RGB mode.
            
        Raises:
            VisionProcessingError: If decoding fails or data is corrupted.
        """
        if not image_data or not isinstance(image_data, str):
            raise VisionProcessingError("Empty or invalid image payload provided.")

        if len(image_data) > cls.MAX_PAYLOAD_CHARS:
            raise VisionProcessingError("Image payload exceeds maximum allowed size.")

        try:
            # Strip data URL prefix if present (e.g., 'data:image/jpeg;base64,')
            if "," in image_data:
                header, encoded = image_data.split(",", 1)
            else:
                encoded = image_data

            image_bytes = base64.b64decode(encoded)
            if len(image_bytes) == 0:
                raise VisionProcessingError("Image payload contained zero bytes.")

            # Open with Pillow
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # Ensure in RGB color space
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")

            # Validate basic dimensions
            width, height = pil_image.size
            if width < 32 or height < 32:
                raise VisionProcessingError(f"Image dimensions ({width}x{height}) too small for visual analysis.")

            return pil_image

        except Exception as exc:
            if isinstance(exc, VisionProcessingError):
                raise
            raise VisionProcessingError(f"Failed to decode image: {str(exc)}") from exc

    @classmethod
    def optimize_image_for_gemini(cls, pil_image: Image.Image) -> Tuple[Image.Image, bytes]:
        """
        Resizes large camera frames and compresses to JPEG bytes to ensure rapid API transmission.
        
        Args:
            pil_image: Raw PIL Image from camera frame.
            
        Returns:
            Tuple of (resized PIL Image, optimized JPEG bytes)
        """
        width, height = pil_image.size
        max_dim = max(width, height)

        # Downscale if larger than MAX_DIMENSION while keeping aspect ratio
        if max_dim > cls.MAX_DIMENSION:
            scale = cls.MAX_DIMENSION / max_dim
            new_width = max(32, int(width * scale))
            new_height = max(32, int(height * scale))
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.BILINEAR)

        # Compress to JPEG in memory buffer
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=cls.JPEG_QUALITY, optimize=True)
        jpeg_bytes = buffer.getvalue()

        return pil_image, jpeg_bytes

    @classmethod
    def check_image_quality(cls, pil_image: Image.Image) -> dict:
        """
        Calculates basic metrics (blur score, average luminance) using NumPy / Pillow.
        Useful for reporting uncertainty if camera capture was dark or blurred.
        """
        try:
            # Convert to grayscale numpy array
            gray = np.array(pil_image.convert("L"), dtype=np.float64)
            mean_brightness = float(np.mean(gray))

            if OPENCV_AVAILABLE:
                laplacian_var = float(cv2.Laplacian(gray.astype(np.uint8), cv2.CV_64F).var())
            else:
                # Fast numpy discrete laplacian variance approximation
                # Kernel: [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
                if gray.shape[0] > 2 and gray.shape[1] > 2:
                    lap = (
                        gray[:-2, 1:-1]
                        + gray[2:, 1:-1]
                        + gray[1:-1, :-2]
                        + gray[1:-1, 2:]
                        - 4 * gray[1:-1, 1:-1]
                    )
                    laplacian_var = float(np.var(lap))
                else:
                    laplacian_var = 100.0

            is_blurry = laplacian_var < 40.0
            is_dark = mean_brightness < 25.0

            return {
                "blur_score": float(laplacian_var),
                "brightness": mean_brightness,
                "is_blurry": is_blurry,
                "is_dark": is_dark,
            }
        except Exception:
            return {"blur_score": 100.0, "brightness": 128.0, "is_blurry": False, "is_dark": False}

