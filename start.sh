#!/bin/bash
# Start FastAPI backend on port 8000 in the background
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit frontend on port 7860
streamlit run frontend.py --server.port 7860 --server.address 0.0.0.0
