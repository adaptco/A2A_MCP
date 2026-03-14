FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tasks.py .

# Copy shared libraries
COPY ../../lib /app/lib
COPY ../../schemas /app/schemas

# Create directories
RUN mkdir -p /app/ledger

CMD ["python", "tasks.py"]
