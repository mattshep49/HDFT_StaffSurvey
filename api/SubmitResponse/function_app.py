import azure.functions as func
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.onelake_connector import OneLakeConnector


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Submit survey responses — POST /api/submit-response
    Body: {token: string, responses: object}
    """
    logging.info('SubmitResponse function triggered')

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({'error': 'Invalid request body'}),
            status_code=400, mimetype='application/json'
        )

    token = req_body.get('token')
    responses = req_body.get('responses')

    if not token or not responses:
        return func.HttpResponse(
            json.dumps({'error': 'Token and responses are required'}),
            status_code=400, mimetype='application/json'
        )

    connector = OneLakeConnector()

    # Resolve token data
    if token == 'test':
        token_data = {
            'token_id': 1,
            'assignment_number': 'TEST-001',
            'staff_id': 'test-staff',
            'staff_name': 'Test User',
            'department': 'Testing'
        }
        if not connector.is_configured():
            # Dev / local mode — log and return success without writing
            logging.info(f'[DEV] Test submission accepted: {len(responses)} responses')
            return func.HttpResponse(
                json.dumps({'success': True, 'message': 'Thank you (dev mode)', 'response_id': 'dev-test'}),
                status_code=200, mimetype='application/json'
            )
    else:
        if not connector.is_configured():
            return func.HttpResponse(
                json.dumps({'error': 'Service not configured — contact support'}),
                status_code=503, mimetype='application/json'
            )
        token_data = connector.validate_token(token)
        if not token_data:
            return func.HttpResponse(
                json.dumps({'error': 'Invalid or expired token'}),
                status_code=401, mimetype='application/json'
            )

    try:
        filename = connector.save_survey_response(
            assignment_number=token_data.get('assignment_number', 'UNKNOWN'),
            staff_id=token_data.get('staff_id', ''),
            responses=responses,
            token_id=token_data.get('token_id')
        )
        logging.info(f"Response saved: {filename}")
        return func.HttpResponse(
            json.dumps({'success': True, 'message': 'Thank you for completing the survey', 'response_id': filename}),
            status_code=200, mimetype='application/json'
        )
    except Exception as e:
        logging.error(f'Error saving response: {e}')
        return func.HttpResponse(
            json.dumps({'error': f'Failed to save response: {str(e)}'}),
            status_code=500, mimetype='application/json'
        )
