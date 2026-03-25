import cv2
import numpy as np
import logging
from ultralytics import YOLO
from api.core.config import settings

logger = logging.getLogger("origins.vision")

class VisionEngine:
    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        try:
            logger.info(f"Loading YOLO model from {settings.MODEL_PATH}")
            self.model = YOLO(settings.MODEL_PATH)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError("Vision model failed to initialize.")

    def process_image(self, image_bytes: bytes, confidence: float = None):
        if self.model is None:
            raise RuntimeError("Model is not loaded.")

        conf_threshold = confidence if confidence is not None else settings.DEFAULT_CONFIDENCE

        # Convert raw bytes to OpenCV image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Invalid image payload.")

        # Run inference
        results = self.model.predict(source=img, conf=conf_threshold, save=False, verbose=False)
        
        # Format results for API response
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Extract coordinates and class info
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                class_id = int(box.cls[0].item())
                class_name = self.model.names[class_id]

                detections.append({
                    "class_name": class_name,
                    "confidence": round(conf, 4),
                    "bounding_box": {
                        "x1": int(x1), "y1": int(y1), 
                        "x2": int(x2), "y2": int(y2)
                    }
                })

        return {
            "status": "success",
            "detection_count": len(detections),
            "detections": detections
        }

# Global singleton so the model only loads once into memory upon server start
vision_engine = VisionEngine()