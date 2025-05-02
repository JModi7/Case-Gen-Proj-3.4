from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import requests
import json
import openai
from datetime import datetime
import authToken
import os
import dotenv

dotenv.load_dotenv()


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
        "patient_name": string,
        "dob": string,
        "gender": string,
        "encounter_date": string,
        "encounter_type": string,
        "conditions": list,
        "medications": list,
        "vitals": {{
            "systolic": integer,
            "diastolic": integer,
            "heart_rate": integer,
            "respiratory_rate": integer,
            "temperature": integer,
            "oxygen_saturation": integer
        }},
        "allergies": list,
        "procedures_performed": list,
        "tests_ordered": list,
        "care_plan": list
        }}

        Here is the clinical note:
        {text}
        """
    client = openai.OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )  # New: create client instance

    response = client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0
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
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"Data successfully saved to '{filename}'")
    except Exception as e:
        print(f"An error occurred while saving to '{filename}': {e}")


file = "./SmithJohn2025428.pdf"
extracted_text = extract_text_from_pdf(file)
extracted = call_openai_to_extract(extracted_text)

file_path = "temp_1.json"
save_json(extracted, file_path)
