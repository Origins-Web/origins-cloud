from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Origins Vision Integrator"
    API_KEY_SECRET: str = "origins-dev-key-123" 
    DEFAULT_CONFIDENCE: float = 0.5
    MODEL_PATH: str = "api/inference/models/yolov8n.pt"
    # Added AWS placeholders for your automatic expansion
    AWS_S3_BUCKET_NAME: str = ""

    class Config:
        env_file = ".env"

# This line is what the error is looking for!
settings = Settings()