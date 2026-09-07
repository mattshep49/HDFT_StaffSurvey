import azure.functions as func
import json
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validate survey token and return staff information
    GET /api/validate-token?token=xxxxx
    """
    logging.info('ValidateToken function triggered')
    
    token = req.params.get('token')
    
    if not token:
        return func.HttpResponse(
            json.dumps({'error': 'Token required'}),
            status_code=400,
            mimetype="application/json"
        )
    
    # Allow test token for development/testing
    if token == 'test':
        return func.HttpResponse(
            json.dumps({
                'valid': True,
                'data': {
                    'token_id': 1,
                    'assignment_number': 'TEST-001',
                    'staff_id': 'test-staff',
                    'staff_name': 'Test User',
                    'department': 'Testing',
                    'already_submitted': False
                }
            }),
            status_code=200,
            mimetype="application/json"
        )
    
    # For non-test tokens, reject for now (token database not implemented yet)
    # In production, validate against survey_tokens table in Fabric
    return func.HttpResponse(
        json.dumps({'error': 'Invalid or expired token. Use token=test for development.'}),
        status_code=401,
        mimetype="application/json"
    )
