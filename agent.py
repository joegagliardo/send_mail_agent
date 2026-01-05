import os
# import datetime
# import base64
# import requests
# from dateutil import parser 
# from icalendar import Calendar, Event
# from google.cloud import secretmanager
# from google.cloud import aiplatform

from dotenv import load_dotenv

# from google.adk.agents import Agent, BaseAgent
# from google.adk.models.google_llm import Gemini
# from pydantic import Field # Add this import
from google.adk.agents import Agent
from google.adk.tools import VertexAiSearchTool

# --- Load Environment Variables ---
# This looks for a .env file in the same directory
# load_dotenv()

os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("GOOGLE_CLOUD_PROJECT") or "qwiklabs-gcp-01-3bb38adc87a2"
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"
os.environ["MODEL"] = os.getenv("MODEL") or "gemini-2.5-flash"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = os.getenv("MODEL", "gemini-2.5-flash")
DATASTORE_ID = os.getenv("DATASTORE_ID")
# DATASTORE_ID = "insurance-datastore"
DATASTORE_PATH = f"projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATASTORE_ID}"

# 1. Define the model explicitly with the correct project/location
# llm = Gemini(
#     model="gemini-2.5-flash",
#     vertexai=True,
#     project="qwiklabs-gcp-01-3bb38adc87a2",
#     location="us-central1"
# )

# --- Tools ---

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

def send_email(recipient_email: str, subject: str, body_html: str, 
               attachment_content: str = '', attachment_name: str = "event.ics") -> dict:
    """Sends an email via Brevo with the corrected attachment structure."""
    import os
    import requests
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    # We use environment variables that will be available in the cloud
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    secret_path = f"projects/{project_id}/secrets/BREVO_API_KEY/versions/latest"
    
    try:
        response = client.access_secret_version(request={"name": secret_path})
        api_key = response.payload.data.decode("UTF-8")
    except Exception as e:
        return {"error": f"Failed to retrieve API key: {str(e)}"}

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"accept": "application/json", "content-type": "application/json", "api-key": api_key}
    
    payload = {
        "sender": {"name": "AI Agent", "email": "backup@ddintl.com"},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "htmlContent": body_html
    }

    if attachment_content:
        payload["attachment"] = [{"name": attachment_name, "content": attachment_content}]
    
    resp = requests.post(url, json=payload, headers=headers)
    return resp.json() if resp.status_code < 400 else {"error": resp.text}

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


# class CalendarRootAgent(BaseAgent):
#     """
#     Custom Agent class for 2026 ADK. 
#     Attributes must be declared as fields for Pydantic validation.
#     """
#     # 1. Declare fields here so Pydantic recognizes them
#     model_name: str
#     project: str
#     location: str
#     executor: Agent = Field(default=None, exclude=True) # exclude=True keeps it out of serialization

#     def __init__(self, model_name: str, project: str, location: str, name: str = "calendar_root"):
#         # 2. Pass values to super().__init__ as keyword arguments
#         super().__init__(
#             name=name, 
#             model_name=model_name, 
#             project=project, 
#             location=location
#         )

#     def set_up(self):
#         """Initializes the inner LLM using the validated fields."""
#         from google.adk.models.google_llm import Gemini
#         import google.adk
        
#         llm = Gemini(
#             model=self.model_name,
#             vertexai=True,
#             project=self.project,
#             location=self.location
#         )
        
#         self.executor = Agent(
#             name=self.name,
#             model=llm,
#             instruction="""
#             You are a precise assistant. Follow these steps exactly:
#             1. If the user mentions a date/reminder, you MUST first call 'create_calendar_event'.
#             2. Once you receive the 'attachment_content' from that tool, you MUST then call 'send_email'.
#             3. Pass the 'attachment_content' and 'attachment_name' from the first tool into the 'send_email' tool.
#             4. Only tell the user "The email has been sent" AFTER you have received a successful response from the 'send_email' tool.
#             """,
#             tools=[create_calendar_event, send_email],
#         )

#     async def _run_async_impl(self, ctx):
#         # Transfer the stream from the executor to the runner
#         async for event in self.executor.run_async(ctx):
#             yield event


# class ReasoningEngineWrapper:
#     def __init__(self, model_name: str, project: str, location: str):
#         self.model_name = model_name
#         self.project = project
#         self.location = location

#     def set_up(self):
#         # Imports inside set_up prevent pickling errors
#         from google.adk.agents import Agent
#         from google.adk.models.google_llm import Gemini
        
#         llm = Gemini(
#             model=self.model_name,
#             vertexai=True,
#             project=self.project,
#             location=self.location
#         )
#         self.executor = Agent(
#             name="calendar_root",
#             model=llm,
#             instruction="...",
#             tools=[create_calendar_event, send_email],
#         )

#     def query(self, input: str):
#         # Vertex AI expects 'input' as a kwarg usually, 
#         # but your wrapper method handles the mapping.
#         return self.executor.run(input)

# # --- Export for Deployment ---

# # def get_agent():
# #     """Function called by deploy.py."""
# #     return ReasoningEngineWrapper(
# #         model_name="gemini-2.5-flash",
# #         project="qwiklabs-gcp-01-3bb38adc87a2",
# #         location="us-central1"
# #     )


# def get_agent():
#     # Define the core agent logic
#     from vertexai import agent_engines
#     llm = Gemini(model="gemini-2.5-flash", vertexai=True)
#     root_agent = Agent(
#         name="calendar_root",
#         model=llm,
#         tools=[create_calendar_event, send_email],
#         instruction="Your instructions here..."
#     )
    
#     # Wrap it in AdkApp for better serialization
#     return agent_engines.AdkApp(agent=root_agent)

# if __name__ == "__main__":
#     # Compatibility for ADK Web tools that look for root_agent
#     root_agent = CalendarRootAgent(
#         model_name="gemini-2.5-flash",
#         project="qwiklabs-gcp-01-3bb38adc87a2",
#         location="us-central1"
#     )
#     root_agent.set_up()


# adk deploy agent_engine send_mail \
# --display_name "Send mail agent 1.0" \
# --staging_bucket gs://qwiklabs-gcp-01-3bb38adc87a2-agent-engine

# old requirements
# google-cloud-aiplatform[adk,agent_engines]==1.110.0
# pydantic