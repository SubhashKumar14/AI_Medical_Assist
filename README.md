# AI-Telemedicine-CDSS

## Design and Development of an Explainable AI-Assisted Clinical Decision Support System for Telemedicine Applications

**Abstract**

Healthcare accessibility remains a major challenge, particularly in rural and underserved regions where shortages of medical professionals, delayed consultations, and fragmented medical records negatively impact patient outcomes. While telemedicine platforms have improved remote consultations, most existing systems lack intelligent pre-consultation analysis and rely heavily on manual clinical workflows. Additionally, the use of opaque, black-box AI models in healthcare raises concerns regarding interpretability, safety, and trust.

This project presents an **AI-assisted Telemedicine Platform designed as a Clinical Decision Support System (CDSS)** using the MERN stack integrated with a dedicated Python-based AI microservice. The core innovation of the system is an **iterative symptom analysis and elimination engine** that extracts symptoms from free-text user input using clinical Natural Language Processing and progressively narrows possible conditions through adaptive questioning and probabilistic reasoning. Instead of generating one-step predictions, the system dynamically selects follow-up questions to reduce diagnostic uncertainty, producing a ranked list of probable conditions with confidence scores.

To ensure real-world applicability and ethical compliance, the platform follows a **safety-first, human-in-the-loop architecture**. AI outputs are treated as assistive insights rather than final diagnoses, with licensed doctors reviewing and validating recommendations. A deterministic rule-based safety layer detects critical “red-flag” symptoms and triggers escalation when necessary. Explainability is achieved through transparent symptom-contribution analysis, eliminating the need for paid XAI tools.

The system also supports **AI-assisted medical report analysis** through uploaded PDFs and images, enabling automated extraction, summarization, and flagging of abnormal findings. The architecture is designed for **model and API flexibility**, allowing seamless switching between local pretrained models and cloud-based APIs such as Gemini and OpenRouter. Developed as a major B.Tech IT project for a three-member team, the platform demonstrates scalable system design, ethical AI practices, and industry-grade engineering suitable for real-world telemedicine applications.

## Structure

- **frontend/**: React Client (UI + WebRTC)
- **backend/**: Node.js + Express (API Gateway)
- **ai_service/**: Python AI Microservice
- **evaluation/**: datasets, benchmarks, reports
- **docker/**: docker-compose.yml
- **docs/**: architecture, methodology, safety, limitations

## Key Features

- **Iterative Symptom Elimination Engine**: Progressive questioning to narrow down conditions.
- **Explainable AI (XAI)**: Symptom contribution scoring and probability tracking.
- **Medical Report Analysis**: PDF/Image OCR, parsing, and summarization.
- **Hybrid AI Architecture**: Local models (Bio_ClinicalBERT) with Cloud API fallback (Gemini).
- **Human-in-the-Loop**: Doctor validation of AI insights.
- **Safety First**: Rule-based red-flag detection.

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Docker & Docker Compose (optional)
- MongoDB
- Redis

### Installation

1. **Clone and setup environment:**
   ```bash
   cd AI-Telemedicine-CDSS
   cp .env.example .env
   # Edit .env with your API keys (GEMINI_API_KEY, etc.)
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   npm install
   npm run dev
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **AI Service Setup:**
   ```bash
   cd ai_service
   pip install -r requirements.txt
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Deployment
```bash
cd docker
docker-compose up --build
```

## API Endpoints

### Backend Gateway (Port 5000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/triage/start` | Start symptom triage session |
| POST | `/api/ai/triage/next` | Get next follow-up question |
| POST | `/api/ai/report/analyze` | Upload and analyze medical report |
| GET | `/api/ai/session/:id` | Get session state and probabilities |

### AI Service (Port 8000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/start` | Initialize symptom elimination |
| POST | `/next` | Process answer, return next question |
| POST | `/extract_symptoms` | Extract symptoms from text |
| POST | `/report/analyze` | Analyze uploaded report |
| GET | `/session/{id}` | Get session details |

## Project Structure

```
AI-Telemedicine-CDSS/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SymptomChecker/     # Main triage UI
│   │   │   └── ReportAnalyzer/     # Report upload UI
│   │   └── services/
│   │       └── api.js              # Axios client
│   └── package.json
│
├── backend/
│   ├── controllers/
│   │   └── aiProxyController.js    # AI service proxy
│   ├── middlewares/
│   │   ├── consentMiddleware.js    # Consent enforcement
│   │   ├── auditMiddleware.js      # Request logging
│   │   └── authMiddleware.js       # JWT auth
│   ├── routes/
│   │   └── aiRoutes.js             # AI endpoints
│   └── index.js                    # Server entry
│
├── ai_service/
│   ├── engines/
│   │   ├── symptom_elimination.py  # Bayesian elimination
│   │   └── explainability.py       # XAI features
│   ├── model_adapters/
│   │   ├── model_selector.py       # AI router
│   │   ├── local_model_adapter.py  # Hugging Face
│   │   └── api_model_adapter.py    # Gemini/OpenRouter
│   ├── report_analysis/
│   │   ├── ocr_engine.py           # Tesseract OCR
│   │   ├── report_parser.py        # Lab value extraction
│   │   └── report_summarizer.py    # AI summaries
│   ├── knowledge/
│   │   ├── disease_symptom.csv     # 90+ disease mappings
│   │   ├── red_flags.json          # Critical symptoms
│   │   ├── symptom_questions.json  # Follow-up templates
│   │   ├── lab_reference_ranges.json
│   │   ├── precautions.json        # Disease precautions
│   │   └── medicine_rules.json     # Clinical rules
│   ├── app.py                      # FastAPI entry
│   └── requirements.txt
│
├── evaluation/
│   ├── calculate_accuracy.py       # Accuracy metrics
│   └── datasets/
│       └── test_cases.csv          # Synthetic test data
│
├── docker/
│   └── docker-compose.yml
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── AI_METHODOLOGY.md
│   ├── SAFETY_AND_ETHICS.md
│   └── LIMITATIONS.md
│
├── .env.example
└── README.md
```

## Core Algorithm: Bayesian Symptom Elimination

```
For each disease D and observed symptoms S:
    P(D|S) ∝ P(S|D) × P(D)
    
Where:
- P(D) = Prior probability (base rate)
- P(S|D) = Likelihood from disease-symptom weights
- P(D|S) = Posterior probability (what we show)
```

**Question Selection**: Uses information gain (entropy reduction) to select the most discriminating follow-up question.

## Evaluation

Run accuracy evaluation:
```bash
cd evaluation
python calculate_accuracy.py --test-file datasets/test_cases.csv
```

Metrics computed:
- **Top-1 Accuracy**: Correct disease is #1 prediction
- **Top-3 Accuracy**: Correct disease in top 3
- **Mean Reciprocal Rank (MRR)**

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Axios, React Router |
| Backend | Node.js, Express, Mongoose |
| AI Service | FastAPI, Transformers, PyTesseract |
| Database | MongoDB |
| Cache | Redis |
| Local AI | Bio_ClinicalBERT, DistilBERT |
| Cloud AI | Gemini Pro, OpenRouter |
| OCR | Tesseract, PaddleOCR |
| Container | Docker, Docker Compose |

## Team

B.Tech IT Major Project - 3 Member Team

## License

Educational Use - MIT License

## Disclaimer

⚠️ **This system is a Clinical Decision SUPPORT System (CDSS), NOT a diagnostic tool.**

- AI outputs are assistive insights, not medical diagnoses
- All recommendations must be reviewed by licensed healthcare professionals
- Do not use this system for emergency medical conditions
- Always consult a qualified doctor for medical advice
