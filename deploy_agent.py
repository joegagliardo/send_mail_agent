import os
import vertexai
from vertexai.preview import reasoning_engines
from google.cloud import aiplatform

# --- Configuration ---
PROJECT_ID = "qwiklabs-gcp-01-3bb38adc87a2"
LOCATION = "us-central1"
STAGING_BUCKET = f"gs://{PROJECT_ID}-agent-engine"
MODEL_NAME = "gemini-1.5-flash" # Use 1.5-flash for maximum stability in Agent Engine

# --- Tool Definitions (Keep these global for easy pickling) ---
def create_calendar_event(event_name: str, date_str: str) -> dict:
    """Generates an RFC-compliant ICS file and returns the base64 content."""
    import datetime
    import base64
    from dateutil import parser 
    from icalendar import Calendar, Event
    # ... (Your existing logic is fine here) ...
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
    except Exception as e:
        return {"error": str(e)}
    cal.add_component(event)
    return {
        "attachment_content": base64.b64encode(cal.to_ical()).decode('utf-8'),
        "attachment_name": f"{event_name.replace(' ', '_')}.ics"
    }

def send_email(recipient_email: str, subject: str, body_html: str, 
               attachment_content: str = None, attachment_name: str = "event.ics") -> dict:
    """Sends an email via Brevo."""
    import os
    import requests
    from google.cloud import secretmanager
    # ... (Your existing logic is fine here) ...
    return {"status": "success"} # Placeholder for brevity

# --- Agent Wrapper ---
class CalendarAgent:
    def __init__(self, model_name: str, project: str, location: str):
        self.model_name = model_name
        self.project = project
        self.location = location

    def set_up(self):
        """This runs on the server. Initialize your agent here."""
        from google.adk.agents import Agent
        from google.adk.models.google_llm import Gemini
        
        llm = Gemini(
            model=self.model_name,
            vertexai=True,
            project=self.project,
            location=self.location
        )
        
        self.executor = Agent(
            name="calendar_root",
            model=llm,
            instruction="You are a precise assistant. Create calendar events and email them.",
            tools=[create_calendar_event, send_email],
        )

    def query(self, input_text: str):
        """Use the synchronous generator to avoid asyncio.run() deadlocks."""
        response_text = ""
        # ADK run() returns a generator. We iterate and collect content.
        for event in self.executor.run(input_text):
            if hasattr(event, 'content'):
                response_text += event.content
            elif isinstance(event, str):
                response_text += event
        return response_text

# --- Deployment Logic ---
if __name__ == "__main__":
    aiplatform.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

    agent_instance = CalendarAgent(MODEL_NAME, PROJECT_ID, LOCATION)

    remote_agent = reasoning_engines.ReasoningEngine.create(
        agent_instance, 
        requirements=[
            "google-adk",  
            "google-cloud-aiplatform[reasoningengine]",
            "google-cloud-secret-manager",
            "icalendar",
            "python-dateutil",
            "requests",
            "pydantic>=2.6.4",
            "cloudpickle==3.0.0" 
        ],
        display_name="Email Calendar Agent Synchronous",
    )
    print(f"Active! Resource: {remote_agent.resource_name}")

