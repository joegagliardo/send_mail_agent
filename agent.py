import os

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools import VertexAiSearchTool

# --- Load Environment Variables ---
# This looks for a .env file in the same directory
load_dotenv()

os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("GOOGLE_CLOUD_PROJECT") or "qwiklabs-gcp-01-3bb38adc87a2"
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"
os.environ["MODEL"] = os.getenv("MODEL") or "gemini-2.5-flash"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = os.getenv("MODEL", "gemini-2.5-flash")
DATASTORE_ID = os.getenv("DATASTORE_ID")
DATASTORE_PATH = f"projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATASTORE_ID}"

# --- Tools ---
import requests

class EmailClient:
    def __init__(self, host="34.136.30.136", port=8080):
        self.base_url = f"http://{host}:{port}"

    def send_email(self, recipient_email, subject, body_html, attachment_content='', attachment_name="event.ics"):
        """
        Calls the Flask web service to send an email via Brevo.
        """
        endpoint = f"{self.base_url}/send-email"
        
        payload = {
            "recipient_email": recipient_email,
            "subject": subject,
            "body_html": body_html,
            "attachment_content": attachment_content,
            "attachment_name": attachment_name
        }

        try:
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()  # Raises an error for 4xx or 5xx responses
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

# # --- Example Usage ---
# if __name__ == "__main__":
#     client = EmailClient()
    
#     result = client.send_email(
#         recipient_email="joey@me.com",
#         subject="Hello from Python Wrapper",
#         body_html="<p>This was sent using the new API wrapper!</p>"
#     )
    
#     print(result)



def get_date(x_days_from_today:int):
    """
    Retrieves a date for today or a day relative to today.

    Args:
        x_days_from_today (int): how many days from today? (use 0 for today)

    Returns:
        A dict with the date in a formal writing format. For example:
        {"date": "Wednesday, May 7, 2025"}
    """
    from datetime import datetime, timedelta

    target_date = datetime.today() + timedelta(days=x_days_from_today)
    date_string = target_date.strftime("%A, %B %d, %Y")

    return {"date": date_string}

def create_calendar_event(event_name: str, date_str: str) -> dict:
    """Generates an RFC-compliant ICS file and returns the base64 content."""
    import datetime
    import base64
    from dateutil import parser 
    from icalendar import Calendar, Event
    cal = Calendar()
    cal.add('prodid', '-//AI Agent Calendar//mxm.dk//')
    cal.add('version', '2.0')
    event = Event()
    event.add('summary', event_name)
    
    try:
        dt = parser.parse(date_str)
        event.add('dtstart', dt)
        event.add('dtend', dt + datetime.timedelta(hours=1))
        event.add('dtstamp', datetime.datetime.now())
        event.add('uid', f"{int(datetime.datetime.now().timestamp())}@ddintl.com")
    except (ValueError, TypeError) as e:
        return {"error": f"Could not parse date '{date_str}': {str(e)}"}
    
    cal.add_component(event)
    ical_bytes = cal.to_ical()
    b64_content = base64.b64encode(ical_bytes).decode('utf-8')
    
    return {
        "attachment_content": b64_content,
        "attachment_name": f"{event_name.replace(' ', '_')}.ics"
    }

# def send_email(recipient_email: str, subject: str, body_html: str, 
#                attachment_content: str = '', attachment_name: str = "event.ics") -> dict:
#     """Sends an email via Brevo with the corrected attachment structure."""
#     import os
#     import requests
#     from google.cloud import secretmanager
#     client = secretmanager.SecretManagerServiceClient()
#     # We use environment variables that will be available in the cloud
#     project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
#     secret_path = f"projects/{project_id}/secrets/BREVO_API_KEY/versions/latest"
    
#     try:
#         response = client.access_secret_version(request={"name": secret_path})
#         api_key = response.payload.data.decode("UTF-8")
#     except Exception as e:
#         return {"error": f"Failed to retrieve API key: {str(e)}"}

#     url = "https://api.brevo.com/v3/smtp/email"
#     headers = {"accept": "application/json", "content-type": "application/json", "api-key": api_key}
    
#     payload = {
#         "sender": {"name": "AI Agent", "email": "backup@ddintl.com"},
#         "to": [{"email": recipient_email}],
#         "subject": subject,
#         "htmlContent": body_html
#     }

#     if attachment_content:
#         payload["attachment"] = [{"name": attachment_name, "content": attachment_content}]
    
#     resp = requests.post(url, json=payload, headers=headers)
#     return resp.json() if resp.status_code < 400 else {"error": resp.text}


def send_email(recipient_email: str, subject: str, body_html: str, 
               attachment_content: str = '', attachment_name: str = "event.ics") -> dict:
    """Sends an email via Brevo with the corrected attachment structure."""
    client = EmailClient()
    
    result = client.send_email(
        recipient_email=recipient_email,
        subject=subject,
        body_html=body_html,
        attachment_content= attachment_content,
        attachment_name=attachment_name
    )


# --- Example Usage ---
# if __name__ == "__main__":
#     client = EmailClient()
    
