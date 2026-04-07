from fastapi import FastAPI
import os

app = FastAPI(title="Farm Dashboard API", version="0.1.0")

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "farm-api"}
