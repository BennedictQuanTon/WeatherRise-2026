import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage
from backend.schemas.session_schema import SessionSchema
from backend.schemas.risk_schema import WeatheriseRiskSchema
import json

class NotificationAgent:
    def __init__(self):
        base_url = os.getenv("NVIDIA_BASE_URL", "http://localhost:8001/v1")
        api_key = os.getenv("NVIDIA_API_KEY", "local")
        
        self.llm = ChatNVIDIA(
            base_url=base_url, 
            api_key=api_key,
            model="meta/llama3-8b-instruct"
        )

    def generate_alert(self, session: SessionSchema, new_risk: WeatheriseRiskSchema) -> dict:
        prompt = f"""
        You are the Weatherise Alert Notification system.
        The user had a trip planned to {new_risk.location}.
        Previously, the risk was '{session.last_risk_overall}'.
        Now, the risk has worsened to '{new_risk.risk.overall}'.
        Specifics: Rain={new_risk.risk.rain}, Heat={new_risk.risk.heat}, Wind={new_risk.risk.wind}.
        
        Generate a very short, urgent but polite push notification message (under 20 words).
        Return JSON with key: "alert_message".
        """
        
        alert_msg = f"Weather Alert: Conditions at {new_risk.location} have worsened to {new_risk.risk.overall}."
        
        try:
            res = self.llm.invoke([HumanMessage(content=prompt)])
            content = res.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            data = json.loads(content.strip())
            if "alert_message" in data:
                alert_msg = data["alert_message"]
        except Exception as e:
            print(f"Notification LLM failed: {e}")
            
        if session.alert_channel == "sms":
            phone = session.phone_number or "+84_MOCK_NUMBER"
            alert_msg = f"[📱 SMS MOCK SENT TO {phone}] {alert_msg}"
        else:
            alert_msg = f"[🖥️ UI BANNER] {alert_msg}"
            
        return {
            "session_id": session.session_id,
            "channel": session.alert_channel,
            "message": alert_msg,
            "new_recommendation": new_risk.recommendation
        }

notification_agent = NotificationAgent()