#     result = client.send_email(
#         recipient_email="joey@me.com",
#         subject="Hello from Python Wrapper",
#         body_html="<p>This was sent using the new API wrapper!</p>"
#     )
    
#     print(result)
#     quit()



vertex_search_tool = VertexAiSearchTool(
    data_store_id=DATASTORE_PATH,
    bypass_multi_tools_limit=True
)

root_agent = Agent(
    name="root_agent",
    description="Sends and email",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    instruction="""
    You are an insurance assistant. Your goal is to help users find policy expiration dates
    and set reminders.
    1. ALWAYS call 'VertexAiSearchTool' first to retrieve the data.
    2. DO NOT claim you lack access to policy information.
    3. If the user mentions a date/reminder or you find one in the search results, you MUST first call 'create_calendar_event'.
    4. Once you receive the 'attachment_content' from that tool, you MUST then call 'send_email'.
    5. Pass the 'attachment_content' and 'attachment_name' from the first tool into the 'send_email' tool.
    6. Only tell the user "The email has been sent" AFTER you have received a successful response from the 'send_email' tool.
    7. Show the curl statement that would be called from a terminal that send_mail function would make as part of the output if the prompt asks for the debugging information.
    """,
    tools=[vertex_search_tool, send_email, create_calendar_event]
    )


# adk deploy agent_engine send_mail --display_name "Send mail agent 1.5" --staging_bucket gs://qwiklabs-gcp-01-3bb38adc87a2-agent-engine


# adk deploy agent_engine send_mail \
# --display_name "Send mail agent 1.0" \
# --staging_bucket gs://qwiklabs-gcp-01-3bb38adc87a2-agent-engine

# def deploy(root_agent: str, display_name: str, attachment_name: str, project_id: str, location: str):
#     import vertexai
#     from vertexai.preview import reasoning_engines


#     vertexai.init(project=project_id, location=location)

#     deployment_config = {
#         "network_attachment": f"projects/{project_id}/regions/{location}/networkAttachments/{attachment_name}"
#     }

#     x = reasoning_engines.ReasoningEngine.create(

#     remote_agent = reasoning_engines.ReasoningEngine.create(
#         root_agent,  
#         display_name=display_name,
#         # Try passing it as deployment_config
#         deployment_config=deployment_config, 
#         requirements=[
#             "google-cloud-aiplatform[langchain,reasoningengine,adk]",
#             "google-cloud-secret-manager",
#             "icalendar",
#             "python-dateutil",
#             "requests",
#             "python-dotenv"
#         ],
#         extra_packages=["."] 
#     )

#     # remote_agent = reasoning_engines.ReasoningEngine.create(
#     #     root_agent,  
#     #     display_name=display_name,
#     #     extra_packages_config={
#     #         "network_attachment": f"projects/{project_id}/regions/{location}/networkAttachments/{attachment_name}"
#     #     },
#     #     requirements=[
#     #         "google-cloud-aiplatform[langchain,reasoningengine,adk]>=1.110.0",
#     #         "google-cloud-secret-manager",
#     #         "icalendar",
#     #         "python-dateutil",
#     #         "requests",
#     #         "python-dotenv"
#     #     ],
#     #     extra_packages=["."] 
#     # )



#     # remote_agent = reasoning_engines.ReasoningEngine.create(
#     # root_agent,  
#     # display_name=display_name,
#     # # 2026 REQUIRED: Link to your VPC for the Fixed IP
#     # network_attachment=f"projects/{project_id}/regions/{location}/networkAttachments/{attachment_name}",
    
#     # # Bundle all dependencies for the cloud runtime
#     # requirements=[
#     #     "google-cloud-aiplatform[langchain,reasoningengine,adk]",
#     #     "google-cloud-secret-manager",
#     #     "icalendar",
#     #     "python-dateutil",
#     #     "requests",
#     # ],
#     # # Includes current directory files (like .env or local modules)
#     # extra_packages=["."] 
#     # )

#     print(f"🚀 Agent successfully deployed to Agent Engine!")
#     print(f"Resource Name: {remote_agent.resource_name}")

# if __name__ == "__main__":
#     import argparse
#     parser = argparse.ArgumentParser(description="Deploy ADK Agent to Vertex AI Agent Engine with Fixed IP")
    
#     # Define the command line arguments
#     parser.add_argument("--display-name", type=str, required=True, help="Display name for the deployed agent")
#     parser.add_argument("--attachment", type=str, required=True, help="Name of the Network Attachment")
#     parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="Google Cloud Project ID")
#     parser.add_argument("--location", type=str, default="us-central1", help="Google Cloud Location")

#     args = parser.parse_args()

#     # Pass the 'root_agent' object (defined globally in your script) 
#     # along with the parsed command line strings
#     deploy(
#         root_agent=root_agent, 
#         display_name=args.display_name, 
#         attachment_name=args.attachment, 
#         project_id=args.project,
#         location=args.location
#     )    

# # python agent.py --display-name "end mail agent 1.5" --attachment "brevo_attachment" --project=${PROJECT_ID} --location ${LOCATION}