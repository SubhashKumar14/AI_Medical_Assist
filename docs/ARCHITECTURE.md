# System Architecture

## Overview
The system follows a microservices architecture with a React frontend, Node.js API Gateway, and a Python AI service.

## Components
1.  **Frontend**: React.js with WebRTC for video consultations.
2.  **Backend**: Node.js/Express.js handling API requests, authentication, and database interactions.
3.  **AI Service**: Python/FastAPI service hosting the symptom elimination engine and model adapters.
4.  **Database**: MongoDB for storing user data, reports, and audit logs.
5.  **Cache**: Redis for session state management during symptom analysis.
