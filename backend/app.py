import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import run_pipeline
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AppCompiler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/generate")
async def generate(request: GenerateRequest):
    if not request.prompt or len(request.prompt.strip()) < 5:
        raise HTTPException(status_code=400, detail="Prompt too short")

    result = run_pipeline(request.prompt)
    return result


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
