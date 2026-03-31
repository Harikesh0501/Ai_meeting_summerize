FROM python:3.10-slim

# Switch to root to install packages
USER root

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face needs a non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy all code
COPY --chown=user . $HOME/app

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 7860 for HuggingFace
EXPOSE 7860

# Command to run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
