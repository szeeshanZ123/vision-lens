# 🔭 Vision Lens — Future Scope & Roadmap

This document outlines the planned future enhancements and architectural evolution for Vision Lens post-hackathon.

---

## 1. Edge & On-Device AI Acceleration
- **MediaPipe / YOLO On-Device Object Detection**: Integrate quantized TensorFlow Lite or ONNX Runtime models running directly on Android NPUs to provide ultra-low-latency (<40ms) obstacle warnings without internet access.
- **On-Device OCR with Google ML Kit**: Replace cloud-dependent text extraction with on-device text recognition for offline book, sign, and document reading.

## 2. Multi-Modal Sensor Fusion
- **LiDAR & ToF Sensor Integration**: Utilize Android ARCore and hardware Time-of-Flight sensors to calculate exact metric distance maps and ground plane detection instead of monocular estimation.
- **IMU Orientation & Spatial Audio**: Integrate smartphone gyroscope and compass data to create 3D binaural spatial audio beacons that orient users towards targets in physical 3D space.

## 3. Specialized Accessibility Modes
- **Medicine & Prescription Scanner**: Barcode, NDC, and label scanning connected to FDA databases to identify medications, dosages, and expiration dates.
- **Currency Reader**: Immediate high-contrast audio identification of banknotes and coin denominations.
- **Indoor Turn-by-Turn Wayfinding**: Integration with indoor BLE (Bluetooth Low Energy) beacon networks and floorplan maps for navigating transit stations, hospitals, and educational buildings.

## 4. Wearable Form Factor
- **Smart Glasses Support**: Adaptation for lightweight smart glasses (Ray-Ban Meta, Android XR glasses) featuring hands-free head-mounted camera capture and bone-conduction audio output.

