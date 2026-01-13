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
    allow_headers=["*"],
)

# === SAFETY MIDDLEWARE ===
from safety_config import safety_filter, UNSAFE_TERMS, validate_safety
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SafetyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        return response

# Register middleware (placeholder)
# app.add_middleware(SafetyMiddleware)


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

def get_session(session_id: str) -> Optional[dict]:
    """Helper to retrieve session from Redis or Memory"""
    if USE_REDIS:
        try:
            data = redis_client.get(f"session:{session_id}")
            return json.loads(data) if data else None
        except Exception:
            return None
    else:
        return sessions.get(session_id)


# Request/Response models
class StartRequest(BaseModel):
    text: str
    user_id: Optional[str] = "anonymous"
    model_provider: Optional[str] = "auto"

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
    red_flags: Optional[List[Dict[str, Any]]] = None
    safe_summary: Optional[str] = None # MANDATORY SAFE OUTPUT
    extend_needed: bool = False # Flag to ask user consent for more questions

@app.post("/start", response_model=TriageResponse)
async def start_triage(request: StartRequest):
    try:
        session_id = str(uuid.uuid4())
        
        # Extract symptoms
        # Note: validation/extraction happens inside engine or via model_selector
        # For now, using engine's standard extraction
        initial_symptoms = elimination_engine.extract_symptoms(request.text)
        
        # Start Engine Session
        state = elimination_engine.start(initial_symptoms, session_id=session_id)
        
        # Save Session
        sessions[session_id] = {
            "state": state,
            "asked_questions": [],
            "answers": {},
            "model_provider": request.model_provider
        }
        
        # Unpack state
        probabilities = state.get('probabilities', [])
        next_question = state.get('next_question')
        red_flags = state.get('red_flags')
        is_complete = state.get('status') == 'FINISHED'
        symptoms = state.get('present_symptoms', [])
        extend_needed = state.get('extend_needed', False)

        # Generate Safe Summary (The 5-Step Structure)
        from safety_config import format_safe_response, RISK_CATEGORIES, validate_safety
            
        # SAFETY V2: Red Flag Override
        if red_flags:
            safe_text = format_safe_response(
                conditions=["EMERGENCY CONCERN"],
                general_explanation="**CRITICAL WARNING:** Your symptoms indicate a potentially serious medical emergency.",
                next_step="**CALL EMERGENCY SERVICES (911/112) IMMEDIATELY.** Do not wait."
            )
            return TriageResponse(
                session_id=session_id,
                probabilities=[],
                next_question=None,
                is_complete=True,
                red_flags=red_flags,
                safe_summary=validate_safety(safe_text),
                extend_needed=False
            )

        # SAFETY V2: Confidence & Risk Masking
        safe_candidates = []
        top_prob = probabilities[0]['probability'] if probabilities else 0.0
        
        # Threshold Check
        if top_prob < 0.60:
            # Low confidence -> Generic viral/bacterial bucket
            explanation = "Your symptoms are non-specific and could be related to common viral or bacterial infections. No specific condition reached high confidence."
            safe_candidates = ["Common Viral Infection", "Non-specific Bacterial Infection"]
        else:
            # High confidence -> Show top 3 (Masked if needed)
            explanation = f"Symptoms such as {', '.join(symptoms[:3])} are commonly seen in these conditions."
            for p in probabilities[:3]:
                d_name = p['disease']
                # Mask if High Risk
                if d_name in RISK_CATEGORIES:
                    d_name = f"⚠️ {RISK_CATEGORIES[d_name]}"
                safe_candidates.append(d_name)
            
        safe_text = format_safe_response(
            conditions=safe_candidates,
            general_explanation=explanation,
            next_step="Please consult a healthcare professional for further evaluation."
        )

        return TriageResponse(
            session_id=session_id,
            probabilities=probabilities[:10],  # Internal probs still sent for debug/frontend bars? Maybe mask them too? 
            # Ideally frontend shouldn't see sensitive names either.
            # For now, let's keep them but Frontend relies on safe_summary.
            next_question=next_question,
            is_complete=is_complete,
            red_flags=red_flags if red_flags else None,
            safe_summary=validate_safety(safe_text),
            extend_needed=extend_needed
        )
        
    except Exception as e:
        print(f"Error in start_triage: {e}")
        # Return safe fallback
        return TriageResponse(
            session_id=request.user_id, # Fallback ID
            probabilities=[],
            next_question=None,
            is_complete=True,
            safe_summary="**System Error:** Unable to process symptoms at this time. Please try again or consult a doctor directly.",
            extend_needed=False
        )


