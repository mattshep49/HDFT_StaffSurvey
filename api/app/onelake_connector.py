import json
import logging
import os

import msal
import requests

logger = logging.getLogger(__name__)

_ONELAKE_DFS = "https://onelake.dfs.fabric.microsoft.com"
_STORAGE_SCOPE = ["https://storage.azure.com/.default"]


class OneLakeConnector:
    """Reads files from Fabric Lakehouse via OneLake DFS REST API — no ODBC needed."""

    def __init__(self):
        self.workspace_id = os.getenv('FABRIC_WORKSPACE_ID')
        self.lakehouse_name = os.getenv('FABRIC_LAKEHOUSE_NAME')
        self.client_id = os.getenv('FABRIC_SQL_USER')
        self.client_secret = os.getenv('FABRIC_SQL_PASSWORD')
        self.tenant_id = os.getenv('FABRIC_TENANT_ID')

    def is_configured(self) -> bool:
        return all([self.workspace_id, self.lakehouse_name,
                    self.client_id, self.client_secret, self.tenant_id])

    def _get_token(self) -> str:
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            self.client_id,
            client_credential=self.client_secret,
            authority=authority
        )
        result = app.acquire_token_for_client(scopes=_STORAGE_SCOPE)
        if 'access_token' not in result:
            raise RuntimeError(result.get('error_description') or str(result))
        return result['access_token']

    def load_json_file(self, file_path: str) -> dict:
        token = self._get_token()
        url = f"{_ONELAKE_DFS}/{self.workspace_id}/{self.lakehouse_name}.Lakehouse/Files/{file_path}"
        logger.info(f"OneLake GET {url}")
        headers = {
            'Authorization': f'Bearer {token}',
            'x-ms-version': '2023-11-03',
        }
        resp = requests.get(url, headers=headers, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code} from {url} — {resp.text[:300]}")
        return resp.json()

    def load_survey_questions(self, file_path: str = 'Question_data_json/survey_questions.json') -> list:
        data = self.load_json_file(file_path)
        return data.get('questions', [])

    def save_survey_response(self, assignment_number: str, staff_id: str,
                              responses: dict, token_id: int = None) -> str:
        """Write response as a JSON file to Files/Responses/ via OneLake DFS API."""
        import uuid
        from datetime import datetime

        token = self._get_token()
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        uid = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{assignment_number}_{uid}.json"

        payload = {
            'token_id': token_id,
            'assignment_number': assignment_number,
            'staff_id': staff_id,
            'responses': responses,
            'submitted_at': datetime.utcnow().isoformat() + 'Z'
        }
        content = json.dumps(payload, indent=2).encode('utf-8')

        base_url = (
            f"{_ONELAKE_DFS}/{self.workspace_id}"
            f"/{self.lakehouse_name}.Lakehouse/Files/Responses/{filename}"
        )
        auth = {
            'Authorization': f'Bearer {token}',
            'x-ms-version': '2023-11-03',
        }

        r = requests.put(f"{base_url}?resource=file", headers=auth, timeout=30)
        if not r.ok:
            raise RuntimeError(f"Create failed: {r.status_code} — {r.text[:200]}")

        r = requests.patch(
            f"{base_url}?action=append&position=0",
            headers={**auth, 'Content-Type': 'application/octet-stream', 'Content-Length': str(len(content))},
            data=content, timeout=30
        )
        if not r.ok:
            raise RuntimeError(f"Append failed: {r.status_code} — {r.text[:200]}")

        r = requests.patch(
            f"{base_url}?action=flush&position={len(content)}",
            headers=auth, timeout=30
        )
        if not r.ok:
            raise RuntimeError(f"Flush failed: {r.status_code} — {r.text[:200]}")

        logger.info(f"Response saved: Responses/{filename}")
        return filename

    def validate_token(self, token_value: str) -> dict:
        """Look up token from Files/Token_data/valid_tokens.json. Returns token dict or None."""
        try:
            data = self.load_json_file('Token_data/valid_tokens.json')
            tokens = data if isinstance(data, list) else data.get('tokens', [])
            for t in tokens:
                if t.get('token') == token_value and t.get('is_valid', True):
                    return t
            return None
        except Exception as e:
            logger.warning(f"Token lookup failed: {e}")
            return None
