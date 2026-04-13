import csv
import re
import os
import pandas as pd
from datetime import datetime
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# --- Configuration ---
INPUT_FILE = 'report.csv'
OUTPUT_FILE = 'ng_report.csv'
MASTER_DATA = 'past_errors.csv'
EXCEL_REPORT = 'Weekly_Security_Report.xlsx'

# --- 1. Presidio Setup (AI & Anonymization Layer) ---
# Define custom pattern for passwords
password_pattern = Pattern(name="password_pattern", regex=r"\b\S{4,}\b", score=0.5)

password_recognizer = PatternRecognizer(
    supported_entity="PASSWORD",
    patterns=[password_pattern],
    context=["password", "pw", "passcode", "secret code"]
)

# Initialize Analyzer Engine
registry = RecognizerRegistry()
registry.load_predefined_recognizers()
registry.add_recognizer(password_recognizer)
analyzer = AnalyzerEngine(registry=registry)

# Initialize Anonymizer Engine
anonymizer = AnonymizerEngine()

# --- 2. Profanity List ---
PROFANITY_LIST = [
    'Jesus Christ', 'God damn', 'Damn it', 'Hell', 'Holy cow',
    'shit', 'fucking', 'fuck', 'bitch', 'asshole', 'bastard', 'crap', 'piss',
    'idiot', 'stupid', 'dumb', 'shut up', 'get lost', 'lazy'
]

def redact_content(text, presidio_results):
    """
    Redacts sensitive information from the text using both 
    Presidio AI results and manual Regex patterns.
    """
    if not text:
        return text

    # 1. Redact using Presidio (AI-based entities)
    # Define how to replace specific entities
    operators = {
        "PASSWORD": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
        "PERSON": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
    }

    anonymized_result = anonymizer.anonymize(
        text=text,
        analyzer_results=presidio_results,
        operators=operators
    )
    temp_text = anonymized_result.text

    # 2. Redact using Manual Regex (Credit Card, PIN, etc.)
    # Credit Card Numbers
    temp_text = re.sub(r'\d{4}-\d{4}-\d{4}-\d{4}', '[REDACTED]', temp_text)
    # CVV/CVC
    temp_text = re.sub(r'(CVV|CVC|CID|security code).{0,10}\d{3,4}', r'\1: [REDACTED]', temp_text, flags=re.IGNORECASE)
    # PIN/Verification Codes
    temp_text = re.sub(r'(Verification|Verified|PIN|Code).{0,25}\b\d{4}\b', r'\1: [REDACTED]', temp_text, flags=re.IGNORECASE)
    # Password patterns (Regex safety net)
    temp_text = re.sub(r'(password|passcode|pw|secret code).{0,15}[:=]\s?\S+', r'\1: [REDACTED]', temp_text, flags=re.IGNORECASE)

    return temp_text

def check_logic(row):
    """
    Performs security scans and redacts PII if issues are found.
    Returns the modified row if errors exist, else None.
    """
    errors = []
    current_row = row.copy()
    
    note = current_row.get('Note', '').strip()
    contact_id = current_row.get('Contact_ID', '').strip()
    agent_time_str = current_row.get('Agent_Time', '').strip()
    skill = current_row.get('Skill', '').strip()

    if not contact_id:
        return None

    try:
        agent_time = int(agent_time_str)
    except ValueError:
        agent_time = 0

    # Check 1: Empty Notes with Handle Time
    if not note and agent_time > 0:
        errors.append(f"Empty Note (Skill: {skill})")

    # Check 2: Security Scans (Only if Note is not empty)
    if note:
        # AI Scan for Passwords
        presidio_results = analyzer.analyze(text=note, entities=["PASSWORD"], language='en')
        
        # Identify if any AI detection meets the score threshold
        if any(res.score >= 0.6 for res in presidio_results):
            errors.append("Password (AI)")

        # Regex Safety Net & PII Patterns
        if re.search(r'(password|passcode|pw|secret code).{0,15}[:=]\s?\S+', note, re.IGNORECASE):
            if "Password (AI)" not in errors:
                errors.append("Password (Regex)")

        if re.search(r'\d{4}-\d{4}-\d{4}-\d{4}', note):
            errors.append("Credit Card Number")
        
        if re.search(r'(CVV|CVC|CID|security code).{0,10}\d{3,4}', note, re.IGNORECASE):
            errors.append("CVV")
            
        if re.search(r'(Verification|Verified|PIN|Code).{0,25}\b\d{4}\b', note, re.IGNORECASE):
            errors.append("PIN")

        # Profanity Scan
        for word in PROFANITY_LIST:
            if re.search(rf'\b{word}\b', note, re.IGNORECASE):
                errors.append(f"Profanity({word})")

    if errors:
        # If any PII/Security issue is found, redact the Note field
        current_row['Note'] = redact_content(note, presidio_results)
        current_row['Reason_for_Error'] = " / ".join(errors)
        return current_row
        
    return None

