from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import requests
import json
import openai
from datetime import datetime
import authToken
import dotenv
import os

dotenv.load_dotenv()

app = Flask(__name__)
CORS(app, origins=[os.getenv("FRONTEND_URL")])


# === BACKEND FUNCTIONS ===
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

    # client = openai.OpenAI(
    #     api_key=os.getenv("OPENAI_API_KEY"),
    # )  # New: create client instance

    # response = client.chat.completions.create(
    #     model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0
    # )

    # extracted_json = json.loads(response.choices[0].message.content.strip())

    return json.loads(
        open("/home/Kira/RamDisk/project3_4/src/backend/temp.json").read()
    )


def create_condition_json(condition_name, patient_id):
    """Create FHIR Condition JSON"""
    return {
        "resourceType": "Condition",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "Active",
                    "display": "Active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                    "display": "Confirmed",
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": "problem-list-item",
                        "display": "Problem List Item",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {"system": "http://snomed.info/sct", "display": "N/A"},
            ],
            "text": condition_name.title(),
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "recordedDate": datetime.now().strftime("%Y-%m-%d"),
    }


def create_medication_request_json(extracted, patient_id):
    """Create FHIR MedicationRequest JSON"""
    return {
        "resourceType": "MedicationRequest",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "display": med,
                }
                for med in extracted["medications"]
            ],
            "text": ", ".join(extracted["medications"]),
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "authoredOn": datetime.now().strftime("%Y-%m-%d"),
        "dosageInstruction": [{"text": "As clinically indicated."}],
    }


def create_observation_json(vitals, patient_id):
    """Create FHIR Observation JSON"""
    data = {
        "resourceType": "Observation",
        "id": "heart-rate",
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/vitalsigns"]},
        "text": {
            "status": "generated",
            "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p><b>Generated Narrative with Details</b></p><p><b>id</b>: heart-rate</p><p><b>meta</b>: </p><p><b>status</b>: final</p><p><b>category</b>: Vital Signs <span>(Details : {http://terminology.hl7.org/CodeSystem/observation-category code 'vital-signs' = 'Vital Signs', given as 'Vital Signs'})</span></p><p><b>code</b>: Heart rate <span>(Details : {LOINC code '8867-4' = 'Heart rate', given as 'Heart rate'})</span></p><p><b>subject</b>: <a>Patient/example</a></p><p><b>effective</b>: 02/07/1999</p><p><b>value</b>: 44 beats/minute<span> (Details: UCUM code /min = '/min')</span></p></div>",
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ],
                "text": "Vital Signs",
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate",
                }
            ],
            "text": "Heart rate",
        },
        "subject": {"reference": "Patient/example"},
        "effectiveDateTime": "1999-07-02",
        "valueQuantity": {
            "value": vitals["heart_rate"],
            "unit": "beats/minute",
            "system": "http://unitsofmeasure.org",
            "code": "/min",
        },
    }

    obs_status, obs_resp = post_to_fhir(data, "Observation")
    if obs_status != 201:
        print(f"Failed to post observation: {obs_resp}")


def create_allergy_intolerance_json(extracted, patient_id):
    """Create FHIR AllergyIntolerance JSON"""
    allergies = extracted.get("allergies", [])
    return {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": "active" if allergies else "inactive",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "confirmed" if allergies else "unconfirmed",
                }
            ]
        },
        "type": "allergy",
        "category": ["medication"],
        "criticality": "low",
        "patient": {"reference": f"Patient/{patient_id}"},
        "recordedDate": datetime.now().strftime("%Y-%m-%d"),
        "reaction": (
            [{"manifestation": [{"text": allergy}]} for allergy in allergies]
            if allergies
            else []
        ),
        "note": [{"text": "No known allergies."}] if not allergies else [],
    }


