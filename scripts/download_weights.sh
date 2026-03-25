#!/bin/bash
# This script downloads the standard YOLOv8 nano weights for testing.

MODEL_DIR="api/inference/models"
MODEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"

mkdir -p $MODEL_DIR

echo "Downloading YOLOv8n weights..."
curl -L -o $MODEL_DIR/yolov8n.pt $MODEL_URL

echo "Download complete. Model saved to $MODEL_DIR/yolov8n.pt"