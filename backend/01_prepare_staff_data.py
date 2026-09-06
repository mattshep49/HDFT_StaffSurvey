"""
Backend Data Preparation Notebook
Prepares staff assignment data and generates survey tokens
This script should be run as a Fabric Notebook
"""

# ============================================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================================

from notebookutils import mssparkutils
import pandas as pd
import datetime
import json
import secrets
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 2. CONFIGURATION
# ============================================================================

# Lakehouse configuration
WORKSPACE_ID = mssparkutils.notebook.getContext().notebookPath.split('/')[2]
LAKEHOUSE_ID = mssparkutils.notebook.getContext().notebookPath.split('/')[3]

# Table names
SOURCE_TABLE = "staff_assignments"  # Your source assignment table
SURVEY_QUESTIONS_TABLE = "survey_questions"
SURVEY_TOKENS_TABLE = "survey_tokens"
SURVEY_RESPONSES_TABLE = "survey_responses"
SURVEY_CONFIG_TABLE = "survey_config"

# Token configuration
TOKEN_LENGTH = 32
TOKEN_EXPIRY_DAYS = 90
SURVEY_ID = "2024-q3-staff-survey"

print(f"Configuration Loaded")
print(f"  Workspace: {WORKSPACE_ID}")
print(f"  Lakehouse: {LAKEHOUSE_ID}")
print(f"  Survey ID: {SURVEY_ID}")

# ============================================================================
# 3. LOAD SOURCE DATA - STAFF ASSIGNMENTS WHERE PRIMARY = 'Y'
# ============================================================================

print("\n" + "="*80)
print("STEP 1: Loading Staff Assignments (Primary = 'Y')")
print("="*80)

# Query for primary assignments
query_primary_assignments = f"""
SELECT 
    assignment_number,
    staff_id,
    staff_name,
    department,
    job_title,
    manager_id,
    is_primary,
    is_active,
    start_date,
    end_date
FROM {SOURCE_TABLE}
WHERE is_primary = 1 AND is_active = 1
ORDER BY staff_id, assignment_number
"""

df_assignments = spark.sql(query_primary_assignments).toPandas()

print(f"\nLoaded {len(df_assignments)} active primary assignments")
print(f"\nSample assignments:")
print(df_assignments.head(10).to_string())

if len(df_assignments) == 0:
    print("WARNING: No primary assignments found. Check source data.")

# ============================================================================
# 4. GENERATE TOKENS
# ============================================================================

print("\n" + "="*80)
print("STEP 2: Generating Survey Tokens")
print("="*80)

def generate_token():
    """Generate a secure token"""
    return secrets.token_urlsafe(TOKEN_LENGTH)

