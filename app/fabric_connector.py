"""
Fabric Lakehouse Connector
Reads survey questions and responses from Fabric Lakehouse tables
"""

import json
import logging
import os
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FabricLakehouseConnector:
    """Connects to Fabric Lakehouse using SQL endpoint"""
    
    def __init__(self, server: str = None, database: str = None, 
                 username: str = None, password: str = None):
        """
        Initialize Lakehouse connector
        
        Args:
            server: SQL endpoint server (e.g., fabric-workspace.database.windows.net)
            database: Lakehouse name (e.g., Staff_survey_HDFT)
            username: Username
            password: Password
        """
        self.server = server or os.getenv('FABRIC_SQL_SERVER')
        self.database = database or os.getenv('FABRIC_LAKEHOUSE_NAME')
        self.username = username or os.getenv('FABRIC_SQL_USER')
        self.password = password or os.getenv('FABRIC_SQL_PASSWORD')
        self.connection = None
        self._import_pyodbc()
    
    def _import_pyodbc(self):
        """Import pyodbc library"""
        try:
            import pyodbc
            self.pyodbc = pyodbc
        except ImportError:
            logger.warning("pyodbc not installed. Install with: pip install pyodbc")
            self.pyodbc = None
    
    def connect(self) -> bool:
        """Establish connection to Lakehouse"""
        try:
            if not self.pyodbc:
                logger.error("pyodbc library required for SQL connection")
                return False
            
            connection_string = (
                f'Driver={{ODBC Driver 17 for SQL Server}};'
                f'Server={self.server},1433;'
                f'Database={self.database};'
                f'UID={self.username};'
                f'PWD={self.password};'
                f'Encrypt=yes;'
                f'TrustServerCertificate=no;'
                f'Connection Timeout=30;'
            )
            
            self.connection = self.pyodbc.connect(connection_string, autocommit=True)
            logger.info(f"Connected to Lakehouse: {self.database}")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Disconnected from Lakehouse")
            except:
                pass
    
    def execute_query(self, query: str) -> List[Dict]:
        """
        Execute SQL query and return results as list of dicts
        
        Args:
            query: SQL query string
            
        Returns:
            List of result rows as dictionaries
        """
        try:
            if not self.connection:
                logger.error("Not connected to Lakehouse")
                return []
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = [
                dict(zip(columns, row))
                for row in rows
            ]
            
            cursor.close()
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def load_survey_questions(self, table_name: str = 'survey_questions') -> List[Dict]:
        """
        Load survey questions from Lakehouse table
        
        Args:
            table_name: Name of the survey questions table in Lakehouse
            
        Returns:
            List of survey question dictionaries
        """
        if not self.connection:
            if not self.connect():
                logger.error("Cannot load questions - connection failed")
                return []
        
        query = f"""
        SELECT 
            question_id,
            question_text,
            answer_type,
            answer_options,
            is_required,
            section,
            sequence
        FROM {table_name}
        WHERE is_active = 1
        ORDER BY sequence ASC
        """
        
        questions = self.execute_query(query)
        
        # Parse JSON answer_options
        for q in questions:
            if q.get('answer_options'):
                try:
                    q['answer_options'] = json.loads(q['answer_options'])
                except:
                    q['answer_options'] = []
        
        logger.info(f"Loaded {len(questions)} survey questions from {table_name}")
        return questions
    
    def save_survey_response(self, token_id: int, assignment_number: str, 
                           staff_id: str, responses: Dict) -> int:
        """
        Save survey response to Lakehouse
        
        Args:
            token_id: Associated token ID
            assignment_number: Assignment number
            staff_id: Staff ID
            responses: Dictionary of question_id: answer
            
        Returns:
            Response ID if successful, 0 otherwise
        """
        try:
            if not self.connection:
                logger.error("Not connected to Lakehouse")
                return 0
            
            cursor = self.connection.cursor()
            
            response_json = json.dumps(responses)
            submitted_at = datetime.now().isoformat()
            
            insert_query = f"""
            INSERT INTO survey_responses 
            (token_id, assignment_number, staff_id, response_data, submitted_at)
            VALUES 
            ({token_id}, '{assignment_number}', '{staff_id}', N'{response_json}', '{submitted_at}')
            """
            
            cursor.execute(insert_query)
            
            # Get the inserted ID
            cursor.execute("SELECT SCOPE_IDENTITY()")
            response_id = cursor.fetchone()[0]
            cursor.close()
            
            logger.info(f"Response saved for assignment {assignment_number}")
            return int(response_id)
            
        except Exception as e:
            logger.error(f"Error saving response: {e}")
            return 0
    
    def get_response_stats(self) -> Dict:
        """Get response statistics"""
        try:
            # Total responses
            query = "SELECT COUNT(*) as total FROM survey_responses"
            results = self.execute_query(query)
            total = results[0].get('total', 0) if results else 0
            
            # Responses summary
            query = """
            SELECT 
                COUNT(*) as submitted_count,
                COUNT(DISTINCT assignment_number) as unique_respondents
            FROM survey_responses
            """
            results = self.execute_query(query)
            
            return {
                'total_responses': total,
                'submitted_count': results[0].get('submitted_count', 0) if results else 0,
                'unique_respondents': results[0].get('unique_respondents', 0) if results else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting response stats: {e}")
            return {}


# Example usage
if __name__ == "__main__":
    # Example: Initialize connector
    connector = FabricLakehouseConnector(
        server="your-fabric-workspace.database.windows.net",
        database="Staff_survey_HDFT",
        username="your-username",
        password="your-password"
    )
    
    if connector.connect():
        # Get questions
        questions = connector.load_survey_questions()
        print(f"Loaded {len(questions)} questions")
        
        # Display first question
        if questions:
            print(f"\nFirst question:")
            print(questions[0])
        
        connector.disconnect()
