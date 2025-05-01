import csv
import json
import sys
import os

import requests
from fhirclient import client
from fhirclient.models.codeableconcept import CodeableConcept
from fhirclient.models.coding import Coding
from fhirclient.models.condition import Condition
from fhirclient.models.extension import Extension
from fhirclient.models.fhirdatetime import FHIRDate
from fhirclient.models.fhirreference import FHIRReference


def create_fhir_condition(condition_name, patient_id, smart):
    """
    Create a FHIR Condition resource using fhirclient and return JSON data.
    
    Args:
        condition_name (str): Name of the condition (e.g., "Chest Pain")
        patient_id (str): Patient MRN or ID (e.g., "7212")
        smart (FHIRClient): Authenticated smart client connected to FHIR server
        
    Returns:
        dict: Created Condition resource as JSON
    """

    # Step 1: Create a Condition resource object
    condition = Condition()

    # Step 2: Set clinicalStatus to "active"
    condition.clinicalStatus = CodeableConcept({
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
            "code": "active",
            "display": "Active"
        }]
    })

    # Step 3: Set verificationStatus to "confirmed"
    condition.verificationStatus = CodeableConcept({
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
            "code": "confirmed",
            "display": "Confirmed"
        }]
    })

    # Step 4: Set category to "problem-list-item"
    condition.category = [
        CodeableConcept({
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item",
                "display": "Problem List Item"
            }]
        })
    ]

    # Step 5: Set the code (actual condition name)
    condition.code = CodeableConcept({
        "text": condition_name
    })

    # Step 6: Set the subject reference
    condition.subject = FHIRReference({
        "reference": f"Patient/{patient_id}"
    })

    # Step 7: Set onsetDateTime and assertedDate
    condition.onsetDateTime = FHIRDate("2025-04-28")
    condition.assertedDate = FHIRDate("2025-04-28")

    # Step 8: Create the condition on FHIR server
    created_condition = condition.create(smart.server)

    # Step 9: Return the created condition as JSON
    return created_condition.as_json()