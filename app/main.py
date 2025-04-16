# main.py 복사하여 가져옴

from contextlib import asynccontextmanager

from fastapi import FastAPI
from transformers import pipeline
from pydantic import BaseModel
import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from app.s3_client import MinioS3Client

import logging
logger = logging.getLogger(__name__)

class Input(BaseModel):
    text: str="""summarize: Twitter’s interim resident grievance officer for India has stepped down, leaving the micro-blogging site without a grievance official as mandated by the new IT rules to address complaints from Indian subscribers, according to a source.

The source said that Dharmendra Chatur, who was recently appointed as interim resident grievance officer for India by Twitter, has quit from the post.

The social media company’s website no longer displays his name, as required under Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules 2021.

Twitter declined to comment on the development.

The development comes at a time when the micro-blogging platform has been engaged in a tussle with the Indian government over the new social media rules. The government has slammed Twitter for deliberate defiance and failure to comply with the country’s new IT rules.
"""

def prepare_model():
    logger.info(">>> model load")
    # mac os gpu 사용 + local model only
    model_path = "models/t5-small"
    
    # Check if model files exist locally
    model_exists = os.path.exists(os.path.join(model_path, "config.json")) and \
                  (os.path.exists(os.path.join(model_path, "pytorch_model.bin")) or \
                   os.path.exists(os.path.join(model_path, "model.safetensors")))
    
    # If model doesn't exist locally, download it
    if not model_exists:
        logger.info(f"Model not found locally at {model_path}, downloading...")
        
        minio_client = MinioS3Client()
        
        if minio_client.exists(prefix="model/t5-small/"):
            logger.info("Model exists in MinIO, downloading...")    
            minio_client.download_from_minio(prefix="model/t5-small/", local_dir=model_path)
        else:
            logger.info("Model not found in MinIO, downloading from Hugging Face...")
            load_model(model_name="t5-small")
            minio_client.upload_to_minio(local_dir=model_path, prefix="model/t5-small/")
            logger.info("Model uploaded to MinIO")
        logger.info("Model downloaded and saved locally")
    else:
        logger.info(f"Using existing model from {model_path}")
    
    model = pipeline("summarization", model=model_path, device=0)
    return model

def load_model(model_name:str = "t5-small"):
    model_path = os.path.join("models", model_name)
    os.makedirs(model_path, exist_ok=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model.save_pretrained(model_path)
    tokenizer.save_pretrained(model_path)

ml_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    ml_models["nlp_model"] = prepare_model()
    logger.info(ml_models)
    yield
    # Clean up the ML models and release the resources
    ml_models.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/predict")
async def predict(x: Input):
    result = ml_models["nlp_model"].predict(x.text)[0]
    return {"result": result}