FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py server.py ./
ENV LLM_URL=http://host.docker.internal:8000/v1/chat/completions
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]
