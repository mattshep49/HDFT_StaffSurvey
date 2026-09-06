"""
Configuration module for HDFT Staff Survey Application
"""

import os
from datetime import datetime, timedelta

class Config:
    """Application configuration"""
    
    # App settings
    APP_NAME = "HDFT Staff Survey"
    SECRET_KEY = os.getenv('SURVEY_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', False)
    
    # Database settings
    DATABASE_TYPE = os.getenv('DB_TYPE', 'azure_sql')  # 'azure_sql' or 'lakehouse'
    DATABASE_SERVER = os.getenv('DB_SERVER', 'your-server.database.windows.net')
    DATABASE_NAME = os.getenv('DB_NAME', 'hdft_survey')
    DATABASE_USER = os.getenv('DB_USER', '')
    DATABASE_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Lakehouse settings (if using Fabric Lakehouse)
    LAKEHOUSE_WORKSPACE_ID = os.getenv('LAKEHOUSE_WORKSPACE_ID', '')
    LAKEHOUSE_ID = os.getenv('LAKEHOUSE_ID', '')
    FABRIC_ACCESS_TOKEN = os.getenv('FABRIC_ACCESS_TOKEN', '')
    
    # Fabric table names
    FABRIC_SURVEY_QUESTIONS_TABLE = 'survey_questions'
    FABRIC_SURVEY_RESPONSES_TABLE = 'survey_responses'
    FABRIC_STAFF_ASSIGNMENTS_TABLE = 'staff_assignments'
    FABRIC_SURVEY_CONFIG_TABLE = 'survey_config'
    
    # Token settings
    TOKEN_LENGTH = 32  # Length of unique tokens
    TOKEN_EXPIRY_DAYS = 90  # Tokens expire after 90 days
    
    # Survey settings
    SURVEY_OPEN = True  # Can be toggled to close survey
    SURVEY_TITLE = "HDFT Staff Survey 2024"
    SURVEY_DESCRIPTION = "We value your feedback. This survey takes approximately 10-15 minutes."
    
    # API settings
    API_TIMEOUT = 30
    MAX_RETRIES = 3
    
    @staticmethod
    def get_token_expiry():
        """Calculate token expiry datetime"""
        return datetime.now() + timedelta(days=Config.TOKEN_EXPIRY_DAYS)
    
    @staticmethod
    def get_database_connection_string():
        """Build database connection string"""
        if Config.DATABASE_TYPE == 'azure_sql':
            return (
                f"Server=tcp:{Config.DATABASE_SERVER},1433;Initial Catalog={Config.DATABASE_NAME};"
                f"Persist Security Info=False;User ID={Config.DATABASE_USER};"
                f"Password={Config.DATABASE_PASSWORD};Encrypt=True;Connection Timeout=30;"
            )
        return None