def hash_token(token):
    """Hash token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()

# Add token columns
tokens = []
token_hashes = []
created_times = []
expiry_times = []

for idx, row in df_assignments.iterrows():
    token = generate_token()
    token_hash = hash_token(token)
    created_at = datetime.datetime.now()
    expires_at = created_at + datetime.timedelta(days=TOKEN_EXPIRY_DAYS)
    
    tokens.append(token)
    token_hashes.append(token_hash)
    created_times.append(created_at)
    expiry_times.append(expires_at)

df_assignments['token'] = tokens
df_assignments['token_hash'] = token_hashes
df_assignments['created_at'] = created_times
df_assignments['expires_at'] = expiry_times
df_assignments['survey_id'] = SURVEY_ID
df_assignments['is_valid'] = True
df_assignments['first_accessed_at'] = None
df_assignments['completed_at'] = None
df_assignments['response_id'] = None

print(f"Generated {len(tokens)} tokens")
print(f"\nSample tokens:")
print(df_assignments[['staff_id', 'staff_name', 'token', 'expires_at']].head(5).to_string())

# ============================================================================
# 5. SAVE TOKENS TO LAKEHOUSE
# ============================================================================

print("\n" + "="*80)
print("STEP 3: Saving Tokens to Lakehouse")
print("="*80)

# Prepare token dataframe for storage
df_tokens_save = df_assignments[[
    'token', 'token_hash', 'assignment_number', 'staff_id', 'staff_name',
    'department', 'survey_id', 'created_at', 'expires_at', 'is_valid', 'response_id'
]].copy()

# Convert to Spark DataFrame and save
spark_df_tokens = spark.createDataFrame(df_tokens_save)
spark_df_tokens.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(SURVEY_TOKENS_TABLE)

print(f"Saved {len(df_tokens_save)} tokens to {SURVEY_TOKENS_TABLE}")

# ============================================================================
# 6. LOAD SURVEY QUESTIONS FROM REQUIREMENTS
# ============================================================================

print("\n" + "="*80)
print("STEP 4: Loading Survey Questions")
print("="*80)

# Check if survey_questions table exists
try:
    df_questions = spark.sql(f"SELECT * FROM {SURVEY_QUESTIONS_TABLE}").toPandas()
    print(f"Loaded {len(df_questions)} questions from {SURVEY_QUESTIONS_TABLE}")
    print("\nQuestions:")
    print(df_questions[['question_id', 'question_text', 'question_type']].to_string())
except Exception as e:
    print(f"Warning: Could not load questions - {e}")
    print("You need to populate the survey_questions table separately")

# ============================================================================
# 7. CREATE SURVEY CONFIGURATION RECORD
# ============================================================================

print("\n" + "="*80)
print("STEP 5: Creating Survey Configuration")
print("="*80)

survey_config_record = {
    'survey_id': [SURVEY_ID],
    'survey_title': ['HDFT Staff Survey Q3 2024'],
    'survey_description': ['Internal staff feedback survey'],
    'survey_version': [1],
    'is_active': [True],
    'start_date': [datetime.datetime.now()],
    'end_date': [datetime.datetime.now() + datetime.timedelta(days=90)],
    'estimated_completion_minutes': [15],
    'created_by': ['system'],
    'created_at': [datetime.datetime.now()],
    'modified_at': [datetime.datetime.now()]
}

df_config = pd.DataFrame(survey_config_record)
spark_df_config = spark.createDataFrame(df_config)

try:
    spark_df_config.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(SURVEY_CONFIG_TABLE)
    print(f"Survey configuration saved for {SURVEY_ID}")
except Exception as e:
    print(f"Note: Survey config may already exist - {e}")

# ============================================================================
# 8. GENERATE URL TOKENS FOR DISTRIBUTION
# ============================================================================

print("\n" + "="*80)
print("STEP 6: Generating Survey URLs")
print("="*80)

BASE_URL = "https://your-survey-domain.com/survey"

survey_urls = []
for idx, row in df_assignments.iterrows():
    url = f"{BASE_URL}?token={row['token']}"
    survey_urls.append({
        'staff_id': row['staff_id'],
        'staff_name': row['staff_name'],
        'email_address': f"{row['staff_id']}@hdft.nhs.uk",  # Adjust domain as needed
        'survey_url': url,
        'expires_at': row['expires_at'],
        'token': row['token']
    })

df_urls = pd.DataFrame(survey_urls)

# Display sample URLs
print(f"\nGenerated {len(df_urls)} survey URLs")
print("\nSample URLs (DO NOT SHARE IN LOGS - for reference only):")
for idx in range(min(3, len(df_urls))):
    print(f"  Staff: {df_urls.iloc[idx]['staff_name']}")
    print(f"  URL: {BASE_URL}?token=<token_{idx}>")

# Save URLs to a CSV for distribution (SECURE THIS FILE)
urls_file = f"/tmp/survey_urls_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
df_urls.to_csv(urls_file, index=False)
print(f"\nURL distribution file saved to: {urls_file}")
print("⚠️  SECURITY: This file contains sensitive URLs - store securely and delete after distribution")

# ============================================================================
# 9. SUMMARY STATISTICS
# ============================================================================

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print(f"""
Survey Setup Complete:
  Survey ID: {SURVEY_ID}
  Total Tokens Generated: {len(df_tokens_save)}
  Token Expiry: {TOKEN_EXPIRY_DAYS} days
  
Tables Created/Updated:
  - {SURVEY_TOKENS_TABLE}: {len(df_tokens_save)} records
  - {SURVEY_CONFIG_TABLE}: Survey configuration
  
Next Steps:
  1. Verify survey questions in {SURVEY_QUESTIONS_TABLE}
  2. Distribute survey URLs to staff members
  3. Monitor responses in {SURVEY_RESPONSES_TABLE}
  4. Generate analytics reports

Note: All tokens expire on: {expiry_times[0] + datetime.timedelta(days=TOKEN_EXPIRY_DAYS)}
""")

print("\nBackend Data Preparation Complete! ✓")
