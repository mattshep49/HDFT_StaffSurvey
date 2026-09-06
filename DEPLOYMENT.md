# HDFT Staff Survey - Azure Static Web App Deployment Guide

## Overview
This guide covers deploying the HDFT Staff Survey as an Azure Static Web App with Azure Functions backend connected to Fabric Lakehouse.

## Prerequisites
- Azure subscription
- GitHub repository access
- Fabric Lakehouse with survey questions table
- Azure CLI installed locally

## Architecture

```
┌─────────────────────────────────────────┐
│  Azure Static Web App                   │
│  ├─ Frontend (HTML/CSS/JS)              │
│  └─ API Functions (/api/*)              │
└────────────┬────────────────────────────┘
             │
             ├─→ Fabric Lakehouse (SQL Endpoint)
             │   ├─ survey_questions
             │   ├─ survey_tokens  
             │   └─ survey_responses
             │
             └─→ User browsers (HTTPS only)
```

## Step 1: Prepare Fabric Lakehouse Tables

### Create survey_questions table
```sql
CREATE TABLE survey_questions (
    question_id NVARCHAR(50) PRIMARY KEY,
    question_text NVARCHAR(MAX) NOT NULL,
    answer_type NVARCHAR(50),  -- likert, multiple_choice, text, textarea
    answer_options NVARCHAR(MAX),  -- JSON array
    is_required BIT DEFAULT 1,
    section NVARCHAR(100),
    sequence INT,
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE()
);
```

### Create survey_tokens table
```sql
CREATE TABLE survey_tokens (
    id INT PRIMARY KEY IDENTITY(1,1),
    token NVARCHAR(MAX) UNIQUE NOT NULL,
    token_hash NVARCHAR(64) UNIQUE NOT NULL,
    assignment_number NVARCHAR(50) UNIQUE NOT NULL,
    staff_id NVARCHAR(50),
    staff_name NVARCHAR(200),
    department NVARCHAR(100),
    created_at DATETIME DEFAULT GETDATE(),
    expires_at DATETIME,
    used_at DATETIME NULL,
    is_valid BIT DEFAULT 1,
    response_id INT NULL
);

CREATE INDEX idx_token_hash ON survey_tokens(token_hash);
CREATE INDEX idx_assignment ON survey_tokens(assignment_number);
```

### Create survey_responses table
```sql
CREATE TABLE survey_responses (
    id INT PRIMARY KEY IDENTITY(1,1),
    token_id INT NOT NULL,
    assignment_number NVARCHAR(50),
    staff_id NVARCHAR(50),
    response_data NVARCHAR(MAX),  -- JSON responses
    submitted_at DATETIME DEFAULT GETDATE(),
    completion_time_seconds INT NULL,
    FOREIGN KEY(token_id) REFERENCES survey_tokens(id)
);

CREATE INDEX idx_response_token ON survey_responses(token_id);
```

## Step 2: Deploy to Azure Static Web App

### Option A: Via Azure Portal
1. Go to Azure Portal → Create resource → Static Web App
2. Configure:
   - **Name**: hdft-staff-survey
   - **Region**: UK South
   - **Deployment details**: GitHub (or manually)
3. Connect GitHub repository
4. Build presets: Custom
5. Build properties:
   - App location: `public/`
   - API location: `api/`

### Option B: Via Azure CLI
```bash
# Create resource group
az group create --name hdft-survey-rg --location uksouth

# Create Static Web App
az staticwebapp create \
  --name hdft-staff-survey \
  --resource-group hdft-survey-rg \
  --location uksouth \
  --source https://github.com/YOUR-ORG/HDFT_StaffSurvey \
  --branch main \
  --app-location public \
  --api-location api \
  --output-location public
```

## Step 3: Configure Environment Variables

### In Azure Portal
1. Static Web App → Settings → Configuration
2. Add application settings:

```
FABRIC_SQL_SERVER=your-workspace.database.windows.net
FABRIC_LAKEHOUSE_NAME=Staff_survey_HDFT
FABRIC_SQL_USER=survey-app-user
FABRIC_SQL_PASSWORD=<secure-password>
```

### Local Development (.env file)
```
FABRIC_SQL_SERVER=your-workspace.database.windows.net
FABRIC_LAKEHOUSE_NAME=Staff_survey_HDFT
FABRIC_SQL_USER=survey-app-user
FABRIC_SQL_PASSWORD=<password>
AZURE_FUNCTIONS_ENVIRONMENT=Development
```

## Step 4: Generate and Distribute Survey Tokens

