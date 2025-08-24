# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "run_server:app", "--host", "0.0.0.0", "--port", "8000"]