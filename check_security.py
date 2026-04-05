import csv
import re
import os
import pandas as pd
from datetime import datetime
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern

# --- Configuration ---
INPUT_FILE = 'report.csv'
OUTPUT_FILE = 'ng_report.csv'
MASTER_DATA = 'past_errors.csv'
EXCEL_REPORT = 'Weekly_Security_Report.xlsx'

# --- 1. Custom Presidio Setup ---
password_pattern = Pattern(name="password_pattern", regex=r"\b\S{4,}\b", score=0.5)
password_recognizer = PatternRecognizer(
    supported_entity="PASSWORD",
    patterns=[password_pattern],
    context=["password", "pw", "passcode", "secret code"]
)

registry = RecognizerRegistry()
registry.load_predefined_recognizers()
registry.add_recognizer(password_recognizer)
analyzer = AnalyzerEngine(registry=registry)

# --- 2. Profanity List ---
PROFANITY_LIST = [
    'Jesus Christ', 'God damn', 'Damn it', 'Hell', 'Holy cow',
    'shit', 'fucking', 'fuck', 'bitch', 'asshole', 'bastard', 'crap', 'piss',
    'idiot', 'stupid', 'dumb', 'shut up', 'get lost', 'lazy'
]

def check_logic(row):
    """
    Hybrid security check. 
    Returns the row with 'Reason_for_Error' if issues are found.
    """
    errors = []
    # Work on a copy to ensure original data (like Note) is preserved
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

    # 1. Check for Empty Notes with Handle Time
    if not note and agent_time > 0:
        errors.append(f"Empty Note (Skill: {skill})")

    # 2. Security Checks (Only if Note exists)
    if note:
        # AI Context Check (Presidio)
        presidio_results = analyzer.analyze(text=note, entities=["PASSWORD"], language='en')
        if any(res.score >= 0.6 for res in presidio_results):
            errors.append("Password (AI Context)")

        # Regex Safety Net
        if "Password (AI Context)" not in errors:
            if re.search(r'(password|passcode|pw|secret code).{0,15}[:=]\s?\S+', note, re.IGNORECASE):
                errors.append("Password (Regex Pattern)")

        # PII Patterns
        if re.search(r'\d{4}-\d{4}-\d{4}-\d{4}', note):
            errors.append("Credit Card Number")
        if re.search(r'(CVV|CVC|CID|security code).{0,10}\d{3,4}', note, re.IGNORECASE):
            errors.append("CVV")
        if re.search(r'(Verification|Verified|PIN|Code).{0,25}\b\d{4}\b', note, re.IGNORECASE):
            errors.append("PIN")

        # Profanity Check
        for word in PROFANITY_LIST:
            if re.search(rf'\b{word}\b', note, re.IGNORECASE):
                errors.append(f"Profanity({word})")

    if errors:
        current_row['Reason_for_Error'] = " / ".join(errors)
        return current_row
    return None

def get_week_of_month(dt):
    """Calculates the week number within the month (1-5)."""
    first_day = dt.replace(day=1)
    dom = dt.day
    adjusted_dom = dom + first_day.weekday()
    return int((adjusted_dom - 1) / 7) + 1

def create_visual_report():
    """Generates Excel Dashboard with labels showing Count and Percentage."""
    if not os.path.exists(MASTER_DATA):
        return

    df = pd.read_csv(MASTER_DATA)
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
    df = df.dropna(subset=['Reason_for_Error'])
    
    df['Week'] = df.apply(lambda x: f"{x['Date'].strftime('%Y-%m')}-Week{get_week_of_month(x['Date'])}", axis=1)
    
    display_df = df.copy()
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    display_df['Note'] = display_df['Note'].fillna('')

    with pd.ExcelWriter(EXCEL_REPORT, engine='xlsxwriter') as writer:
        display_df.sort_values('Date', ascending=False).to_excel(writer, sheet_name='All_NG_Data', index=False)
        
        workbook = writer.book
        dashboard = workbook.add_worksheet('Dashboard')
        
        # --- Summary Data ---
        type_summary = df['Reason_for_Error'].value_counts().reset_index()
        type_summary.columns = ['Error', 'Count']
        type_summary.to_excel(writer, sheet_name='Chart_Data', index=False)
        
        weekly_trend = df.groupby('Week').size().reset_index(name='Total_Errors').sort_values('Week')
        weekly_trend.to_excel(writer, sheet_name='Chart_Data', startcol=3, index=False)

        # --- PIE CHART (Updated with Labels) ---
        pie = workbook.add_chart({'type': 'pie'})
        pie.add_series({
            'categories': ['Chart_Data', 1, 0, len(type_summary), 0],
            'values':     ['Chart_Data', 1, 1, len(type_summary), 1],
            'data_labels': {
                'category': True,    
                'value': True,       
                'percentage': True,  
                'leader_lines': True, 
                'position': 'outside_end', 
            },
        })
        pie.set_title({'name': 'Security Risk Distribution (Count & %)'})
        pie.set_size({'width': 540, 'height': 400})
        dashboard.insert_chart('B2', pie)

        # --- LINE CHART ---
        line = workbook.add_chart({'type': 'line'})
        line.add_series({
            'categories': ['Chart_Data', 1, 3, len(weekly_trend), 3],
            'values':     ['Chart_Data', 1, 4, len(weekly_trend), 4],
            'name':       'Weekly Errors',
            'marker':     {'type': 'circle'},
            'data_labels': {'value': True}, 
        })
        line.set_title({'name': 'Weekly Security Risk Trend'})
        line.set_size({'width': 540, 'height': 400})
        dashboard.insert_chart('J2', line)

    print(f"Success: Professional Report generated as {EXCEL_REPORT}")

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    ng_list = []
    with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if 'Reason_for_Error' not in fieldnames:
            fieldnames.append('Reason_for_Error')
            
        for row in reader:
            result = check_logic(row)
            if result:
                ng_list.append(result)

    if ng_list:
        # 1. Save daily findings
        with open(OUTPUT_FILE, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(ng_list)
        
        # 2. Master Data Accumulation
        new_df = pd.DataFrame(ng_list)
        if os.path.exists(MASTER_DATA):
            old_df = pd.read_csv(MASTER_DATA)
            # Combine, keeping the structure intact, then drop duplicates across all columns
            combined_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates()
        else:
            combined_df = new_df
        
        # Save to Master CSV
        combined_df.to_csv(MASTER_DATA, index=False, encoding='utf-8-sig')
        print(f"Success: {len(ng_list)} items flagged. Master data updated.")
    else:
        print("Success: No security issues detected.")

    create_visual_report()

if __name__ == "__main__":
    main()
