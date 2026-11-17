# WebScout: Natural-Language Web Retrieval Agent

AMD AI League, Match 4 (Intelligent Web Information Retrieval).

WebScout takes a start URL and a plain-English question, navigates the site by
following links, and returns the exact answer, a verbatim evidence sentence and
the source URL. Answers are only accepted when the evidence sentence really
appears in the page text; otherwise the agent keeps searching or reports "not found".

## How it works
1. Fetch the page and clean it to text plus a numbered same-site link list.
2. An LLM (Qwen3, served with vLLM on AMD GPU via ROCm) answers, follows a link, or gives up.
3. Loop with a step cap and visited-page tracking.

## Run (AMD notebook at notebooks.amd.com/hackathon)
```bash
pip install -r requirements.txt
# terminal 1: serve the model (vLLM ROCm build)
vllm serve Qwen/Qwen3-8B --port 8000
# terminal 2: ask a question
python agent.py https://books.toscrape.com "What is the price of A Light in the Attic?"
# or run the API
uvicorn server:app --port 9000
curl -X POST localhost:9000/ask -H 'content-type: application/json' \
  -d '{"url":"https://books.toscrape.com","question":"Price of A Light in the Attic?"}'
```
Env vars: `LLM_URL`, `LLM_MODEL`, `MAX_STEPS`.

## Docker
`docker build -t webscout .` then `docker run -p 9000:9000 webscout`.

## Limitations
Static HTML only (no JavaScript rendering); same-site navigation only.
