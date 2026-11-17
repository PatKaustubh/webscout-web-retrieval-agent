from fastapi import FastAPI
from pydantic import BaseModel

from agent import ask

app = FastAPI(title="WebScout")


class Query(BaseModel):
    url: str
    question: str
    max_steps: int = 8


@app.post("/ask")
def ask_endpoint(q: Query):
    return ask(q.url, q.question, q.max_steps)


@app.get("/health")
def health():
    return {"status": "ok"}
