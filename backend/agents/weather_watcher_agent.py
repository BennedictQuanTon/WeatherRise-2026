from backend.services.redis_store import redis_store
from backend.agents.weather_agent import weather_agent
from backend.agents.notification_agent import notification_agent

class WeatherWatcherAgent:
    def check_all_sessions(self):
        sessions = redis_store.get_active_sessions()
        alerts = []
        for session in sessions:
            try:
                new_risk = weather_agent.get_weather_risk(
                    session.destination_id, 
                    session.forecast_date, 
                    session.forecast_time
                )
                
                # Check for worsening condition
                risk_levels = {"good": 0, "caution": 1, "poor": 2}
                old_level = risk_levels.get(session.last_risk_overall, 0)
                new_level = risk_levels.get(new_risk.risk.overall, 0)
                
                if new_level > old_level:
                    alert = notification_agent.generate_alert(session, new_risk)
                    alerts.append(alert)
                    
                    # Update session with new risk
                    session.last_risk_overall = new_risk.risk.overall
                    redis_store.save_session(session)
            except Exception as e:
                print(f"Error checking session {session.session_id}: {e}")
                
        return alerts

    def simulate_conflict(self, session_id: str):
        """Force a conflict for demonstration purposes"""
        session = redis_store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
            
        # Get current to generate alert details
        new_risk = weather_agent.get_weather_risk(
            session.destination_id, 
            session.forecast_date, 
            session.forecast_time
        )
        
        # Force the state to be worse
        session.last_risk_overall = "good"
        new_risk.risk.overall = "poor"
        new_risk.risk.rain = "high"
        new_risk.recommendation = "Due to simulated severe weather, please seek shelter immediately or switch to an indoor activity."
        
        alert = notification_agent.generate_alert(session, new_risk)
        return alert

watcher_agent = WeatherWatcherAgent()
