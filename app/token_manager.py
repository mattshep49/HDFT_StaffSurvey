"""
Token Manager - Handles generation, validation, and lookup of survey tokens
Tokens are linked to assignment numbers where Primary = 'Y'
"""

import secrets
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Tuple
import sqlite3

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages survey tokens linked to staff assignments"""
    
    def __init__(self, db_path: str = 'data/tokens.db'):
        """
        Initialize Token Manager
        
        Args:
            db_path: Path to SQLite database for token storage
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tokens table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tokens (
                        id INTEGER PRIMARY KEY,
                        token TEXT UNIQUE NOT NULL,
                        token_hash TEXT UNIQUE NOT NULL,
                        assignment_number TEXT NOT NULL,
                        staff_id TEXT NOT NULL,
                        staff_name TEXT,
                        department TEXT,
                        is_primary BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        used_at TIMESTAMP,
                        is_valid BOOLEAN DEFAULT 1,
                        response_id INTEGER,
                        UNIQUE(assignment_number)
                    )
                ''')
                
                # Responses table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS responses (
                        id INTEGER PRIMARY KEY,
                        token_id INTEGER NOT NULL,
                        response_data TEXT,
                        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completion_time_seconds INTEGER,
                        FOREIGN KEY(token_id) REFERENCES tokens(id)
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_token ON tokens(token)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignment ON tokens(assignment_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_staff_id ON tokens(staff_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_primary ON tokens(is_primary)')
                
                conn.commit()
                logger.info("Token database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def generate_token(self, assignment_number: str, staff_id: str, 
                      staff_name: str = None, department: str = None,
                      expires_at: datetime = None) -> str:
        """
        Generate a unique token for a staff member
        
        Args:
            assignment_number: Unique assignment identifier (Primary = 'Y')
            staff_id: Staff member ID
            staff_name: Staff member name
            department: Staff member department
            expires_at: Token expiration datetime
            
        Returns:
            Generated token string
            
        Raises:
            ValueError: If assignment already has a token
        """
        try:
            # Generate cryptographically secure token
            token = secrets.token_urlsafe(32)
            token_hash = self._hash_token(token)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if assignment already exists
                cursor.execute('SELECT id FROM tokens WHERE assignment_number = ?', 
                             (assignment_number,))
                if cursor.fetchone():
                    raise ValueError(f"Token already exists for assignment {assignment_number}")
                
                # Insert token
                cursor.execute('''
                    INSERT INTO tokens 
                    (token, token_hash, assignment_number, staff_id, staff_name, 
                     department, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (token, token_hash, assignment_number, staff_id, staff_name, 
                      department, expires_at))
                
                conn.commit()
                logger.info(f"Token generated for assignment {assignment_number}")
                
            return token
            
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            raise
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate a token and return associated staff information
        
        Args:
            token: Token string to validate
            
        Returns:
            Tuple of (is_valid, token_data)
            - is_valid: True if token is valid and not expired
            - token_data: Dict with staff/assignment info if valid, None otherwise
        """
        try:
            token_hash = self._hash_token(token)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, assignment_number, staff_id, staff_name, department,
                           created_at, expires_at, is_valid, used_at
                    FROM tokens
                    WHERE token_hash = ?
                ''', (token_hash,))
                
                row = cursor.fetchone()
                
                if not row:
                    logger.warning("Invalid token provided")
                    return False, None
                
                token_id, assignment_number, staff_id, staff_name, department, \
                    created_at, expires_at, is_valid, used_at = row
                
                # Check validity
                if not is_valid:
                    logger.warning(f"Token marked as invalid: {assignment_number}")
                    return False, None
                
                if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                    logger.warning(f"Token expired: {assignment_number}")
                    return False, None
                
                # If already used
                if used_at:
                    logger.warning(f"Token already used: {assignment_number}")
                    # Return data but flag as already submitted
                    return True, {
                        'token_id': token_id,
                        'assignment_number': assignment_number,
                        'staff_id': staff_id,
                        'staff_name': staff_name,
                        'department': department,
                        'already_submitted': True
                    }
                
                return True, {
                    'token_id': token_id,
                    'assignment_number': assignment_number,
                    'staff_id': staff_id,
                    'staff_name': staff_name,
                    'department': department,
                    'already_submitted': False
                }
                
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, None
    
    def mark_token_used(self, token: str, response_id: int = None) -> bool:
        """
        Mark a token as used after survey submission
        
        Args:
            token: Token string
            response_id: Associated response record ID
            
        Returns:
            True if successful
        """
        try:
            token_hash = self._hash_token(token)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE tokens
                    SET used_at = CURRENT_TIMESTAMP, response_id = ?
                    WHERE token_hash = ?
                ''', (response_id, token_hash))
                
                conn.commit()
                logger.info(f"Token marked as used: {token_hash[:8]}...")
                
            return True
            
        except Exception as e:
            logger.error(f"Error marking token as used: {e}")
            return False
    
    def invalidate_token(self, token: str) -> bool:
        """
        Invalidate a token (e.g., for staff member who left)
        
        Args:
            token: Token string
            
        Returns:
            True if successful
        """
        try:
            token_hash = self._hash_token(token)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE tokens
                    SET is_valid = 0
                    WHERE token_hash = ?
                ''', (token_hash,))
                
                conn.commit()
                logger.info(f"Token invalidated: {token_hash[:8]}...")
                
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating token: {e}")
            return False
    
    def get_token_stats(self) -> Dict:
        """
        Get overall token statistics
        
        Returns:
            Dictionary with token stats
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total tokens
                cursor.execute('SELECT COUNT(*) FROM tokens')
                total = cursor.fetchone()[0]
                
                # Used tokens
                cursor.execute('SELECT COUNT(*) FROM tokens WHERE used_at IS NOT NULL')
                used = cursor.fetchone()[0]
                
                # Expired tokens
                cursor.execute('''
                    SELECT COUNT(*) FROM tokens 
                    WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
                ''')
                expired = cursor.fetchone()[0]
                
                # Valid but unused
                unused = total - used - expired
                
                return {
                    'total_tokens': total,
                    'submitted': used,
                    'pending': max(0, unused),
                    'expired': expired,
                    'submission_rate': round((used / total * 100), 2) if total > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting token stats: {e}")
            return {}
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage (never store plain tokens)"""
        return hashlib.sha256(token.encode()).hexdigest()


# Example usage
if __name__ == "__main__":
    import os
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Initialize manager
    manager = TokenManager()
    
    # Generate sample tokens
    print("Generating sample tokens...")
    token1 = manager.generate_token(
        assignment_number="ASS-001",
        staff_id="EMP-12345",
        staff_name="John Smith",
        department="Clinical"
    )
    print(f"Token 1: {token1}")
    
    # Validate token
    print("\nValidating token...")
    is_valid, data = manager.validate_token(token1)
    print(f"Valid: {is_valid}")
    print(f"Data: {data}")
    
    # Get stats
    print("\nToken Statistics:")
    stats = manager.get_token_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
