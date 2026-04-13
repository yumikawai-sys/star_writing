import httpx
from fastapi import FastAPI, Request, BackgroundTasks
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

app = FastAPI()

# --- 1. Configuration (Obtain these from your NICE CXone admin) ---
# Your regional base URL (e.g., na1, jp1, au1)
CXONE_BASE_URL = "https://api-jp1.niceincontact.com" 
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

# Initialize Presidio Engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# --- 2. Redaction Logic ---
def redact_sensitive_info(text):
    """Scan and replace PII with [REDACTED]"""
    if not text:
        return text

    # Analyze for Passwords, Credit Cards, etc.
    results = analyzer.analyze(text=text, entities=["CRYPTO", "CREDIT_CARD", "PERSON", "PHONE_NUMBER"], language='en')

    # Anonymize (Replace found entities with [REDACTED])
    operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})}
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)
    
    return anonymized_result.text

# --- 3. NICE CXone API Helpers ---
async def get_access_token():
    """Fetch OAuth2 token for CXone API"""
    url = f"{CXONE_BASE_URL}/incontactapi/services/v28.0/token"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, auth=(CLIENT_ID, CLIENT_SECRET), data={"grant_type": "client_credentials"})
        response.raise_for_status()
        return response.json().get("access_token")

async def update_cxone_summary(contact_id, clean_text):
    """Write the redacted summary back to CXone database"""
    token = await get_access_token()
    # Note: Endpoint path may vary based on your specific CXone product (e.g. Admin API or Business Data)
    url = f"{CXONE_BASE_URL}/incontactapi/services/v28.0/interactions/{contact_id}/summary"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.put(url, json={"summary": clean_text}, headers=headers)
        if response.status_code == 200:
            print(f"Successfully redacted Contact ID: {contact_id}")
        else:
            print(f"Failed to update ID {contact_id}: {response.text}")

# --- 4. WebHook Endpoint ---
@app.post("/webhook/summary-generated")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint that NICE CXone calls when a summary is generated.
    Expected JSON: {"contactId": "12345", "summaryText": "Customer's card is..."}
    """
    payload = await request.json()
    contact_id = payload.get("contactId")
    raw_text = payload.get("summaryText")

    if not contact_id or not raw_text:
        return {"status": "ignored", "reason": "missing data"}

    # Run the heavy redaction and API call in the background 
    # to respond to CXone immediately and prevent timeouts.
    background_tasks.add_task(process_redaction_flow, contact_id, raw_text)

    return {"status": "received"}

async def process_redaction_flow(contact_id, text):
    # Perform redaction
    clean_text = redact_sensitive_info(text)
    # Update CXone via API
    await update_cxone_summary(contact_id, clean_text)

if __name__ == "__main__":
    import uvicorn
    # Start the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