def get_week_of_month(dt):
    """Helper to calculate week number within the month."""
    first_day = dt.replace(day=1)
    dom = dt.day
    adjusted_dom = dom + first_day.weekday()
    return int((adjusted_dom - 1) / 7) + 1

def create_visual_report(total_scanned):
    """Generates a clean Excel Dashboard from master data."""
    if not os.path.exists(MASTER_DATA):
        return

    df = pd.read_csv(MASTER_DATA)
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
    
    total_ng_records = df['Contact_ID'].nunique()
    total_error_instances = len(df)
    ng_rate = (total_ng_records / total_scanned) if total_scanned > 0 else 0

    df['Week'] = df.apply(lambda x: f"{x['Date'].strftime('%Y-%m')}-W{get_week_of_month(x['Date'])}", axis=1)

    with pd.ExcelWriter(EXCEL_REPORT, engine='xlsxwriter') as writer:
        display_df = df.copy()
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
        display_df.sort_values('Date', ascending=False).to_excel(writer, sheet_name='All_NG_Data', index=False)
        
        workbook = writer.book
        dashboard = workbook.add_worksheet('Dashboard')

        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#CFE2F3', 'border': 1})
        val_fmt = workbook.add_format({'border': 1})
        pct_fmt = workbook.add_format({'num_format': '0.00%', 'border': 1})

        dashboard.write('B2', 'Total Scanned Records', header_fmt)
        dashboard.write('C2', total_scanned, val_fmt)
        dashboard.write('B3', 'Unique NG Records Found', header_fmt)
        dashboard.write('C3', total_ng_records, val_fmt)
        dashboard.write('B4', 'NG Rate (Per Record)', header_fmt)
        dashboard.write('C4', ng_rate, pct_fmt)
        dashboard.write('B5', 'Total Error Instances', header_fmt)
        dashboard.write('C5', total_error_instances, val_fmt)

        pivot_df = df.groupby(['Week', 'Reason_for_Error']).size().unstack(fill_value=0)
        pivot_df.to_excel(writer, sheet_name='Chart_Data')
        
        num_weeks = len(pivot_df)
        num_errors = len(pivot_df.columns)

        bar_chart = workbook.add_chart({'type': 'column', 'subtype': 'stacked'})
        for i in range(num_errors):
            bar_chart.add_series({
                'name':       ['Chart_Data', 0, i + 1],
                'categories': ['Chart_Data', 1, 0, num_weeks, 0],
                'values':      ['Chart_Data', 1, i + 1, num_weeks, i + 1],
            })
        
        bar_chart.set_title({'name': 'Weekly Security Incident Distribution'})
        bar_chart.set_x_axis({'name': 'Week Number'})
        bar_chart.set_y_axis({'name': 'Number of Incidents'})
        bar_chart.set_legend({'position': 'right'})
        bar_chart.set_size({'width': 800, 'height': 450})
        
        dashboard.insert_chart('B7', bar_chart)

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    scanned_count = 0
    ng_list = []
    
    # Process input file
    with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if 'Reason_for_Error' not in fieldnames:
            fieldnames.append('Reason_for_Error')
            
        for row in reader:
            scanned_count += 1
            result = check_logic(row)
            if result:
                ng_list.append(result)

    if ng_list:
        # Save results to NG report
        with open(OUTPUT_FILE, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(ng_list)
        
        # Update Master Database
        new_df = pd.DataFrame(ng_list)
        if os.path.exists(MASTER_DATA):
            old_df = pd.read_csv(MASTER_DATA)
            combined_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates()
        else:
            combined_df = new_df
        
        combined_df.to_csv(MASTER_DATA, index=False, encoding='utf-8-sig')
        print(f"Audit Complete. Scanned: {scanned_count}, NG Found: {len(ng_list)}")
    else:
        print("Audit Complete. No issues detected.")

    create_visual_report(scanned_count)

if __name__ == "__main__":
    main()
