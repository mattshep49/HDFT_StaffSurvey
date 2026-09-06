"""
Fabric Table Schema Setup
Define and create required tables in Fabric Lakehouse for the survey application
"""


class SurveyTablesSchema:
    """Define table schemas for survey application"""
    
    # Survey Questions Table - Stores all survey questions
    SURVEY_QUESTIONS = {
        'table_name': 'survey_questions',
        'columns': {
            'question_id': 'STRING',  # e.g., 'q1', 'q2'
            'question_text': 'STRING',  # The actual question
            'question_type': 'STRING',  # 'likert', 'text', 'multiple_choice', 'yes_no'
            'category': 'STRING',  # Category/section (e.g., 'role satisfaction', 'management support')
            'scale': 'INT',  # For Likert: 5 for 5-point scale, etc.
            'options': 'STRING',  # JSON array for multiple choice options
            'is_required': 'BOOLEAN',  # Whether answer is mandatory
            'question_order': 'INT',  # Display order
            'is_active': 'BOOLEAN',  # Can be toggled for active/inactive questions
            'created_at': 'TIMESTAMP',
            'modified_at': 'TIMESTAMP'
        },
        'primary_key': 'question_id',
        'description': 'Stores all survey questions pulled from requirements'
    }
    
    # Survey Responses Table - Stores submitted survey responses
    SURVEY_RESPONSES = {
        'table_name': 'survey_responses',
        'columns': {
            'response_id': 'STRING',  # Unique identifier
            'token_id': 'INT',  # Reference to token
            'assignment_number': 'STRING',  # Staff assignment (Primary = 'Y')
            'staff_id': 'STRING',  # Employee ID
            'staff_name': 'STRING',  # Employee name
            'department': 'STRING',  # Department
            'responses_json': 'STRING',  # JSON object with all Q&A pairs
            'submitted_at': 'TIMESTAMP',  # Submission time
            'completion_time_seconds': 'INT',  # How long survey took
            'survey_version': 'INT',  # Version of survey answered
            'created_at': 'TIMESTAMP'
        },
        'primary_key': 'response_id',
        'description': 'Stores completed survey responses'
    }
    
    # Staff Assignments Table - Source data for token generation
    STAFF_ASSIGNMENTS = {
        'table_name': 'staff_assignments',
        'columns': {
            'assignment_number': 'STRING',  # Unique assignment ID
            'staff_id': 'STRING',  # Employee ID
            'staff_name': 'STRING',  # Employee name
            'department': 'STRING',  # Department name
            'job_title': 'STRING',  # Role/title
            'manager_id': 'STRING',  # Manager's employee ID
            'is_primary': 'BOOLEAN',  # Whether this is primary assignment (Y/N)
            'start_date': 'DATE',  # Assignment start date
            'end_date': 'DATE',  # Assignment end date (null if active)
            'is_active': 'BOOLEAN',  # Current active status
            'created_at': 'TIMESTAMP'
        },
        'primary_key': 'assignment_number',
        'description': 'Staff assignment data - source for token generation'
    }
    
    # Survey Tokens Table - Linking tokens to staff
    SURVEY_TOKENS = {
        'table_name': 'survey_tokens',
        'columns': {
            'token_id': 'INT',  # Auto-increment ID
            'token': 'STRING',  # The actual token (can be nullable for security)
            'token_hash': 'STRING',  # SHA-256 hash of token (for lookups)
            'assignment_number': 'STRING',  # Reference to assignment
            'staff_id': 'STRING',  # Employee ID
            'staff_name': 'STRING',  # Name
            'department': 'STRING',  # Department
            'survey_id': 'STRING',  # Which survey this token is for
            'created_at': 'TIMESTAMP',  # Token creation time
            'expires_at': 'TIMESTAMP',  # Expiry (usually 90 days)
            'first_accessed_at': 'TIMESTAMP',  # When survey first opened
            'completed_at': 'TIMESTAMP',  # Completion time
            'is_valid': 'BOOLEAN',  # Has token been invalidated?
            'response_id': 'STRING'  # FK to survey_responses
        },
        'primary_key': 'token_id',
        'indexes': ['token_hash', 'assignment_number', 'staff_id'],
        'description': 'Survey tokens linked to staff assignments'
    }
    
    # Survey Configuration Table - Track surveys and metadata
    SURVEY_CONFIG = {
        'table_name': 'survey_config',
        'columns': {
            'survey_id': 'STRING',  # Unique survey identifier
            'survey_title': 'STRING',  # Display title
            'survey_description': 'STRING',  # Description
            'survey_version': 'INT',  # Version number
            'is_active': 'BOOLEAN',  # Is this survey currently live?
            'start_date': 'TIMESTAMP',  # Survey opens
            'end_date': 'TIMESTAMP',  # Survey closes
            'estimated_completion_minutes': 'INT',  # How long survey takes
            'created_by': 'STRING',  # Who created it
            'created_at': 'TIMESTAMP',
            'modified_at': 'TIMESTAMP'
        },
        'primary_key': 'survey_id',
        'description': 'Survey configuration and metadata'
    }