### Generate Tokens
```bash
cd backend

# Use the generate_survey_tokens.py script
python generate_survey_tokens.py

# This creates:
# - output/survey_tokens.json (for Lakehouse bulk insert)
# - output/survey_urls.csv (for email distribution)
```

### Load Tokens to Lakehouse
```sql
-- Bulk insert from JSON (using Python script output)
EXEC sp_executesql N'
INSERT INTO survey_tokens (token, token_hash, assignment_number, staff_id, 
                          staff_name, department, created_at, expires_at, is_valid)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)'
```

### Send Survey Emails
Use your email service to send personalized URLs:
- Each staff member gets unique URL: `https://survey.hdft.nhs.uk/?token=ABC123XYZ...`
- Include survey deadline
- Provide support contact for technical issues

## Step 5: Monitor and Track Responses

### Check Response Statistics
```sql
SELECT 
    COUNT(*) as total_tokens,
    SUM(CASE WHEN used_at IS NOT NULL THEN 1 ELSE 0 END) as submitted,
    SUM(CASE WHEN used_at IS NULL AND expires_at > GETDATE() THEN 1 ELSE 0 END) as pending,
    ROUND(SUM(CASE WHEN used_at IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as submission_rate
FROM survey_tokens;
```

### View Responses
```sql
SELECT 
    sr.staff_id,
    st.staff_name,
    st.department,
    sr.submitted_at,
    sr.response_data
FROM survey_responses sr
JOIN survey_tokens st ON sr.token_id = st.id
ORDER BY sr.submitted_at DESC;
```

### Export for Analysis
```sql
-- Export responses as CSV
SELECT 
    st.staff_id,
    st.staff_name,
    st.department,
    sr.response_data,
    sr.submitted_at
INTO #temp_responses
FROM survey_responses sr
JOIN survey_tokens st ON sr.token_id = st.id;

-- Then export #temp_responses to CSV
```

## Security Considerations

### SSL/HTTPS
- Azure Static Web App provides automatic HTTPS
- All traffic encrypted in transit

### Token Security
- Tokens are 32-character cryptographically random strings
- Stored as SHA256 hashes in database (plain tokens never stored)
- Each token expires after 90 days
- Tokens become invalid after first use

### Data Protection
- Responses stored in Fabric Lakehouse (Microsoft data centers)
- Configure Lakehouse encryption at rest
- Implement row-level security if needed
- Regular backups of Lakehouse

### CORS and API Security
- API endpoints restricted to Static Web App domain
- CORS headers configured in staticwebapp.config.json
- No API keys exposed in frontend code

## Troubleshooting

### Issue: "Invalid token" error
**Solution**: 
- Verify token is in database with correct hash
- Check token hasn't expired
- Ensure SQL connection string is correct

### Issue: "Cannot connect to Lakehouse"
**Solution**:
- Verify credentials in environment variables
- Check SQL Server firewall allows Azure connections
- Test connection with Azure Data Studio

### Issue: Survey loads but questions don't appear
**Solution**:
- Verify survey_questions table has data
- Check is_active = 1 for questions
- Verify answer_options is valid JSON

## Performance Optimization

### Cache Survey Questions
```javascript
// In app.js, add caching:
if (localStorage.getItem('surveyQuestions')) {
    this.questions = JSON.parse(localStorage.getItem('surveyQuestions'));
} else {
    // Fetch from API and cache
}
```

### Compress API Responses
- Enable gzip compression in Azure Static Web App
- Responses typically compress to <20% of original size

### CDN Configuration
- Azure Static Web App includes integrated CDN
- Static assets cached globally by default

## Maintenance

### Invalidate Expired Tokens
```bash
# Schedule monthly job
az sql db execute-sql --resource-group hdft-survey-rg \
  --database-name survey_db \
  --query "UPDATE survey_tokens SET is_valid = 0 WHERE expires_at < GETDATE()"
```

### Archive Old Responses
```sql
-- Archive responses older than 1 year
INSERT INTO survey_responses_archive
SELECT * FROM survey_responses
WHERE submitted_at < DATEADD(YEAR, -1, GETDATE());

DELETE FROM survey_responses
WHERE submitted_at < DATEADD(YEAR, -1, GETDATE());
```

## Support and Escalation

For issues:
1. Check Static Web App diagnostics: Settings → Logs
2. Review Function App logs: Monitor → Logs
3. Check Fabric Lakehouse query history
4. Contact Microsoft Support if Azure infrastructure issues

---

**Last Updated**: September 2024  
**Contact**: Digital Opportunities Team @ HDFT
