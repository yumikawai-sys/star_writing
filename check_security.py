import csv
import re
import os
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern


# intall library
# pip install presidio-analyzer presidio-anonymizer spacy

# download English model
# python -m spacy download en_core_web_lg

# --- Configuration ---
INPUT_FILE = 'report.csv'
OUTPUT_FILE = 'ng_report.csv'

# --- 1. Custom Presidio Setup (AI Layer) ---

# Define a custom pattern for potential passwords (4+ characters)
password_pattern = Pattern(name="password_pattern", regex=r"\b\S{4,}\b", score=0.5)

# Create a Custom Recognizer for "PASSWORD"
# Score increases if context words like 'pass' or 'pw' are nearby
password_recognizer = PatternRecognizer(
    supported_entity="PASSWORD",
    patterns=[password_pattern],
    context=["password", "pw", "passcode", "secret code"]
)

registry = RecognizerRegistry()
registry.load_predefined_recognizers()
registry.add_recognizer(password_recognizer)

analyzer = AnalyzerEngine(registry=registry)

# --- 2. List of prohibited words ---
PROFANITY_LIST = [
    'Jesus Christ', 'God damn', 'Damn it', 'Hell', 'Holy cow',
    'shit', 'fucking', 'fuck', 'bitch', 'asshole', 'bastard', 'crap', 'piss',
    'idiot', 'stupid', 'dumb', 'shut up', 'get lost', 'lazy'
]

def check_logic(row):
    """
    Hybrid security check using AI (Presidio) and Manual Regex.
    """
    errors = []
    
    note = row.get('Note', '').strip()
    contact_id = row.get('Contact_ID', '').strip()
    agent_time_str = row.get('Agent_Time', '').strip()
    skill = row.get('Skill', '').strip()

    if not contact_id:
        return None

    try:
        agent_time = int(agent_time_str)
    except ValueError:
        agent_time = 0

    if not note:
        if agent_time > 0:
            errors.append(f"Empty Note (Skill: {skill})")
        return row if errors else None

    # --- 3. LAYER 1: AI Context Check (Presidio) ---
    # Finds "Tom123" only if the word "password" is nearby
    presidio_results = analyzer.analyze(text=note, entities=["PASSWORD"], language='en')
    if any(res.score >= 0.6 for res in presidio_results):
        errors.append("Password (AI Context)")

    # --- 4. LAYER 2: Regex Safety Net (Pattern Matching) ---
    # Catches common password formats even if AI is unsure
    # Example: "pw: admin123" or "password=ABC"
    if "Password (AI Context)" not in errors:
        if re.search(r'(password|passcode|pw|secret code).{0,15}[:=]\s?\S+', note, re.IGNORECASE):
            errors.append("Password (Regex Pattern)")

    # --- 5. Other Security Checks (Regex) ---
    
    # Credit Card Number
    if re.search(r'\d{4}-\d{4}-\d{4}-\d{4}', note):
        errors.append("Credit Card Number")

    # CVV
    if re.search(r'(CVV|CVC|CID|security code).{0,10}\d{3,4}', note, re.IGNORECASE):
        errors.append("CVV")

    # PIN/Verification Code
    if re.search(r'(Verification|Verified|PIN|Code).{0,25}\b\d{4}\b', note, re.IGNORECASE):
        errors.append("PIN/Verification Code")

    # --- 6. Profanity Check ---
    for word in PROFANITY_LIST:
        if re.search(rf'\b{word}\b', note, re.IGNORECASE):
            errors.append(f"Profanity({word})")

    if errors:
        row['Reason_for_Error'] = " / ".join(errors)
        return row
    return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    ng_list = []
    
    with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        original_fieldnames = reader.fieldnames
        for row in reader:
            result = check_logic(row)
            if result:
                ng_list.append(result)

    if ng_list:
        output_fieldnames = list(original_fieldnames)
        if 'Reason_for_Error' not in output_fieldnames:
            output_fieldnames.append('Reason_for_Error')

        with open(OUTPUT_FILE, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=output_fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(ng_list)
        print(f"Success: {len(ng_list)} NG items flagged in '{OUTPUT_FILE}'.")
    else:
        print("Success: No security issues detected.")

if __name__ == "__main__":
    main()
