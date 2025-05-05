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

# Import FHIR client libraries
from fhirclient.models import (
    patient,
    condition,
    observation,
    medicationrequest,
    allergyintolerance,
    dosage,
)
from fhirclient.models.fhirdate import FHIRDate
from fhirclient.models.fhirdatetime import FHIRDateTime
from fhirclient.models.codeableconcept import CodeableConcept
from fhirclient.models.coding import Coding
from fhirclient.models.quantity import Quantity
from fhirclient.models.fhirreference import FHIRReference
from fhirclient.models.annotation import Annotation

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

    client = openai.OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )  # New: create client instance

    response = client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0
    )

    extracted_json = json.loads(response.choices[0].message.content.strip())


def create_condition_resource(condition_name, patient_id):
    """Create FHIR Condition resource using fhirclient model"""
    # Create a new Condition resource
    cond_resource = condition.Condition()

    # Set resource type
    cond_resource.resource_type = "Condition"

    # Set clinical status
    clinical_status = CodeableConcept()
    clinical_coding = Coding()
    clinical_coding.system = "http://terminology.hl7.org/CodeSystem/condition-clinical"
    clinical_coding.code = "Active"
    clinical_coding.display = "Active"
    clinical_status.coding = [clinical_coding]
    cond_resource.clinicalStatus = clinical_status

    # Set verification status
    verification_status = CodeableConcept()
    verification_coding = Coding()
    verification_coding.system = (
        "http://terminology.hl7.org/CodeSystem/condition-ver-status"
    )
    verification_coding.code = "confirmed"
    verification_coding.display = "Confirmed"
    verification_status.coding = [verification_coding]
    cond_resource.verificationStatus = verification_status

    # Set category
    category = CodeableConcept()
    category_coding = Coding()
    category_coding.system = "http://terminology.hl7.org/CodeSystem/condition-category"
    category_coding.code = "problem-list-item"
    category_coding.display = "Problem List Item"
    category.coding = [category_coding]
    cond_resource.category = [category]

    # Set condition code
    code = CodeableConcept()
    code_coding = Coding()
    code_coding.system = "http://snomed.info/sct"
    code_coding.display = "N/A"
    code.coding = [code_coding]
    code.text = condition_name.title()
    cond_resource.code = code

    # Set subject reference
    subject = FHIRReference()
    subject.reference = f"Patient/{patient_id}"
    cond_resource.subject = subject

    # Set recorded date
    cond_resource.recordedDate = FHIRDateTime(
        datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    return cond_resource.as_json()


def create_medication_request_resources(extracted, patient_id):
    """Create multiple FHIR MedicationRequest resources using fhirclient model"""
    medications = extracted.get("medications", [])
    medication_resources = []

    for medication in medications:
        med_resource = medicationrequest.MedicationRequest()

        # Set resource type
        med_resource.resource_type = "MedicationRequest"

        # Set status
        med_resource.status = "active"

        # Set intent
        med_resource.intent = "order"

        # Set medication concept - now only for this specific medication
        med_concept = CodeableConcept()
        med_concept.text = medication

        med_coding = Coding()
        med_coding.system = "http://www.nlm.nih.gov/research/umls/rxnorm"
        med_coding.display = medication
        med_concept.coding = [med_coding]

        med_resource.medicationCodeableConcept = med_concept

        # Set subject reference
        subject = FHIRReference()
        subject.reference = f"Patient/{patient_id}"
        med_resource.subject = subject

        # Set authored date
        med_resource.authoredOn = FHIRDateTime(
            datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        # Extract dosage information if available in medication string
        dosage_inst = dosage.Dosage()

        # Parse potential dosage information from medication string
        # Example: "Aspirin 325mg" -> extract "325mg" as dosage
        # This is a simple implementation - could be enhanced with regex pattern matching
        dose_text = medication

        # Try to set a more specific dosage instruction if possible
        if " " in medication and any(char.isdigit() for char in medication):
            dosage_inst.text = f"Take {medication} as prescribed."
        else:
            dosage_inst.text = "Take as clinically indicated."

        med_resource.dosageInstruction = [dosage_inst]

        # Add the medication resource to the list
        medication_resources.append(med_resource.as_json())

    return medication_resources


def create_observation_resources(vitals, patient_id):
    """Create multiple FHIR Observation resources using fhirclient model"""
    # Define mapping for vital signs with their LOINC codes
    vital_sign_mappings = {
        "systolic": {
            "code": "8480-6",
            "display": "Systolic blood pressure",
            "unit": "mm[Hg]",
            "system": "http://unitsofmeasure.org",
            "unitCode": "mm[Hg]",
        },
        "diastolic": {
            "code": "8462-4",
            "display": "Diastolic blood pressure",
            "unit": "mm[Hg]",
            "system": "http://unitsofmeasure.org",
            "unitCode": "mm[Hg]",
        },
        "heart_rate": {
            "code": "8867-4",
            "display": "Heart rate",
            "unit": "beats/minute",
            "system": "http://unitsofmeasure.org",
            "unitCode": "/min",
        },
        "respiratory_rate": {
            "code": "9279-1",
            "display": "Respiratory rate",
            "unit": "breaths/minute",
            "system": "http://unitsofmeasure.org",
            "unitCode": "/min",
        },
        "temperature": {
            "code": "8310-5",
            "display": "Body temperature",
            "unit": "F",
            "system": "http://unitsofmeasure.org",
            "unitCode": "[degF]",
        },
        "oxygen_saturation": {
            "code": "2708-6",
            "display": "Oxygen saturation",
            "unit": "%",
            "system": "http://unitsofmeasure.org",
            "unitCode": "%",
        },
    }

    observation_resources = []

    # Create an observation resource for each vital sign
    for vital_name, vital_value in vitals.items():
        if vital_name in vital_sign_mappings and vital_value is not None:
            mapping = vital_sign_mappings[vital_name]

            # Create a new Observation resource
            obs_resource = observation.Observation()

            # Set resource type and ID
            obs_resource.resource_type = "Observation"
            obs_resource.id = vital_name.replace("_", "-")

            # Set status
            obs_resource.status = "final"

            # Set category
            category = CodeableConcept()
            category_coding = Coding()
            category_coding.system = (
                "http://terminology.hl7.org/CodeSystem/observation-category"
            )
            category_coding.code = "vital-signs"
            category_coding.display = "Vital Signs"
            category.coding = [category_coding]
            category.text = "Vital Signs"
            obs_resource.category = [category]

            # Set code
            code = CodeableConcept()
            code_coding = Coding()
            code_coding.system = "http://loinc.org"
            code_coding.code = mapping["code"]
            code_coding.display = mapping["display"]
            code.coding = [code_coding]
            code.text = mapping["display"]
            obs_resource.code = code

            # Set subject reference
            subject = FHIRReference()
            subject.reference = f"Patient/{patient_id}"
            obs_resource.subject = subject

            # Set effective date time
            obs_resource.effectiveDateTime = FHIRDateTime(
                datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            )

            # Set value quantity
            value_quantity = Quantity()
            value_quantity.value = vital_value
            value_quantity.unit = mapping["unit"]
            value_quantity.system = mapping["system"]
            value_quantity.code = mapping["unitCode"]
            obs_resource.valueQuantity = value_quantity

            # Add the observation resource to the list
            observation_resources.append(obs_resource.as_json())

    return observation_resources


def create_allergy_intolerance_resources(extracted, patient_id):
    """Create multiple FHIR AllergyIntolerance resources using fhirclient model"""
    allergies = extracted.get("allergies", [])
    allergy_resources = []

    # If no allergies are present, create a "No Known Allergies" record
    if not allergies:
        allergy_resource = allergyintolerance.AllergyIntolerance()

        # Set resource type
        allergy_resource.resource_type = "AllergyIntolerance"

        # Set clinical status
        clinical_status = CodeableConcept()
        clinical_coding = Coding()
        clinical_coding.system = (
            "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"
        )
        clinical_coding.code = "inactive"
        clinical_status.coding = [clinical_coding]
        allergy_resource.clinicalStatus = clinical_status

        # Set verification status
        verification_status = CodeableConcept()
        verification_coding = Coding()
        verification_coding.system = (
            "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification"
        )
        verification_coding.code = "confirmed"
        verification_status.coding = [verification_coding]
        allergy_resource.verificationStatus = verification_status

        # Set type
        allergy_resource.type = "allergy"

        # Set category
        allergy_resource.category = ["medication"]

        # Set patient reference
        patient_ref = FHIRReference()
        patient_ref.reference = f"Patient/{patient_id}"
        allergy_resource.patient = patient_ref

        # Set recorded date
        allergy_resource.recordedDate = FHIRDateTime(
            datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        # Set note for no known allergies
        note = Annotation()
        note.text = "No known allergies."
        allergy_resource.note = [note]

        allergy_resources.append(allergy_resource.as_json())

    # Create individual allergy resources for each allergy
    else:
        for allergy in allergies:
            allergy_resource = allergyintolerance.AllergyIntolerance()

            # Set resource type
            allergy_resource.resource_type = "AllergyIntolerance"

            # Set clinical status
            clinical_status = CodeableConcept()
            clinical_coding = Coding()
            clinical_coding.system = (
                "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"
            )
            clinical_coding.code = "active"
            clinical_status.coding = [clinical_coding]
            allergy_resource.clinicalStatus = clinical_status

            # Set verification status
            verification_status = CodeableConcept()
            verification_coding = Coding()
            verification_coding.system = (
                "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification"
            )
            verification_coding.code = "confirmed"
            verification_status.coding = [verification_coding]
            allergy_resource.verificationStatus = verification_status

            # Set type
            allergy_resource.type = "allergy"

            # Set category
            allergy_resource.category = ["medication"]

            # Set criticality - default to low unless specified
            allergy_resource.criticality = "low"

            # Set patient reference
            patient_ref = FHIRReference()
            patient_ref.reference = f"Patient/{patient_id}"
            allergy_resource.patient = patient_ref

            # Set recorded date
            allergy_resource.recordedDate = FHIRDateTime(
                datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            )

            # Create a reaction for this specific allergy
            reaction = allergyintolerance.AllergyIntoleranceReaction()
            manifestation_concept = CodeableConcept()
            manifestation_concept.text = allergy
            reaction.manifestation = [manifestation_concept]
            allergy_resource.reaction = [reaction]

            # Create FHIR code for the allergy
            code = CodeableConcept()
            code.text = allergy
            allergy_resource.code = code

            allergy_resources.append(allergy_resource.as_json())

    return allergy_resources


def create_patient_json(user_data):
    """Create Patient registration JSON from user data"""
    # Since this function seems to create a custom JSON for an external API,
    # not directly related to FHIR client, we'll keep it as is
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
    # url = f"http://127.0.0.1:8080/fhir/{resource_type}/"
    url = os.getenv("FHIR_SERVER_URL") + resource_type
    headers = {"Content-Type": "application/fhir+json;charset=UTF-8"}
    response = requests.post(url, headers=headers, json=resource_json)
    return response.status_code, response.text


def create_patient(resource_json):
    """POST patient registration to registration service"""
    url = os.getenv("REGISTRATION_URL")  # Don't add anything, already correct
    headers = authToken.lof_service_request_headers()
    response = requests.post(url, headers=headers, json=resource_json)
    return response.status_code, response.text


def get_patient_id(email):
    """Get patient ID by email"""
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
    """Process clinical note and create FHIR resources"""
    file = request.files["pdf"]
    user_data = request.form.get("user_data")
    user_data = json.loads(user_data)

    # Create patient registration JSON
    registration_json = create_patient_json(user_data)

    # Extract text from PDF and analyze with OpenAI
    extracted_text = extract_text_from_pdf(file)
    extracted = call_openai_to_extract(extracted_text)

    # Register patient
    reg_status, reg_resp = create_patient(registration_json)

    # Get patient ID
    patient_id = get_patient_id(user_data["email"])

    # Create and post all conditions
    conditions_responses = []
    for condition_name in extracted["conditions"]:
        condition_resource = create_condition_resource(condition_name, patient_id)
        cond_status, cond_resp = post_to_fhir(condition_resource, "Condition")
        conditions_responses.append({"status": cond_status, "response": cond_resp})
        if cond_status != 201:
            print(f"Failed to post condition: {cond_resp}")

    # Create and post medication request
    medication_resources = create_medication_request_resources(extracted, patient_id)
    medication_responses = []

    for med_resource in medication_resources:
        med_status, med_resp = post_to_fhir(med_resource, "MedicationRequest")
        medication_responses.append({"status": med_status, "response": med_resp})
        if med_status != 201:
            print(f"Failed to post medication request: {med_resp}")

    # Create and post multiple observations for vitals
    observation_resources = create_observation_resources(
        extracted["vitals"], patient_id
    )
    observation_responses = []

    for obs_resource in observation_resources:
        obs_status, obs_resp = post_to_fhir(obs_resource, "Observation")
        observation_responses.append({"status": obs_status, "response": obs_resp})
        if obs_status != 201:
            print(f"Failed to post observation: {obs_resp}")

    # Create and post allergy intolerance
    allergy_resources = create_allergy_intolerance_resources(extracted, patient_id)
    allergy_responses = []

    for allergy_resource in allergy_resources:
        allergy_status, allergy_resp = post_to_fhir(
            allergy_resource, "AllergyIntolerance"
        )
        allergy_responses.append({"status": allergy_status, "response": allergy_resp})
        if allergy_status != 201:
            print(f"Failed to post allergy intolerance: {allergy_resp}")

    # Return response with all statuses
    return jsonify(
        {
            "registration": {"status": reg_status, "response": reg_resp},
            "conditions": conditions_responses,
            "medications": medication_responses,
            "observations": observation_responses,
            "allergyIntolerances": allergy_responses,
        }
    )


if __name__ == "__main__":
    app.run(port=4040, debug=True)
