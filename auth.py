"""
Authentication module for MyBank
Handles PIN code creation, verification, and password hashing
"""
import hashlib
import secrets
from typing import Optional


class AuthManager:
    """Manages user authentication and PIN codes"""
    
    @staticmethod
    def hash_pin(pin: str) -> str:
        """Hash a PIN code with salt"""
        salt = secrets.token_hex(16)
        pin_hash = hashlib.sha256((salt + pin).encode()).hexdigest()
        return f"{salt}${pin_hash}"
    
    @staticmethod
    def verify_pin(pin: str, stored_hash: str) -> bool:
        """Verify a PIN against stored hash"""
        if not stored_hash:
            return False
        
        try:
            salt, hash_value = stored_hash.split('$')
            computed_hash = hashlib.sha256((salt + pin).encode()).hexdigest()
            return secrets.compare_digest(computed_hash, hash_value)
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def validate_pin_format(pin: str) -> tuple[bool, str]:
        """Validate PIN format (4-6 digits)"""
        if not pin.isdigit():
            return False, "PIN должен содержать только цифры"
        
        if len(pin) < 4:
            return False, "PIN должен быть минимум 4 цифры"
        
        if len(pin) > 6:
            return False, "PIN должен быть максимум 6 цифр"
        
        return True, "OK"
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)


class SessionManager:
    """Manages user sessions"""
    
    def __init__(self):
        self._sessions: dict[str, dict] = {}
    
    def create_session(self, telegram_id: int) -> str:
        """Create a new session for user"""
        token = AuthManager.generate_session_token()
        self._sessions[token] = {
            'telegram_id': telegram_id,
            'authenticated': False,
            'pin_verified': False
        }
        return token
    
    def verify_session(self, token: str) -> Optional[dict]:
        """Verify session token"""
        return self._sessions.get(token)
    
    def mark_authenticated(self, token: str):
        """Mark session as authenticated"""
        if token in self._sessions:
            self._sessions[token]['authenticated'] = True
            self._sessions[token]['pin_verified'] = True
    
    def invalidate_session(self, token: str):
        """Remove session"""
        self._sessions.pop(token, None)
    
    def is_authenticated(self, token: str) -> bool:
        """Check if session is authenticated"""
        session = self._sessions.get(token)
        return session.get('authenticated', False) if session else False


# Global session manager instance
session_manager = SessionManager()
