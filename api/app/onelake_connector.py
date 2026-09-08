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
        resp = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def load_survey_questions(self, file_path: str = 'survey_questions.json') -> list:
        data = self.load_json_file(file_path)
        return data.get('questions', [])
