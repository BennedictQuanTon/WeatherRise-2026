import redis
import os
from typing import Optional, List
from backend.schemas.session_schema import SessionSchema
from dotenv import load_dotenv

load_dotenv()

class RedisStore:
    def __init__(self):
        self.r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )

    def save_session(self, session: SessionSchema):
        key = f"session:{session.session_id}"
        self.r.set(key, session.model_dump_json())

    def get_session(self, session_id: str) -> Optional[SessionSchema]:
        data = self.r.get(f"session:{session_id}")
        if data:
            return SessionSchema.model_validate_json(data)
        return None

    def get_active_sessions(self) -> List[SessionSchema]:
        keys = self.r.keys("session:*")
        sessions = []
        for key in keys:
            data = self.r.get(key)
            if data:
                sess = SessionSchema.model_validate_json(data)
                if sess.is_active:
                    sessions.append(sess)
        return sessions

redis_store = RedisStore()
