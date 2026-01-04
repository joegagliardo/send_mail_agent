import sys, os
import importlib.util

# 1. Force the current directory into the front of the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 2. Explicitly import the local agent.py
try:
    import agent
    # Optional: Force a reload to ensure you aren't using a cached version
    import importlib
    importlib.reload(agent)
except ImportError as e:
    print(f"Error: Could not find agent.py in {current_dir}")
    raise e
    
# Ensure the current directory is in the path so 'agent.py' can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_file_path = os.path.join(current_dir, "agent.py")
print(agent_file_path)

from google.cloud import aiplatform
from vertexai.preview import reasoning_engines

# Configuration
PROJECT_ID = "qwiklabs-gcp-01-3bb38adc87a2"
LOCATION = "us-central1"
STAGING_BUCKET = f"gs://{PROJECT_ID}-agent-engine"

aiplatform.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

print("Deploying Gemini 2.5 Flash Agent to Vertex AI...")

# Pass the result of the function we added to agent.py
remote_agent = reasoning_engines.ReasoningEngine.create(
    agent.get_agent(), 
    requirements=[
        "google-adk",  
        "google-cloud-aiplatform[reasoningengine]",
        "google-cloud-secret-manager",
        "google-cloud-storage>=3.0.0",
        "icalendar",
        "python-dateutil",
        "requests",
        "python-dotenv",
        "pydantic>=2.6.4", 
        "cloudpickle==3.0.0" 
        ],
    extra_packages=[agent_file_path],
    display_name="Email Calendar Agent 2.5",
    description="Agent using Gemini 2.5 Flash to create .ics files and send emails.",
)

print(f"Deployment complete! Resource Name: {remote_agent.resource_name}")
