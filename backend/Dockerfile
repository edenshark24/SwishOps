FROM python:3.11-slim

# Prevent Python from writing pyc files and enable unbuffered output for clean logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create a non-privileged system user and group
RUN addgroup --system appgroup && adduser --system --no-create-home --group appuser \
    && chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
