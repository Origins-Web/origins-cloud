from api.inference.engine import vision_engine
import cv2

# Create a blank image (black square) to test the pipeline
blank_img = bytes(cv2.imencode('.jpg', (0 * (100, 100, 3)))[1])

try:
    print("🔄 Testing Engine Initialization...")
    results = vision_engine.process_image(blank_img)
    print(f"✅ Engine Status: {results['status']}")
    print(f"📦 Detections found in blank image: {results['detection_count']}")
except Exception as e:
    print(f"❌ Engine Test Failed: {e}")