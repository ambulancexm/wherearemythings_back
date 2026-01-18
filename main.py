import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = FastAPI(title="Simple Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: mets ton domaine
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    answer: str

@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": "Tu es un assistant utile. Réponds en français, clairement."},
            {"role": "user", "content": req.message},
        ],
    )
    return {"session_id": req.session_id, "answer": resp.output_text}
