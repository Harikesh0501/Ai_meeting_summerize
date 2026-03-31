FROM python:3.10-slim

# Switch to root to install packages
USER root

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    python3-dev \
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
# Install CPU-only torch to save massive amounts of space and prevent freezing
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# Split heavy installations to prevent Out-Of-Memory errors during pip resolution
RUN pip install --no-cache-dir wheel setuptools
RUN pip install --no-cache-dir fastapi uvicorn python-multipart motor pydantic python-dotenv
RUN pip install --no-cache-dir transformers==4.38.2
RUN pip install --no-cache-dir openai-whisper deep-translator
RUN pip install --no-cache-dir yake
RUN pip install --no-cache-dir resemblyzer spectralcluster
RUN pip install --no-cache-dir -r requirements.txt

# Make start script executable
RUN chmod +x start.sh

# Expose port 7860 for HuggingFace (Streamlit)
EXPOSE 7860

# Command to run both the FastAPI application and Streamlit
CMD ["./start.sh"]