"""Data models and schemas for Gemini Visual Lens using Pydantic."""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates [0.0 - 1.0]."""
    ymin: float = Field(0.0, ge=0.0, le=1.0, description="Top edge coordinate")
    xmin: float = Field(0.0, ge=0.0, le=1.0, description="Left edge coordinate")
    ymax: float = Field(1.0, ge=0.0, le=1.0, description="Bottom edge coordinate")
    xmax: float = Field(1.0, ge=0.0, le=1.0, description="Right edge coordinate")


class DetectedObject(BaseModel):
    """Represents a single visible object identified in the scene with spatial positioning."""
    name: str = Field(..., description="Name or label of the detected object")
    label: Optional[str] = Field(
        default=None, description="Standardized object category label"
    )
    
    # 3-Zone horizontal position (backwards-compatible)
    position: Literal["left", "center", "right"] = Field(
        default="center", description="3-zone horizontal position"
    )
    
    # 7-Zone fine-grained horizontal position
    horizontal_position: Literal[
        "far_left", "left", "slightly_left", "center", "slightly_right", "right", "far_right"
    ] = Field(
        default="center", description="Fine-grained 7-zone horizontal position"
    )
    
    direction: Optional[str] = Field(
        default=None, description="Intuitive direction phrase (e.g. 'slightly right', 'center', 'front-right')"
    )
    
    vertical_position: Literal["above", "middle", "below", "center"] = Field(
        default="middle", description="Approximate vertical position relative to eye-level"
    )
    
    # Distance classifications
    relative_distance: Literal["very_close", "near", "medium", "far", "close"] = Field(
        default="near", description="Estimated relative proximity to user"
    )
    distance_category: Literal["very_close", "close", "medium", "far"] = Field(
        default="close", description="Standardized distance tier"
    )
    
    # Approximate metric estimation (e.g. 1.5 for ~1.5m)
    approximate_distance_m: Optional[float] = Field(
        default=None, description="Estimated approximate distance in meters (explicitly approximate)"
    )
    distance_display: Optional[str] = Field(
        default=None, description="Human-readable distance string (e.g. '~1.5 meters', '~2 meters')"
    )
    distance: Optional[str] = Field(
        default=None, description="Natural language distance phrase (e.g. 'approximately 1.5 meters', 'about 2 meters ahead')"
    )
    
    # Obstacle flag
    is_obstacle: bool = Field(
        default=False, description="True if this object is an obstacle interfering with movement in the path"
    )
    
    # Bounding Box
    bounding_box: Optional[BoundingBox] = Field(
        default=None, description="Normalized bounding box coordinates"
    )
    
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    landmark: Optional[str] = Field(
        default=None, description="Nearby reference landmark or surface placement (e.g. 'on table', 'on floor')"
    )
    clock_position: Optional[str] = Field(
        default=None, description="Clock-face direction relative to user (e.g. '12 o\'clock', '1–2 o\'clock', '3 o\'clock')"
    )
    spatial_instruction: Optional[str] = Field(
        default=None, description="Individual spatial voice instruction for this object"
    )


class VisionResult(BaseModel):
    """Structured spatial analysis result returned by the backend and processed by Python."""
    summary: str = Field(
        ..., description="Complete, high-clarity natural language description suitable for UI and speech"
    )
    scene_summary: Optional[str] = Field(
        default=None, description="Descriptive environmental scene summary"
    )
    path_status: Optional[Literal["clear", "partially_blocked", "blocked", "uncertain"]] = Field(
        default="clear", description="Status of the walking path ahead"
    )
    guidance: Optional[str] = Field(
        default=None, description="Actionable directional guidance for navigation"
    )
    guidance_direction: Optional[str] = Field(
        default=None, description="Actionable directional guidance"
    )
    voice_response: Optional[str] = Field(
        default=None, description="Concise spoken response optimized for speech synthesis"
    )
    objects: List[DetectedObject] = Field(
        default_factory=list, description="List of recognized spatial objects"
    )
    uncertainty: Optional[str] = Field(
        default=None, description="Explicit note of uncertainty if the frame is blurry or ambiguous"
    )
    target_found: Optional[bool] = Field(
        default=None, description="Indicates if a specific sought target object was located"
    )
    target_status: Optional[Literal["found", "not_found", "not_requested"]] = Field(
        default="not_requested", description="Target search status"
    )
    hazard_alert: Optional[str] = Field(
        default=None, description="Urgent safety warning for close obstacles or drop-offs if present"
    )
    spatial_instruction: Optional[str] = Field(
        default=None, description="Primary spatial instruction ready for Text-to-Speech"
    )


class AnalyzeRequest(BaseModel):
    """Payload received from the mobile browser camera capture."""
    image: str = Field(..., description="Base64-encoded image string or data URL")
    query: Optional[str] = Field(
        default=None, description="Optional voice query or target search phrase (e.g. 'Find my keys', 'Where is my bottle?')"
    )
    mode: Optional[Literal["standard", "find_target", "continuous_guidance", "text_reading"]] = Field(
        default="standard", description="Operating mode of the analysis"
    )
    target_object: Optional[str] = Field(
        default=None, description="Specific target item being searched for"
    )


class AnalyzeResponse(BaseModel):
    """Response returned to the mobile UI."""
    success: bool
    data: Optional[VisionResult] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None
