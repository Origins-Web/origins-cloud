import cv2
import requests
import time

API_URL = "http://localhost:8000/predict/image"
API_KEY = "origins-dev-key-123"
HEADERS = {"X-API-Key": API_KEY}

def test_stream():
    cap = cv2.VideoCapture(0) # 0 for default webcam
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Press 'q' to quit. Sending 1 frame per second to API...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Show the local feed
        cv2.imshow("Origins Local Feed", frame)

        # Encode frame to JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        
        # Send to API
        try:
            files = {"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")}
            response = requests.post(API_URL, headers=HEADERS, files=files)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Detected {data['detection_count']} objects.")
                for obj in data['detections']:
                    print(f" -> {obj['class_name']} ({obj['confidence']})")
            else:
                print(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Connection failed: {e}")

        # Throttle to avoid spamming the local server during a simple test
        time.sleep(1)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_stream()