from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import os

app = FastAPI(title="Codessa OSS Starter API")

class Health(BaseModel):
    status: str

@app.get("/health", response_model=Health)
def health():
    return Health(status="ok")
