# Install required packages:
# pip install google-adk langchain requests certifi httpx

import json
import requests
import certifi
import os
import httpx
import urllib3
from google.adk import Agent
from langchain_openai import ChatOpenAI

# --- Fix SSL certificate issues for requests ---
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = certifi.where()

# Disable SSL warnings for ServiceNow requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional: tiktoken cache directory
tiktoken_cache_dir = r"C:\Users\GenAICHNSIRUSR84\Desktop\SNOW Agent\tiktoken_cache"
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir

# Validate cache file exists (optional, remove if not needed)
assert os.path.exists(os.path.join(
    tiktoken_cache_dir,
    "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
))

print("Testing Langchain with GenAI Lab Models")

client = httpx.Client(verify=False)

# 🔑 GenAI Lab model (Hackathon key only)
llm = ChatOpenAI(
    base_url="https://genailab.tcs.in",
    model="azure/genailab-maas-gpt-4o-mini",
    api_key="sk-V4pmNP__HX36T0eUIpnPdA",  # Hackathon only
    http_client=client
)

# 🔑 ServiceNow credentials
SNOW_INSTANCE = "dev202851.service-now.com"
SNOW_USER = "admin"
SNOW_PASS = "yi-FmXmSR93$"

# --- Agent that parses user input using GenAI Lab model ---
class ParseAgent(Agent):
    def __init__(self):
        super().__init__(name="ParseAgent")

    def run(self, user_input: str) -> dict:
        prompt = f"""
        You are an assistant that extracts ticket details from user input for ServiceNow.
        The user input is: "{user_input}"

        Extract the following fields:
        - short_description: A brief summary of the issue (max 100 characters)
        - description: A detailed description of the issue
        - priority: One of '1 - Critical', '2 - High', '3 - Moderate', '4 - Low'

        If any field is missing or unclear, use reasonable defaults:
        - short_description: "Issue reported by user"
        - description: "User-reported issue, details incomplete"
        - priority: "3 - Moderate"

        Return the result as a JSON object.
        """
        try:
            response = llm.invoke(prompt)   # ✅ use global llm directly
            response_text = response.content.strip()
            # Try to parse JSON safely
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                import re
                match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                else:
                    raise
        except Exception as e:
            print(f"Error parsing input with GenAI Lab model: {e}")
            return {
                "short_description": "Issue reported by user",
                "description": "User-reported issue, details incomplete",
                "priority": "3 - Moderate"
            }

# --- Agent that creates ServiceNow tickets ---
class ServiceNowAgent(Agent):
    def __init__(self):
        super().__init__(name="ServiceNowAgent")

    def run(self, ticket_details: dict) -> dict:
        url = f"https://{SNOW_INSTANCE}/api/now/table/incident"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "short_description": ticket_details["short_description"],
            "description": ticket_details["description"],
            "priority": ticket_details["priority"]
        }
        try:
            response = requests.post(
                url,
                auth=(SNOW_USER, SNOW_PASS),
                headers=headers,
                json=payload,
                verify=False   # 🚫 SSL verification disabled
            )
            if response.status_code == 201:
                ticket_data = response.json()
                return {
                    "status": "success",
                    "ticket_number": ticket_data["result"]["number"],
                    "sys_id": ticket_data["result"]["sys_id"]
                }
            else:
                return {
                    "status": "error",
                    "error_message": f"Failed to create ticket: {response.text}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e)
            }

# --- Main entry point ---
if __name__ == "__main__":
    print("🚀 ServiceNow Ticket Assistant")
    print("Type your issue below. Type 'exit' to quit.\n")

    while True:
        user_input = input("📝 Describe your issue: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Exiting ServiceNow Ticket Assistant.")
            break

        # Step 1: Parse user input
        print("\n🔍 Parsing user input...")
        parse_agent = ParseAgent()
        ticket_details = parse_agent.run(user_input)
        print("✅ Parsed ticket details:")
        print(json.dumps(ticket_details, indent=2))

        # Step 2: Create ServiceNow ticket
        print("\n🛠️ Creating ServiceNow ticket...")
        snow_agent = ServiceNowAgent()
        result = snow_agent.run(ticket_details)

        if result["status"] == "success":
            print("🎫 Ticket created successfully:")
            print(f"  - Ticket Number: {result['ticket_number']}")
            print(f"  - Sys ID: {result['sys_id']}\n")
        else:
            print("❌ Failed to create ticket:")
            print(f"  - Error: {result['error_message']}\n")
