"""
AI Service API - FastAPI Application

Clinical Decision Support System AI Microservice.

Endpoints:
- POST /start - Start triage session with symptom text
- POST /next - Answer follow-up question
- POST /extract_symptoms - Extract symptoms from text
- POST /report/analyze - Analyze medical report (PDF/image)
- GET /session/{session_id} - Get session state

This service is NOT a diagnostic system - it provides assistive insights only.
"""

import os
import uuid
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import json

# Import internal modules
from engines.symptom_elimination import SymptomEliminationEngine
from engines.explainability import ExplainabilityEngine
from report_analysis.ocr_engine import OCREngine
from report_analysis.report_parser import ReportParser
from model_adapters.model_selector import ModelSelector

app = FastAPI(
    title="AI Telemedicine CDSS",
    description="Clinical Decision Support System AI Microservice",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
elimination_engine = SymptomEliminationEngine()
explainability_engine = ExplainabilityEngine()
ocr_engine = OCREngine()
report_parser = ReportParser()
model_selector = ModelSelector()

# Session storage (Redis in production, in-memory for dev)
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )
    redis_client.ping()
    USE_REDIS = True
except:
    USE_REDIS = False
    sessions: Dict[str, dict] = {}


# Request/Response models
class StartRequest(BaseModel):
    text: str
    user_id: Optional[str] = "anonymous"

class NextRequest(BaseModel):
    session_id: str
    answer: str
    user_id: Optional[str] = "anonymous"

class ExtractRequest(BaseModel):
    text: str

class TriageResponse(BaseModel):
    session_id: str
    probabilities: List[Dict[str, Any]]
    next_question: Optional[Dict[str, Any]]
    is_complete: bool
    red_flags: Optional[List[str]] = None


def save_session(session_id: str, data: dict):
    """Save session to Redis or in-memory store"""
    if USE_REDIS:
        redis_client.setex(session_id, 3600, json.dumps(data))  # 1 hour TTL
    else:
        sessions[session_id] = data

def get_session(session_id: str) -> Optional[dict]:
    """Get session from Redis or in-memory store"""
    if USE_REDIS:
        data = redis_client.get(session_id)
        return json.loads(data) if data else None
    else:
        return sessions.get(session_id)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "ai_service"}


@app.post("/start", response_model=TriageResponse)
async def start_triage(request: StartRequest):
    """
    Start a new triage session.
    
    Extracts symptoms from user text and initializes probability engine.
    """
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Extract symptoms from text
        extracted = elimination_engine.extract_symptoms(request.text)
        symptoms = extracted.get("symptoms", [])
        
        # Check for red flags (emergency symptoms)
        red_flags = elimination_engine.check_red_flags(symptoms)
        
        # Initialize session state
        state = elimination_engine.start(symptoms)
        
        # Get initial probabilities with explainability
        probabilities = explainability_engine.add_contributions(
            state["probabilities"],
            symptoms
        )
        
        # Get first follow-up question
        next_question = elimination_engine.next_question(state)
        
        # Determine if triage is complete
        is_complete = next_question is None or len(state.get("asked_questions", [])) >= 10
        
        # Save session
        session_data = {
            "state": state,
            "user_id": request.user_id,
            "symptoms": symptoms,
            "original_text": request.text,
            "asked_questions": [],
            "answers": []
        }
        save_session(session_id, session_data)
        
        return TriageResponse(
            session_id=session_id,
            probabilities=probabilities[:10],  # Top 10
            next_question=next_question,
            is_complete=is_complete,
            red_flags=red_flags if red_flags else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/next", response_model=TriageResponse)
async def next_step(request: NextRequest):
    """
    Process answer and return next question or final results.
    """
    try:
        # Get session
        session_data = get_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = session_data["state"]
        
        # Update state with answer
        state = elimination_engine.update(state, request.answer)
        
        # Track question/answer
        session_data["asked_questions"].append(state.get("last_question"))
        session_data["answers"].append(request.answer)
        
        # Get updated probabilities with explainability
        probabilities = explainability_engine.add_contributions(
            state["probabilities"],
            session_data["symptoms"]
        )
        
        # Get next question
        next_question = elimination_engine.next_question(state)
        
        # Determine if complete (max 10 questions or no more questions)
        is_complete = next_question is None or len(session_data["asked_questions"]) >= 10
        
        # Update session
        session_data["state"] = state
        save_session(request.session_id, session_data)
        
        return TriageResponse(
            session_id=request.session_id,
            probabilities=probabilities[:10],
            next_question=next_question,
            is_complete=is_complete
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract_symptoms")
async def extract_symptoms(request: ExtractRequest):
    """
    Extract symptoms from free text input.
    """
    try:
        result = elimination_engine.extract_symptoms(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}")
async def get_session_state(session_id: str):
    """
    Get current session state.
    """
    session_data = get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "probabilities": session_data["state"]["probabilities"][:10],
        "asked_questions": session_data["asked_questions"],
        "answers": session_data["answers"]
    }


@app.post("/report/analyze")
async def analyze_report(
    file: UploadFile = File(...),
    user_id: str = Form("anonymous")
):
    """
    Analyze uploaded medical report (PDF/image).
    
    Returns extracted text, lab values, abnormal findings, and AI summary.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Extract text using OCR
        extracted_text = ocr_engine.extract_text(content, file.content_type)
        
        # Parse lab values
        lab_values = report_parser.parse_lab_values(extracted_text)
        
        # Identify abnormal findings
        abnormal_findings = report_parser.identify_abnormalities(lab_values)
        
        # Check for red flags
        red_flags = report_parser.check_critical_values(lab_values)
        
        # Generate AI summary (using model selector for API routing)
        summary = await model_selector.summarize_report(
            extracted_text,
            lab_values,
            abnormal_findings
        )
        
        return {
            "extracted_text": extracted_text[:2000],  # Truncate for response
            "lab_values": lab_values,
            "abnormal_findings": abnormal_findings,
            "red_flags": red_flags,
            "summary": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
