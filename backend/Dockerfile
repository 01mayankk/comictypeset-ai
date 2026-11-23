# Pinned Python 3.11 Debian Slim Image for Hugging Face Spaces
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EASYOCR_MODULE_PATH=/home/user/.EasyOCR \
    PORT=7860

# Install system dependencies required for OpenCV headless and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with UID 1000 per Hugging Face Spaces requirements
RUN useradd -m -u 1000 user

# Set up working directory and writable EasyOCR and cache paths
WORKDIR /app
RUN mkdir -p /home/user/.EasyOCR /home/user/.cache /app/models \
    && chown -R user:user /home/user /app

# Switch to non-root user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Copy requirements and install dependencies
COPY --chown=user:user requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --user -r /app/requirements.txt

# Copy application code
COPY --chown=user:user app /app/app
COPY --chown=user:user models /app/models

# Expose port 7860
EXPOSE 7860

# Run Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
