import random
import datetime
from typing import Dict, List, Optional
import asyncio

class TokenSystem:
    """
    Smart Appointment Token System.
    Prioritizes critical patients for immediate slots.
    """
    
    def __init__(self):
        # In-memory storage for MVP (Redis in production)
        self.active_tokens = {} # token_id -> booking_details
        self.daily_counters = {
            "CRIT": 0,
            "HIGH": 0,
            "REG": 0
        }
    
    def generate_token(self, severity: str) -> str:
        """
        Generate a smart token ID based on severity.
        Format: [SEVERITY]-[YYYYMMDD]-[SEQ]
        Example: CRIT-20250113-001
        """
        today = datetime.datetime.now().strftime("%Y%m%d")
        
        # Map triage severity to token prefix
        if severity == "critical":
            prefix = "CRIT"
        elif severity == "high":
            prefix = "HIGH"
        else:
            prefix = "REG"
            
        # Increment counter
        self.daily_counters[prefix] += 1
        seq = self.daily_counters[prefix]
        
        return f"{prefix}-{today}-{seq:03d}"

    def estimate_wait_time(self, severity: str) -> int:
        """
        Estimate wait time in minutes based on severity.
        """
        if severity == "critical":
            return 0 # Immediate
        elif severity == "high":
            return 15 # Priority
        else:
            return 45 + (self.daily_counters["REG"] * 10) # 10 mins per person ahead

    async def book_appointment(self, patient_id: str, doctor_id: str, severity: str, time_slot: Optional[str] = None):
        """
        Book an appointment and generate a priority token.
        """
        token_id = self.generate_token(severity)
        wait_time = self.estimate_wait_time(severity)
        
        booking = {
            "token_id": token_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "severity": severity,
            "time_slot": time_slot or "IMMEDIATE" if severity == "critical" else time_slot,
            "status": "confirmed", # confirmed, completed, cancelled
            "estimated_wait_minutes": wait_time,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        self.active_tokens[token_id] = booking
        
        return booking

    def get_queue(self) -> List[Dict]:
        """
        Get sorted queue of active appointments.
        Prioritizes Critical > High > Reg.
        """
        severity_weight = {"critical": 0, "high": 1, "normal": 2}
        
        active = [b for b in self.active_tokens.values() if b["status"] == "confirmed"]
        
        # Sort by Severity Weight, then by Creation Time
        active.sort(key=lambda x: (severity_weight.get(x["severity"], 3), x["created_at"]))
        
        return active

    def complete_appointment(self, token_id: str):
        """Mark appointment as completed."""
        if token_id in self.active_tokens:
            self.active_tokens[token_id]["status"] = "completed"
            return True
        return False

# Singleton
token_system = TokenSystem()
