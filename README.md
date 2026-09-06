# HDFT Staff Survey Application

## Overview
This is an internal staff survey application that:
- Identifies staff members from assignment data where **Primary = 'Y'**
- Generates unique survey tokens for each eligible staff member
- Provides a secure URL-based survey interface
- Collects and tracks survey responses

## Architecture

### Components
1. **Backend** - Data processing and token generation (Fabric Notebook)
2. **Frontend** - Web interface for survey completion (Flask/HTML)
3. **Database** - Response storage and token validation (Azure SQL / Lakehouse)
4. **App** - Main application logic

### Key Features
- ✅ Assignment-based staff identification
- ✅ Primary assignment filtering
- ✅ Unique token generation per staff member
- ✅ URL-based survey access with token validation
- ✅ Response tracking and analytics
- ✅ Admin dashboard for monitoring

## File Structure
```
HDFT_StaffSurvey/
├── backend/          # Data processing notebooks
│   ├── 01_prepare_staff_data.py
│   └── 02_generate_tokens.py
├── frontend/         # Web application
│   ├── app.py
│   ├── templates/
│   └── static/
├── database/         # Schema and migrations
│   └── schema.sql
├── app/              # Configuration and utilities
│   ├── config.py
│   └── token_manager.py
└── README.md
```

## Getting Started

### 1. Prepare Survey Questions
- Load questions from Excel file (`Scoping survey qus list.xlsx`)
- Transform to structured table format in Fabric Lakehouse
- Ensure table name is `survey_questions` with columns:
  - `question_id`: Unique question identifier
  - `question_text`: Full question text
  - `answer_type`: likert, multiple_choice, text, textarea
  - `answer_options`: JSON array of options
  - `is_required`: Boolean (1/0)
  - `section`: Question category
  - `sequence`: Display order
  - `is_active`: Boolean (1/0)

### 2. Configure Environment
Set environment variables in Azure Static Web App or local `.env`:
```
FABRIC_SQL_SERVER=your-workspace.database.windows.net
FABRIC_LAKEHOUSE_NAME=Staff_survey_HDFT
FABRIC_SQL_USER=your-username
FABRIC_SQL_PASSWORD=your-password
```

### 3. Generate Staff Tokens
Use the Fabric notebook to:
1. Filter assignments where `Primary = 'Y'`
2. Generate unique tokens for each staff member
3. Store in `survey_tokens` table with columns:
   - `token`: Unique URL-safe token
   - `assignment_number`: Staff assignment ID
   - `staff_id`: Employee ID
   - `staff_name`: Employee name
   - `department`: Department
   - `created_at`: Timestamp
   - `expires_at`: Expiration date
   - `is_valid`: Status flag

### 4. Send Personalized Survey URLs
Generate individualized URLs for each staff member:
```
https://your-survey-app.azurestaticapps.net/?token=abc123xyz...
```

Each URL is unique to the staff member and contains their token in the query parameter.

### 5. Deploy to Azure Static Web App
```bash
az staticwebapp create --name hdft-staff-survey \
  --resource-group your-rg \
  --location eastus \
  --source https://github.com/your-repo/HDFT_StaffSurvey \
  --branch main
```

## Deployment Architecture
- **Frontend**: Azure Static Web App (HTML/CSS/JS)
- **Backend**: Azure Functions (Token validation, question loading, response submission)
- **Data**: Fabric Lakehouse with SQL endpoint
- **Security**: HTTPS, token validation, CORS restrictions

## URL Token Flow
1. Staff receives personalized email with unique survey URL
2. URL contains `?token=xxxxx` parameter
3. Browser automatically validates token against Fabric Lakehouse
4. If valid → loads survey questions
5. If invalid/expired → shows error message
6. Survey response submitted → token marked as used
7. Same token cannot be reused

## Response Data
Survey responses are stored in `survey_responses` table:
- `token_id`: Reference to token
- `assignment_number`: Staff assignment
- `staff_id`: Employee ID
- `response_data`: JSON with all answers
- `submitted_at`: Submission timestamp
