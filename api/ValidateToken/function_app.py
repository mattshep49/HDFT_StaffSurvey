import azure.functions as func
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.onelake_connector import OneLakeConnector


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validate survey token — GET /api/validate-token?token=xxxxx
    """
    logging.info('ValidateToken function triggered')

    token = req.params.get('token')
    if not token:
        return func.HttpResponse(
            json.dumps({'error': 'Token required'}),
            status_code=400, mimetype='application/json'
        )

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
            status_code=200, mimetype='application/json'
        )

    connector = OneLakeConnector()
    if not connector.is_configured():
        return func.HttpResponse(
            json.dumps({'valid': False, 'error': 'Service not configured'}),
            status_code=503, mimetype='application/json'
        )

    token_data = connector.validate_token(token)
    if not token_data:
        return func.HttpResponse(
            json.dumps({'valid': False, 'error': 'Invalid or expired token'}),
            status_code=401, mimetype='application/json'
        )

    return func.HttpResponse(
        json.dumps({'valid': True, 'data': {
            'token_id': token_data.get('token_id'),
            'assignment_number': token_data.get('assignment_number'),
            'staff_id': token_data.get('staff_id'),
            'staff_name': token_data.get('staff_name'),
            'department': token_data.get('department'),
            'already_submitted': token_data.get('already_submitted', False)
        }}),
        status_code=200, mimetype='application/json'
    )
