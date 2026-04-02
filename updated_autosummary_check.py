import csv
import re
import os

INPUT_FILE = 'Data.csv'
OUTPUT_FILE = 'ng_report.csv'

PROFANITY_LIST = ['JESUS CHRIST', 'DAMN IT', 'GOD damn','HELL','HOLY COW','SHIT','FUCK', 'FUCKING', 
                  'ASSHOLE','BASTARD','CRAP','PISS','IDIOT','DUMB', 'SHUT UP','GET LOST','Bitch', 'lazy']


def check_logic(row):

    errors = []
    
    contact_id =row.get('Contact_ID', '')
    agent_time_str = row.get('Agent_time', '')
    note = row.get('Disp_Comments', '')
    skill = row.get('Skill_Name', '')

    # Check if Contact ID exists
    if not contact_id:
        return None

    # convert agent_time to integer for numerical comparison
    try:
        agent_time = int(agent_time_str)
    except ValueError:
        agent_time = 0
    
    # Check if time is more than 0
    if not note:
        if agent_time > 0:
            errors.append(f"Empty Note (Skill: {skill})")
        else:
            return None
        
    # Check if Profanity exists
    for word in PROFANITY_LIST:
        if re.search(rf'\b{word}\b', note, re.IGNORECASE):
            errors.append(f"Profanity Detected ({word})")

    # Credit Card Check
    if re.search(r'\b(credit card|card number)\b.{0,20}\d{4}-\d{4}-\d{4}-\d{4}', note, re.IGNORECASE):
        errors.append("Credit Card Number")

    # CVV check
    if re.search(r'(CVV|security code).{0,20}\d{3,4}', note, re.IGNORECASE):
        errors.append("CVV")

    # # Phone Number
    # if re.search(r'(\d{3}-\d{3}-\d{4}|d{10})', note):
    #     errors.append("Phone Number")

    # Password check (Detect 4+ non-space chars near the keywords)
    # if re.search(r'(password|passcode|pw).{0,25}\S{4,}', note, re.IGNORECASE):
    #     errors.append("Password")

    # ---- Examples of Passwords -----
    # with a password of ____
    # ask for password, which was provided as "____"
    # create a network with the password "____"
    # new password, "____"
    # password as ____
    # password is "____"
    # password to "____"
    # password was ____
    # password, which was "____"
    # provided password (____)
    # temporary password ____
    # the password "____"
    # temporary one
    # with the password “____"

    if re.search(r'(with a password of|ask for password, which was provided as|new password|password is|password as|password is|password to|password was|password, which was|provided password|temporary password|the password|temporary one|with the password).{0,25}\S{4,}', note, re.IGNORECASE):
        errors.append("Password")

    # PIN check
    if re.search(r'\b(PIN|verification|verified|security code)\b.{0,20}\d{4}', note, re.IGNORECASE):
        errors.append("PIN")

    # If any errors are found, attach the reasons to the row
    if errors:
        row['Reason_for_Error'] = " / ".join(errors)
        return row
    return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not Found")
        return
    
    ng_list = []

    # Open the input file
    with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        original_fieldnames = reader.fieldnames
        for row in reader:
            result = check_logic(row)
            if result:
                ng_list.append(result)


    if ng_list:
        output_fieldnames = list(original_fieldnames)
        if "Reason_for_Error" not in output_fieldnames:
            output_fieldnames.append("Reason_for_Error")
        
        with open(OUTPUT_FILE, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=output_fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            # Ensure to write the correct format only
            # print(ng_list)
            valid_data = [row for row in ng_list if isinstance(row, dict)]
            writer.writerows(valid_data)

        print(f"Inspction Completed: {len(ng_list)} NG items found. See {OUTPUT_FILE}")

    else:
        print("Inspection Completed: No NG found")

if __name__ == "__main__":
    main()






    

        
