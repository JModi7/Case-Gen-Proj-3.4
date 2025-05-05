# 🧠 AI Simulation Tool for Medical Education

## 📘 Overview

This project is an AI-powered simulation platform that transforms real clinical transcripts into dynamic, interactive patient encounters. It allows medical students to practice diagnostic reasoning, patient communication, and decision-making in a safe, repeatable environment using real-time feedback.

-   Converts real transcripts (e.g., Suki output) into simulations.
-   Uses LLMs (e.g., OpenAI) to simulate patient dialogue.
-   Exports structured feedback in FHIR JSON format.
-   Can be extended to integrate with clinical dashboards like CCD.

---

## 🏗️ Project Structure

```bash
.
├── README.md                     # Project summary
├── DOCUMENTATION.md              # You are here!
├── requirements.txt              # Python dependencies
├── .env                          # API keys and config (excluded from version control)
├── .gitignore                    # Ignored files
├── createAllergyIntolerance.json # FHIR resource sample
├── createCondition.json
├── createMedicationRequest.json
├── createObservation.json
├── app/
│   ├── frontend/
│   │   └── index.py              # UI logic (currently minimal)
│   └── backend/
│       ├── main.py               # Entry point for simulation
│       ├── authToken.py          # API token management
│       ├── test.py               # Unit tests or prototyping
│       ├── data.json             # Sample case input
│       └── SmithJohn2025428.pdf # Case transcript (source)
├── venv/                         # Virtual environment (excluded from git)
```

---

## 🔧 Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/JModi7/Case-Generation
cd Case-Generation
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up `.env`

Create a `.env` file in the root with the following:

```
OPENAI_API_KEY=api-key-here
OTHER_API_URL=https://api.example.com

FRONTEND_URL   = "http://localhost:8501"

client_id     = client-id-for-fhir
client_secret = client-secret-for-fhir

FHIR_SERVER_URL  = "http://127.0.0.1:8080/fhir/"
REGISTRATION_URL = "http://127.0.0.1:8000/api/patient/registration/"

GET_PATIENT_URL = "http://localhost:8080/fhir/Patient?email="
```

---

## 🚀 Running the App

### 1. Run Backend Simulation

```bash
python app/backend/main.py
```

This script:

-   Loads a clinical transcript from uploaded files (Suki-generated PDF)
-   Sends it to a prompt handler for LLM processing
-   Returns simulated patient dialogue
-   Stores outputs and generates FHIR JSON templates

### 2. Run Frontend

```bash
streamlit run app/frontend/index.py
```

---

## 📂 File/Module Descriptions

| File/Folder           | Purpose                                               |
| --------------------- | ----------------------------------------------------- |
| `main.py`             | Central script for case processing and AI interaction |
| `authToken.py`        | Manages and refreshes access tokens for APIs          |
| `data.json`           | Sample input case data in structured form             |
| `*.json` (FHIR files) | Sample FHIR-formatted resources                       |
| `index.py`            | Placeholder for frontend                              |
| `.env`                | API keys and config (keep secret)                     |

---

## 🏛️ Architecture Summary

```
User Input (Case Selection)
        ↓
Transcript Loader → Prompt Builder → LLM API (OpenAI, etc.)
        ↓
AI Patient Responses → Feedback Analyzer → FHIR Output
        ↓
FHIR JSON → CCD Dashboard / Export
```

# Function-Level Documentation

### `extract_text_from_pdf(file)`

Extracts raw text content from an uploaded clinical note in PDF format using `pdfplumber`.

---

### `call_openai_to_extract(text)`

Sends extracted clinical text to an OpenAI-based LLM with a prompt to return structured medical data (JSON) for FHIR generation.

---

### `create_condition_resource(condition_name, patient_id)`

Generates a FHIR `Condition` resource using `fhirclient`, associated with a given patient.

---

### `create_medication_request_resources(extracted, patient_id)`

Generates multiple FHIR `MedicationRequest` resources from parsed medication data. It includes fallback dosage handling and patient linkage.

---

### `create_observation_resources(vitals, patient_id)`

Generates a list of `Observation` resources for each vital sign using LOINC codes and standard FHIR practices.

---

### `create_allergy_intolerance_resources(extracted, patient_id)`

Creates allergy records based on parsed input. Includes a "No Known Allergies" fallback if none are reported.

---

### `create_patient_json(user_data)`

Takes frontend form data and builds a custom patient registration JSON for external auth/register APIs (not FHIR-native).

---

### `post_to_fhir(resource_json, resource_type)`

Performs a `POST` operation to the FHIR API to store resource data (e.g., Condition, Observation). Uses environment-configured URL.

---

### `create_patient(resource_json)`

Sends user registration data to an external registration API with required headers.

---

### `get_patient_id(email)`

Looks up the FHIR server to get a unique `Patient ID` for a given email address.

---

### `process_note()`

**Flask API Endpoint: `/process_note` (POST)**  
Main entrypoint for the backend. This function orchestrates the full pipeline:

-   Registers patient
-   Extracts clinical content from uploaded PDF
-   Sends it to LLM for structured parsing
-   Posts resources (Condition, Observation, Medication, Allergy) to the FHIR API
-   Returns JSON of all statuses

---

### Streamlit UI Form (`user_form`)

A form that:

-   Collects patient demographics, preferences, and alerts
-   Uploads clinical note in PDF
-   Validates inputs
-   Sends metadata and file to `/process_note` backend endpoint

---

### PDF Upload & Processing

On form submission:

-   If valid, displays a spinner while backend processes
-   Upon success, shows success message and conditional registration confirmation
-   Handles error messages clearly using `st.error()`

---

## ⚠️ Known Limitations

-   Emotionally nuanced patient responses may vary in realism.
-   LLMs must be monitored to prevent hallucinated clinical data.
-   Cost depends on token usage from AI API (main expense).
-   Requires internet access for live LLM interaction.

---

## 🔐 Compliance Notes

-   All outputs are local and anonymized.
-   Designed to be HIPAA- and FERPA-friendly (pending institutional review).
-   No patient-identifiable data is shared with external APIs.