@app.post("/next", response_model=TriageResponse)
async def next_question_endpoint(request: NextRequest):
    """
    Handle follow-up answer and determine next step.
    """
    try:
        session_id = request.session_id
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
            
        session = sessions[session_id]
        engine_state = session["state"]
        
        # Update Engine with Answer
        new_state = elimination_engine.update(engine_state, request.answer)
        
        # Update Session
        session["state"] = new_state
        
        # Safe access to previous question ID
        prev_q = engine_state.get('next_question') or {}
        session["answers"][prev_q.get('symptom_id', 'unknown')] = request.answer
        
        if prev_q:
             session["asked_questions"].append(prev_q.get('text', ''))

        # Unpack state
        probabilities = new_state.get('probabilities', [])
        next_q = new_state.get('next_question')
        red_flags = new_state.get('red_flags')
        is_complete = new_state.get('status') == 'FINISHED'
        
        # Safety & Summary Logic (Same as start_triage)
        from safety_config import format_safe_response, RISK_CATEGORIES, validate_safety
        
        # 1. Red Flags
        if red_flags:
            safe_text = format_safe_response(
                conditions=["EMERGENCY CONCERN"],
                general_explanation="**CRITICAL WARNING:** Your symptoms indicate a potentially serious medical emergency.",
                next_step="**CALL EMERGENCY SERVICES (911/112) IMMEDIATELY.** Do not wait."
            )
            return TriageResponse(
                session_id=session_id,
                probabilities=[],
                next_question=None,
                is_complete=True,
                red_flags=red_flags,
                safe_summary=validate_safety(safe_text),
                extend_needed=False
            )

        # 2. Risk Masking
        safe_candidates = []
        top_prob = probabilities[0]['probability'] if probabilities else 0.0
        symptoms = new_state.get('present_symptoms', [])
        
        if top_prob < 0.60:
             explanation = "Based on your answers, the cause remains unclear but suggests common minor illnesses."
             safe_candidates = ["Unspecified Viral Illness", "General Fatigue/Stress"]
        else:
            explanation = f"Based on your answers, symptoms such as {', '.join(symptoms[:3])} are consistent with these patterns."
            for p in probabilities[:3]:
                d_name = p['disease']
                if d_name in RISK_CATEGORIES:
                    d_name = f"⚠️ {RISK_CATEGORIES[d_name]}"
                safe_candidates.append(d_name)

        safe_text = format_safe_response(
            conditions=safe_candidates,
            general_explanation=explanation,
            next_step="Please consult a doctor for a physical examination." if is_complete else None
        )

        return TriageResponse(
            session_id=session_id,
            probabilities=probabilities[:10],
            next_question=next_q,
            is_complete=is_complete,
            red_flags=red_flags,
            safe_summary=validate_safety(safe_text),
            extend_needed=new_state.get("extend_needed", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in next_question: {e}")
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
    user_id: str = Form("anonymous"),
    model_provider: str = Form("auto")
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
            abnormal_findings,
            provider=model_provider
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



# === AI CHAT ENDPOINT ===
class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: Optional[str] = "anonymous"
    model_provider: Optional[str] = "auto"

class ChatResponse(BaseModel):
    reply: str
    safe_disclaimer: str

@app.post("/ai/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Context-aware AI Health Chat.
    Uses cached session state from Redis/Memory to provide relevant answers.
    """
    try:
        session_data = get_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # factory prompt
        context = {
            "symptoms": session_data["state"].get("observed_symptoms", []),
            "probabilities": session_data["state"]["probabilities"][:3]
        }
        
        system_prompt = f"""
        You are a helpful AI Health Assistant.
        CONTEXT:
        Patient Symptoms: {', '.join(context['symptoms'])}
        Possible Conditions (Internal): {', '.join([p['disease'] for p in context['probabilities']])}
        
        RULES:
        1. Answer the user's question clearly and simply.
        2. DO NOT diagnose or prescribe.
        3. If asked "What do I have?", refer to the Triage Report summaries.
        4. Refer to the patient context when relevant (e.g. "Given your fever...").
        """
        
        # Call LLM (Gemini preferred, or local fallback)
        # Using ModelSelector to handle routing
        
        reply = await model_selector.generate_chat_response(
            system_prompt=system_prompt,
            user_message=request.message,
            session_context=context,
            provider=request.model_provider
        )
        
        # Safety Filter on Output
        safe_reply = validate_safety(reply)
        
        return ChatResponse(
            reply=safe_reply,
            safe_disclaimer="This is an AI assistant, not a doctor. Advice is informational only."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pill/identify")
async def identify_pill_endpoint(file: UploadFile = File(...)):
    """
    Identify pill from uploaded image.
    """
    try:
        content = await file.read()
        result = await model_selector.identify_pill(content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Import Token System
from booking.token_system import token_system

class BookingRequest(BaseModel):
    patient_id: str
    doctor_id: str
    severity: str # critical, high, normal
    time_slot: Optional[str] = None

@app.post("/appointments/book")
async def book_appointment(request: BookingRequest):
    """
    Book appointment with Priority Token System.
    """
    try:
        booking = await token_system.book_appointment(
            patient_id=request.patient_id,
            doctor_id=request.doctor_id,
            severity=request.severity,
            time_slot=request.time_slot
        )
        return booking
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/doctor/queue")
async def get_doctor_queue():
    """Get priority sorted queue."""
    return token_system.get_queue()

@app.post("/doctor/complete/{token_id}")
async def complete_appointment(token_id: str):
    """Mark appointment as done."""
    if token_system.complete_appointment(token_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Token not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
