def send_email(recipient_email: str, subject: str, body_html: str) -> dict:
    """
    Sends an email using the Brevo API.
    Args:
        recipient_email: Destination email.
        subject: Email subject.
        body_html: HTML content.
    """
    import requests
    from google.cloud import secretmanager
    
    project_id = "qwiklabs-gcp-01-3bb38adc87a2"
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/BREVO_API_KEY/versions/latest"
    
    response = client.access_secret_version(request={"name": name})
    api_key = response.payload.data.decode("UTF-8")

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
    
    resp = requests.post(url, json=payload, headers=headers)
    return resp.json()