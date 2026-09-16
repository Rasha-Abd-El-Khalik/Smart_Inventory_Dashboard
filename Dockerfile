# Hugging Face Spaces (Docker SDK) runs whatever this Dockerfile builds,
# and expects the app to listen on port 7860 by default.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Hugging Face Spaces routes external traffic to port 7860 inside the
# container -- this must match the --port below.
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
