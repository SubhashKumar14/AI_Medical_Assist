"""
Run AI Service with Trained DDXPlus Data
=========================================

Start: python run_server.py
Stop:  Ctrl+C

Loads:
- 49 diseases from DDXPlus
- 473 symptoms trained on 1.15M cases
- Information gain-based question selection
"""

import sys
import os

# Add ai_service to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🏥 AI-Assisted Telemedicine CDSS - Starting Server")
    print("=" * 60)
    print("📊 Using trained DDXPlus knowledge base")
    print("🔗 API Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
