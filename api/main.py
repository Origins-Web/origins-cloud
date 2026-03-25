from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from api.core.config import settings
from api.core.security import verify_api_key
from api.inference.engine import vision_engine
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Origins Base Architecture for Computer Vision deployments.",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    return {
        "status": "online", 
        "engine_ready": vision_engine.model is not None,
        "model_loaded": settings.MODEL_PATH
    }

@app.post("/predict/image", dependencies=[Depends(verify_api_key)])
def predict_image(file: UploadFile = File(...), confidence: float = None):
    """
    Standard HTTP endpoint for processing single frames (e.g., from a trigger camera).
    Using standard 'def' instead of 'async def' to run blocking ML code in a threadpool.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        contents = file.file.read()
        results = vision_engine.process_image(contents, confidence)
        return JSONResponse(content=results)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal inference error.")
    finally:
        file.file.close()