# SQL CREATE TABLE statements for Fabric/SQL
CREATE_TABLE_STATEMENTS = {
    'survey_questions': """
        CREATE TABLE IF NOT EXISTS survey_questions (
            question_id STRING NOT NULL,
            question_text STRING NOT NULL,
            question_type STRING,
            category STRING,
            scale INT,
            options STRING,
            is_required BOOLEAN DEFAULT true,
            question_order INT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (question_id)
        )
        COMMENT 'Survey questions stored in Fabric Lakehouse'
    """,
    
    'survey_responses': """
        CREATE TABLE IF NOT EXISTS survey_responses (
            response_id STRING NOT NULL,
            token_id INT,
            assignment_number STRING NOT NULL,
            staff_id STRING,
            staff_name STRING,
            department STRING,
            responses_json STRING,
            submitted_at TIMESTAMP,
            completion_time_seconds INT,
            survey_version INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (response_id)
        )
        COMMENT 'Survey responses from completed surveys'
    """,
    
    'staff_assignments': """
        CREATE TABLE IF NOT EXISTS staff_assignments (
            assignment_number STRING NOT NULL,
            staff_id STRING NOT NULL,
            staff_name STRING,
            department STRING,
            job_title STRING,
            manager_id STRING,
            is_primary BOOLEAN DEFAULT true,
            start_date DATE,
            end_date DATE,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (assignment_number)
        )
        COMMENT 'Staff assignment data - Source for survey participants'
    """,
    
    'survey_tokens': """
        CREATE TABLE IF NOT EXISTS survey_tokens (
            token_id INT AUTO_INCREMENT,
            token STRING,
            token_hash STRING NOT NULL UNIQUE,
            assignment_number STRING NOT NULL,
            staff_id STRING,
            staff_name STRING,
            department STRING,
            survey_id STRING,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            first_accessed_at TIMESTAMP,
            completed_at TIMESTAMP,
            is_valid BOOLEAN DEFAULT true,
            response_id STRING,
            PRIMARY KEY (token_id),
            FOREIGN KEY (assignment_number) REFERENCES staff_assignments(assignment_number),
            FOREIGN KEY (response_id) REFERENCES survey_responses(response_id),
            INDEX idx_token_hash (token_hash),
            INDEX idx_assignment (assignment_number),
            INDEX idx_staff_id (staff_id)
        )
        COMMENT 'Survey tokens linked to staff assignments'
    """,
    
    'survey_config': """
        CREATE TABLE IF NOT EXISTS survey_config (
            survey_id STRING NOT NULL,
            survey_title STRING NOT NULL,
            survey_description STRING,
            survey_version INT DEFAULT 1,
            is_active BOOLEAN DEFAULT true,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            estimated_completion_minutes INT,
            created_by STRING,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (survey_id)
        )
        COMMENT 'Survey configuration and metadata'
    """
}


if __name__ == "__main__":
    print("Survey Table Schemas Defined")
    print("\nTables:")
    for name, config in [
        ("survey_questions", SurveyTablesSchema.SURVEY_QUESTIONS),
        ("survey_responses", SurveyTablesSchema.SURVEY_RESPONSES),
        ("staff_assignments", SurveyTablesSchema.STAFF_ASSIGNMENTS),
        ("survey_tokens", SurveyTablesSchema.SURVEY_TOKENS),
        ("survey_config", SurveyTablesSchema.SURVEY_CONFIG)
    ]:
        print(f"\n{name}:")
        print(f"  Description: {config['description']}")
        print(f"  Primary Key: {config['primary_key']}")
        print(f"  Columns: {len(config['columns'])}")
        for col, dtype in config['columns'].items():
            print(f"    - {col}: {dtype}")
