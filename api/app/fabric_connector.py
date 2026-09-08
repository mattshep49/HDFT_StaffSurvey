"""
Fabric Lakehouse Connector
Reads survey questions and responses from Fabric Lakehouse tables
"""

import json
import logging
import os
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class FabricLakehouseConnector:
    """Connects to Fabric Lakehouse using SQL endpoint"""

    def __init__(self, server: str = None, database: str = None,
                 username: str = None, password: str = None, tenant_id: str = None):
        self.server = server or os.getenv('FABRIC_SQL_SERVER')
        self.database = database or os.getenv('FABRIC_LAKEHOUSE_NAME')
        self.username = username or os.getenv('FABRIC_SQL_USER')
        self.password = password or os.getenv('FABRIC_SQL_PASSWORD')
        self.tenant_id = tenant_id or os.getenv('FABRIC_TENANT_ID')
        self.connection = None
        self._import_pyodbc()

    def _import_pyodbc(self):
        try:
            import pyodbc
            self.pyodbc = pyodbc
        except ImportError:
            logger.warning("pyodbc not installed")
            self.pyodbc = None

    def connect(self) -> bool:
        try:
            if not self.pyodbc:
                logger.error("pyodbc not available")
                return False

            if self.tenant_id:
                connection_string = (
                    f'Driver={{ODBC Driver 17 for SQL Server}};'
                    f'Server={self.server},1433;'
                    f'Database={self.database};'
                    f'UID={self.username};'
                    f'PWD={self.password};'
                    f'Authentication=ActiveDirectoryServicePrincipal;'
                    f'Encrypt=yes;'
                    f'TrustServerCertificate=no;'
                    f'Connection Timeout=30;'
                )
            else:
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
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        try:
            if not self.connection:
                logger.error("Not connected to Lakehouse")
                return []

            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def load_survey_questions(self, table_name: str = 'survey_questions') -> List[Dict]:
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
            sequence,
            parent_question_id,
            show_if_answer,
            branch_type,
            created_at,
            is_active
        FROM {table_name}
        WHERE is_active = 1
        ORDER BY sequence ASC
        """

        questions = self.execute_query(query)

        for q in questions:
            if q.get('answer_options') and isinstance(q['answer_options'], str):
                try:
                    q['answer_options'] = json.loads(q['answer_options'])
                except Exception:
                    q['answer_options'] = []

        logger.info(f"Loaded {len(questions)} survey questions from {table_name}")
        return questions

    def save_survey_response(self, token_id: int, assignment_number: str,
                             staff_id: str, responses: Dict) -> int:
        try:
            if not self.connection:
                logger.error("Not connected to Lakehouse")
                return 0

            cursor = self.connection.cursor()
            response_json = json.dumps(responses)
            submitted_at = datetime.now().isoformat()

            insert_query = """
            INSERT INTO survey_responses
            (token_id, assignment_number, staff_id, response_data, submitted_at)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (token_id, assignment_number, staff_id, response_json, submitted_at))
            cursor.execute("SELECT SCOPE_IDENTITY()")
            response_id = cursor.fetchone()[0]
            cursor.close()

            logger.info(f"Response saved for assignment {assignment_number}")
            return int(response_id)

        except Exception as e:
            logger.error(f"Error saving response: {e}")
            return 0

    def get_response_stats(self) -> Dict:
        try:
            results = self.execute_query(
                "SELECT COUNT(*) as total, "
                "COUNT(DISTINCT assignment_number) as unique_respondents "
                "FROM survey_responses"
            )
            row = results[0] if results else {}
            return {
                'total_responses': row.get('total', 0),
                'unique_respondents': row.get('unique_respondents', 0)
            }
        except Exception as e:
            logger.error(f"Error getting response stats: {e}")
            return {}
