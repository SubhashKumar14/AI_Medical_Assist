# AI Methodology

## Core Components

### 1. Symptom Extraction
- **Model**: `emilyalsentzer/Bio_ClinicalBERT`
- **Method**: Token classification / NER.
- **Fallback**: Keyword matching & Regex.

### 2. Inference Engine
- **Algorithm**: Iterative Bayesian Elimination.
- **process**:
    1.  Initialize disease priors.
    2.  Update posteriors based on extracted symptoms.
    3.  Select next question based on Expected Information Gain (entropy).

### 3. Report Analysis
- **OCR**: Tesseract / PaddleOCR.
- **Summarization**: Google Gemini Pro (via API) or Local LLM.

### 4. Explainability
- **Metric**: Symptom contribution scores.
- **Visualization**: Contribution bar charts.
