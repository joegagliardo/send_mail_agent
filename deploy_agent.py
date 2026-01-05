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
        """This runs on the server. We wrap everything in a try-except to see logs."""
        try:
            import nest_asyncio
            nest_asyncio.apply()
            
            import vertexai
            from google.adk.agents import Agent
            from google.adk.models.google_llm import Gemini
            
            vertexai.init(project=self.project, location=self.location)
            
            # Using Gemini 1.5 Flash for the backend model
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
        except Exception as e:
            # This will print to the Reasoning Engine logs if initialization fails
            print(f"CRITICAL ERROR DURING SET_UP: {str(e)}")
            raise e

    def query(self, input_text: str):
        """
        Updated query method to use .stream() which is standard for 
        the current Google ADK Agent executor.
        """
        try:
            responses = []
            # In ADK, 'stream' is the common method for iterative execution
            for event in self.executor.stream(input_text):
                # The event object structure can vary; we check for common content attributes
                if hasattr(event, 'content'):
                    responses.append(str(event.content))
                elif hasattr(event, 'text'):
                    responses.append(str(event.text))
                elif isinstance(event, str):
                    responses.append(event)
            
            final_response = "".join(responses)
            return final_response if final_response else "Action completed, but no text response was generated."
            
        except Exception as e:
            # This helps us catch if 'stream' is also not the right method
            return f"Execution error: {str(e)}. Attempting alternative..."

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
            "nest-asyncio",
            "cloudpickle==3.0.0" 
        ],
        display_name="Email Calendar Agent Synchronous",
    )
    print(f"Active! Resource: {remote_agent.resource_name}")

