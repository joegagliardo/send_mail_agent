import os
import requests
from flask import Flask, request, jsonify
from google.cloud import secretmanager

app = Flask(__name__)
GOOGLE_CLOUD_PROJECT="qwiklabs-gcp-01-3bb38adc87a2"
def get_brevo_api_key():
    """Retrieves the API key from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    secret_path = f"projects/{project_id}/secrets/BREVO_API_KEY/versions/latest"
    
    response = client.access_secret_version(request={"name": secret_path})
    return response.payload.data.decode("UTF-8")

@app.route('/send-email', methods=['POST'])
def send_email_endpoint():
    # 1. Parse incoming JSON data
    data = request.get_json()
    
    # 2. Validate required fields
    recipient_email = data.get('recipient_email')
    subject = data.get('subject')
    body_html = data.get('body_html')
    
    if not all([recipient_email, subject, body_html]):
        return jsonify({"error": "Missing required fields: recipient_email, subject, or body_html"}), 400

    # Optional fields
    attachment_content = data.get('attachment_content', '')
    attachment_name = data.get('attachment_name', 'event.ics')

    try:
        api_key = get_brevo_api_key()
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve API key: {str(e)}"}), 500

    # 3. Prepare Brevo API call
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json", 
        "content-type": "application/json", 
        "api-key": api_key
    }
    
    payload = {
        "sender": {"name": "AI Agent", "email": "backup@ddintl.com"},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "htmlContent": body_html
    }

    if attachment_content:
        payload["attachment"] = [{"name": attachment_name, "content": attachment_content}]
    
    # 4. Execute request
    resp = requests.post(url, json=payload, headers=headers)
    
    if resp.status_code < 400:
        return jsonify(resp.json()), 200
    else:
        return jsonify({"error": resp.text}), resp.status_code

if __name__ == '__main__':
    # Use PORT env var for Cloud Run compatibility
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