def create_patient_json(user_data):
    """Create Patient registration JSON from user data"""
    patient_json = {
        "username": user_data["username"],
        "email": user_data["email"],
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "password1": user_data["password"],  # password from frontend
        "password2": user_data["password"],  # repeat password
        "dob": user_data["birth_date"],  # birth_date already in YYYY-MM-DD
        "gender": user_data["gender"],
        "mrn": "",  # (Optional: populate if you have medical record number)
        "user_profile": {
            "preferred_alert_mode": user_data[
                "preferred_alert_mode"
            ].capitalize(),  # Capitalize for consistency
            "secondary_alert_mode": user_data["secondary_alert_mode"].capitalize(),
            "address": user_data.get("address", ""),
            "phone": user_data.get("phone", ""),
        },
    }
    return patient_json


def post_to_fhir(resource_json, resource_type):
    """POST generated JSON to FHIR server"""
    url = f"{os.getenv('FHIR_SERVER_URL')}/{resource_type}"
    headers = {"Content-Type": "application/fhir+json;charset=UTF-8"}
    response = requests.post(url, headers=headers, json=resource_json)
    return response.status_code, response.text


def create_patient(resource_json):

    url = os.getenv("REGISTRATION_URL")  # Don't add anything, already correct
    # headers = {"Content-Type": "application/fhir+json;charset=UTF-8",
    #            "Authorization": f"Bearer {auth_token}"}

    headers = authToken.lof_service_request_headers()
    response = requests.post(url, headers=headers, json=resource_json)
    # print(response)
    return response.status_code, response.text


def get_patient_id(email):

    headers = {"Accept": "application/fhir+json"}
    response = requests.get(os.getenv("GET_PATIENT_URL") + str(email), headers=headers)
    if response.status_code == 200:
        bundle = response.json()
        if bundle.get("total", 0) > 0:
            # Return the first matching Patient resource
            return bundle["entry"][0]["resource"]["id"]
        else:
            return {"message": "No patient found with this email."}
    else:
        return {
            "error": f"Failed to query FHIR server. Status code: {response.status_code}"
        }


# === API ENDPOINT ===
@app.route("/process_note", methods=["POST"])
def process_note():

    file = request.files["pdf"]
    user_data = request.form.get("user_data")
    user_data = json.loads(user_data)

    registration_json = create_patient_json(user_data)

    extracted_text = extract_text_from_pdf(file)
    extracted = call_openai_to_extract(extracted_text)

    reg_status, reg_resp = create_patient(registration_json)

    patient_id = get_patient_id(user_data["email"])

    for key in extracted["conditions"]:
        condition_json = create_condition_json(key, patient_id)
        print(condition_json)
        cond_status, cond_resp = post_to_fhir(condition_json, "Condition")
        if cond_status != 201:
            print(f"Failed to post condition: {cond_resp}")

    # for key in extracted["medications"]:
    #     medication_json = create_medication_request_json(key, patient_id)
    #     print(medication_json)
    #     med_status, med_resp = post_to_fhir(medication_json, "MedicationRequest")
    #     if med_status != 201:
    #         print(f"Failed to post medication request: {med_resp}")

    # for key in extracted["allergies"]:
    #     allergy_json = create_allergy_intolerance_json(extracted, patient_id)

    # print(condition_json,medication_json,observation_json,allergy_json)

    # Post to FHIR Server
    create_observation_json(extracted["vitals"], patient_id)
    # med_status, med_resp = post_to_fhir(medication_json, "MedicationRequest")
    # allergy_status, allergy_resp = post_to_fhir(allergy_json, "AllergyIntolerance")

    return jsonify(
        {
            "registration": {"status": reg_status, "response": reg_resp},
            "Condition": {"status": cond_status, "response": cond_resp},
            # "MedicationRequest": {"status": med_status, "response": med_resp},
            # "Observation": {"status": obs_status, "response": obs_resp},
            # "AllergyIntolerance": {"status": allergy_status, "response": allergy_resp},
        }
    )


if __name__ == "__main__":
    app.run(port=4040, debug=True)
