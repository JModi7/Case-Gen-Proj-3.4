from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import requests
import json
import openai
from datetime import datetime
import authToken

def extract_text_from_pdf(file):
    """Extract raw text from uploaded PDF"""
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

def call_openai_to_extract(text):
    """Send extracted text to OpenAI API to parse clinical information"""
    prompt = f"""
        You are a medical coding assistant. Analyze the following clinical note and extract structured data suitable for generating HL7 FHIR R4 resources.

        Extract the following fields in **valid JSON format** (no explanation, only JSON):

        - patient_name: Full name of the patient  
        - dob: Date of birth in YYYY-MM-DD  
        - gender: "male" or "female"  
        - encounter_date: Date of clinical encounter in YYYY-MM-DD  
        - encounter_type: One of ["emergency", "outpatient", "inpatient"]  
        - conditions: List of diagnosis terms (e.g., ["Hypertension", "ACS"])  
        - medications: List of medication names prescribed or administered  
        - vitals: Object with the following keys and numeric values:  
        - systolic  
        - diastolic  
        - heart_rate  
        - respiratory_rate  
        - temperature  
        - oxygen_saturation  
        - allergies: List of allergies, or an empty list if not mentioned  
        - procedures_performed: List of procedures already performed (e.g., EKG, IV access, cardiac monitoring)  
        - tests_ordered: List of lab or imaging tests ordered (e.g., troponin I, CBC, BMP, chest X-ray)  
        - care_plan: List of care plan steps (e.g., consult cardiology, repeat troponin, lifestyle modifications)  

        Format your answer strictly in this JSON structure:
        {{
        "patient_name": "John Smith",
        "dob": "1970-01-18",
        "gender": "male",
        "encounter_date": "2025-04-28",
        "encounter_type": "emergency",
        "conditions": ["Chest Pain", "Hypertension", "Hyperlipidemia"],
        "medications": ["Aspirin", "Nitroglycerin", "Morphine"],
        "vitals": {{
            "systolic": 148,
            "diastolic": 92,
            "heart_rate": 102,
            "respiratory_rate": 20,
            "temperature": 98.4,
            "oxygen_saturation": 96
        }},
        "allergies": [],
        "procedures_performed": ["12-lead EKG", "IV access", "Cardiac monitoring"],
        "tests_ordered": ["Troponin I", "CBC", "BMP", "Chest X-ray"],
        "care_plan": [
            "Consult cardiology",
            "Repeat troponins in 3 and 6 hours",
            "Continuous telemetry monitoring",
            "Lifestyle modifications"
        ]
        }}

        Here is the clinical note:
        {text}
        """
    client = openai.OpenAI(api_key="")  # New: create client instance

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    extracted_json = json.loads(response.choices[0].message.content.strip())
    return extracted_json

def save_json(data, filename):
    """
    Saves data to a JSON file.

    Args:
        data: The data to be saved (e.g., dictionary, list).
        filename: The name of the file to save to (e.g., "data.json").
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"Data successfully saved to '{filename}'")
    except Exception as e:
        print(f"An error occurred while saving to '{filename}': {e}")



file = "./SmithJohn2025428.pdf"
extracted_text = extract_text_from_pdf(file)
extracted = call_openai_to_extract(extracted_text)

file_path = "temp.json"
save_json(extracted, file_path)