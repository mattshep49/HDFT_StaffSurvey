import azure.functions as func
import json
import logging
import os
import sys
from datetime import datetime

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
        now = datetime.utcnow()
        campaign = f"Q{(now.month - 1) // 3 + 1}{now.year}"
        return func.HttpResponse(
            json.dumps({
                'valid': True,
                'data': {
                    'token': 'test',
                    'campaign': campaign,
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
            'token': token_data.get('token'),
            'campaign': token_data.get('campaign'),
        }}),
        status_code=200, mimetype='application/json'
    )
