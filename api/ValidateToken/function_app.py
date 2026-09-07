import azure.functions as func
import json
import logging
from app.token_manager import TokenManager

# Initialize token manager
token_manager = TokenManager('data/tokens.db')

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
    
    is_valid, token_data = token_manager.validate_token(token)
    
    if not is_valid:
        return func.HttpResponse(
            json.dumps({'error': 'Invalid or expired token'}),
            status_code=401,
            mimetype="application/json"
        )
    
    return func.HttpResponse(
        json.dumps({
            'valid': True,
            'data': token_data
        }),
        status_code=200,
        mimetype="application/json"
    )
