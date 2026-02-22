<<<<<<< HEAD
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install them
# (We'll create requirements.txt next)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the orchestrator
CMD ["python", "orchestrator/main.py"]
=======
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Copy only the server implementation to keep image lean.
COPY app/server.py ./server.py

EXPOSE 8080

CMD ["python", "server.py"]
COPY app ./app
COPY codex_qernel ./codex_qernel
COPY capsules ./capsules
COPY scripts ./scripts
COPY README.md ./README.md

RUN mkdir -p var/log

EXPOSE 8080

CMD ["python", "app/server.py"]
>>>>>>> core-orchestrator/ci-migration-gh-actions-3099626751256413922
