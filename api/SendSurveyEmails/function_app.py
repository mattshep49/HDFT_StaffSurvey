import azure.functions as func
import json
import logging
import os
import sys

from azure.communication.email import EmailClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.onelake_connector import OneLakeConnector

EMAIL_LINKS_PATH = "email_json_link/email_links.json"

EMAIL_SUBJECT = "HDFT Staff Survey – Your Personal Survey Link"

EMAIL_BODY_HTML = """\
<html>
<body>
<p>Dear colleague,</p>
<p>
  You are invited to take part in the HDFT QuarterlyStaff Survey. Your responses are
  completely confidential and the survey takes approximately 10 minutes.
</p>
<p>
  Please use your personal link below — it is unique to you and can only be
  used once:
</p>
<p><a href="{url}">{url}</a></p>
<p>

</p>
<p>Thank you for your time.</p>
<p>HDFT People Team</p>
</body>
</html>
"""


def _send_emails(records: list) -> tuple[int, int, list]:
    conn_str = os.environ["ACS_CONNECTION_STRING"]
    sender = os.environ["ACS_SENDER_ADDRESS"]
    client = EmailClient.from_connection_string(conn_str)

    sent = 0
    failed = 0
    errors = []

    for record in records:
        to_addr = record.get("email")
        url = record.get("url")
        if not to_addr or not url:
            failed += 1
            errors.append({"email": to_addr, "error": "missing email or url"})
            continue
        try:
            message = {
                "senderAddress": sender,
                "recipients": {"to": [{"address": to_addr}]},
                "content": {
                    "subject": EMAIL_SUBJECT,
                    "html": EMAIL_BODY_HTML.format(url=url),
                },
            }
            poller = client.begin_send(message)
            result = poller.result()
            if result.get("status") == "Succeeded":
                sent += 1
            else:
                failed += 1
                errors.append({"email": to_addr, "error": str(result)})
        except Exception as exc:
            logging.warning(f"Failed to send to {to_addr}: {exc}")
            failed += 1
            errors.append({"email": to_addr, "error": str(exc)})

    return sent, failed, errors


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Send survey invitation emails — POST /api/send-survey-emails
    Reads email_links.json from OneLake and emails every recipient their survey URL.
    Optional body: {"dry_run": true} to validate config without sending.
    """
    logging.info("SendSurveyEmails function triggered")

    dry_run = False
    test_email = None
    try:
        body = req.get_json()
        dry_run = body.get("dry_run", False)
        test_email = body.get("test_email")
    except (ValueError, AttributeError):
        pass

    # Single test email — bypasses OneLake entirely
    if test_email:
        test_url = "https://calm-mushroom-018f3be03.3.azurestaticapps.net/?token=TEST-TOKEN"
        try:
            sent, failed, errors = _send_emails([{"email": test_email, "url": test_url}])
            return func.HttpResponse(
                json.dumps({"test_email": test_email, "sent": sent, "failed": failed, "errors": errors}),
                status_code=200, mimetype="application/json"
            )
        except Exception as exc:
            return func.HttpResponse(
                json.dumps({"error": f"ACS failure: {exc}"}),
                status_code=500, mimetype="application/json"
            )

    connector = OneLakeConnector()
    if not connector.is_configured():
        return func.HttpResponse(
            json.dumps({"error": "OneLake service not configured"}),
            status_code=503, mimetype="application/json"
        )

    try:
        records = connector.load_json_file(EMAIL_LINKS_PATH)
        if not isinstance(records, list):
            raise ValueError("email_links.json is not a JSON array")
    except Exception as exc:
        logging.error(f"Failed to load email links: {exc}")
        return func.HttpResponse(
            json.dumps({"error": f"Could not load email list: {exc}"}),
            status_code=500, mimetype="application/json"
        )

    if dry_run:
        return func.HttpResponse(
            json.dumps({"dry_run": True, "records_found": len(records)}),
            status_code=200, mimetype="application/json"
        )

    try:
        sent, failed, errors = _send_emails(records)
    except Exception as exc:
        logging.error(f"ACS error: {exc}")
        return func.HttpResponse(
            json.dumps({"error": f"ACS failure: {exc}"}),
            status_code=500, mimetype="application/json"
        )

    logging.info(f"Email send complete: sent={sent} failed={failed}")
    return func.HttpResponse(
        json.dumps({"sent": sent, "failed": failed, "errors": errors}),
        status_code=200, mimetype="application/json"
    )
