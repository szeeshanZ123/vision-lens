
"""FastAPI Application for Gemini Visual Lens Prototype.

Coordinates camera frame reception, OpenCV/Pillow validation, Gemini AI spatial analysis,
and structured accessible responses.
"""

import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Load environment configuration
load_dotenv()

from models.vision_result import AnalyzeRequest, AnalyzeResponse, VisionResult
from services.vision_service import VisionService, VisionProcessingError
from services.gemini_service import GeminiService, GeminiConfigurationError, GeminiAnalysisError
from services.speech_service import SpeechService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("visual_lens_app")

# Discover project directories cleanly
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = BASE_DIR.parent / "static"

TEMPLATES_DIR = BASE_DIR / "templates"
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = BASE_DIR.parent / "templates"

PUBLIC_DIR = BASE_DIR / "public"
if not PUBLIC_DIR.exists():
    PUBLIC_DIR = BASE_DIR.parent / "public"

gemini_service = GeminiService()
vision_service = VisionService()
speech_service = SpeechService()

# Create FastAPI app
app = FastAPI(
    title="Gemini Visual Lens",
    description="Mobile-first visual assistance prototype for spatial awareness and object detection.",
    version="1.2.0"
)

# Enable secure CORS for web browser and mobile APK clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Injects standard defensive HTTP security headers into all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self)"
    return response


# Mount static and public assets and templates
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    """Explicit static file fallback handler with directory traversal protection."""
    # Resolve candidate static directories safely
    valid_roots = [STATIC_DIR.resolve()]
    if (BASE_DIR.parent / "static").exists():
        valid_roots.append((BASE_DIR.parent / "static").resolve())

    for root in valid_roots:
        try:
            target = (root / file_path).resolve()
            # Ensure resolved path is strictly within the allowed static directory
            if target.is_relative_to(root) and target.exists() and target.is_file():
                media_type = "text/css" if file_path.endswith(".css") else "application/javascript" if file_path.endswith(".js") else None
                return FileResponse(str(target), media_type=media_type)
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="Static asset not found")


@app.get("/vision-lens.apk")
@app.get("/public/vision-lens.apk")
@app.get("/static/vision-lens.apk")
async def download_apk():
    """Serves the latest Vision Lens Android APK package."""
    candidates = [
        PUBLIC_DIR / "vision-lens.apk",
        STATIC_DIR / "vision-lens.apk",
        BASE_DIR / "public" / "vision-lens.apk",
        BASE_DIR.parent / "public" / "vision-lens.apk",
        BASE_DIR / "static" / "vision-lens.apk",
        BASE_DIR.parent / "static" / "vision-lens.apk",
    ]
    for apk_path in candidates:
        if apk_path.exists() and apk_path.is_file():
            return FileResponse(
                path=str(apk_path),
                filename="vision-lens.apk",
                media_type="application/vnd.android.package-archive",
                headers={
                    "Content-Disposition": 'attachment; filename="vision-lens.apk"',
                    "Content-Type": "application/vnd.android.package-archive",
                    "Cache-Control": "public, max-age=3600",
                }
            )
    raise HTTPException(status_code=404, detail="APK package not found on server.")


@app.get("/download", response_class=HTMLResponse)
@app.get("/api/download", response_class=HTMLResponse)
async def download_view(request: Request):
    """Serves the professional Vision Lens Download & QR Code portal."""
    return templates.TemplateResponse(
        request=request,
        name="download.html"
    )


@app.get("/", response_class=HTMLResponse)
@app.get("/index", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/index", response_class=HTMLResponse)
async def index_view(request: Request):
    """Serves the main mobile-friendly camera interface."""
    api_configured = gemini_service.is_configured()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"api_configured": api_configured}
    )


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check and API key configuration status."""
    return {
        "status": "online",
        "gemini_configured": gemini_service.is_configured(),
        "model": gemini_service.DEFAULT_MODEL,
        "message": "Gemini Visual Lens backend is running."
    }


@app.post("/analyze", response_model=AnalyzeResponse)
@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_frame(payload: AnalyzeRequest):
    """
    Receives captured camera frame from mobile browser, validates via OpenCV/Pillow,
    queries Gemini Vision, and returns structured spatial JSON.
    """
    start_time = time.time()
    
    # 1. Check API Key configuration
    if not gemini_service.is_configured():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=AnalyzeResponse(
                success=False,
                error="Vision AI service is unavailable. Please ensure GEMINI_API_KEY is configured in the server deployment environment."
            ).model_dump()
        )

    # 2. Decode and validate image payload
    try:
        pil_image = vision_service.decode_base64_image(payload.image)
        optimized_image, _ = vision_service.optimize_image_for_gemini(pil_image)
    except VisionProcessingError as v_err:
        logger.warning(f"Image processing error: {v_err}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=AnalyzeResponse(
                success=False,
                error=f"Invalid image: {str(v_err)}"
            ).model_dump()
        )
    except Exception as exc:
        logger.error(f"Unexpected image decode error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AnalyzeResponse(
                success=False,
                error="Could not decode the camera frame."
            ).model_dump()
        )

    # 3. Call Gemini Vision AI Service
    try:
        result: VisionResult = gemini_service.analyze_scene(
            optimized_image,
            query=payload.query,
            mode=payload.mode,
            target_object=payload.target_object
        )
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"Analysis complete in {duration_ms}ms. Detected {len(result.objects)} objects.")
        
        return AnalyzeResponse(
            success=True,
            data=result,
            processing_time_ms=duration_ms
        )

    except GeminiConfigurationError as cfg_err:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AnalyzeResponse(
                success=False,
                error=str(cfg_err)
            ).model_dump()
        )
    except GeminiAnalysisError as a_err:
        logger.error(f"Gemini API failure: {a_err}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=AnalyzeResponse(
                success=False,
                error=str(a_err)
            ).model_dump()
        )
    except Exception as gen_err:
        logger.error(f"Unexpected analysis error: {gen_err}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=AnalyzeResponse(
                success=False,
                error="An unexpected error occurred during visual analysis. Please try again."
            ).model_dump()
        )


@app.post("/speak")
@app.post("/api/speak")
async def speak_text(payload: dict):
    """Optional server-side speech synthesis trigger."""
    text = payload.get("text", "")
    if text:
        dispatched = speech_service.speak(text)
        return {"success": dispatched, "text": text}
    return {"success": False, "error": "No text provided"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"Starting Gemini Visual Lens server at http://localhost:{port}")
    print(f"To test on phone on same Wi-Fi, open: http://<YOUR_LOCAL_IP>:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=True)


