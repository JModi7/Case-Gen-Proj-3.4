# Case Generator for Simulations

An AI-powered simulation platform that transforms real clinical case transcripts into interactive, feedback-driven patient encounters. Designed to help medical students practice clinical reasoning, communication, and decision-making — before they ever meet a real patient.

---

## Project Overview

Medical education often relies on mannequins, peer role-play, and scripted exercises — tools that fall short in replicating real clinical complexity.  
This tool bridges that gap by using **Large Language Models (LLMs)** to simulate realistic patient behavior and dialogue, enabling:

-   Anytime, anywhere clinical skill development
-   Structured feedback aligned to medical training standards
-   Scalable deployment across institutions

---

## Group Members

-   **Harsh Patel**
-   **Jainil Modi** - A20586989
-   **Saloni Patel** - A20558369
-   **Snehal Phadtare**
-   **Swapnil Jadhav**

### Acknowledgments

We extend our gratitude to our mentors and collaborators for their invaluable guidance and support:

-   **Frank Rad**
-   **John Trzesniak**
-   **Abhinav**
-   **Nikolina**

---

## Core Features

-   **Transcript-to-Simulation:** Convert real Suki-generated transcripts into simulation-ready cases
-   **AI-Powered Patient Interaction:** Engage with dynamic, context-aware simulated patients
-   **Real-Time Feedback:** Structured reports mapped to H&P clinical competencies
-   **FHIR JSON Export:** Interoperable output for Care Compliance Dashboards (CCD)
-   **Secure, Scalable Access:** Web and mobile access with HIPAA/FERPA-compliant architecture

---

## Tech Stack

-   **LLMs:** GPT-4o-mini
-   **FHIR:** Fast Healthcare Interoperability Resources
-   **Web Frameworks:** Streamlit / Flask
-   **Backend Logic:** Python
-   **Database:** PostgreSQL
-   **Authentication:** OAuth2, HIPAA-compliant handling

---

## Citations

-   AAMC Graduation Questionnaire, 2022
-   Makary & Daniel. _BMJ_, 2016: Medical Error as a Leading Cause
-   Cook et al. _JAMA_, 2011: Simulation improves diagnostic accuracy
-   Ziv et al. _Medical Education_, 2003: Ethical imperative for simulation

---

## File Structure

```
.
├── README.md
├── app/
│   ├── frontend/
│   │   ├── index.py
│   └── backend/
│       ├── main.py
│       ├── authToken.py
```

---

## Risks & Mitigation

| **Risk**               | **Mitigation**                             |
| ---------------------- | ------------------------------------------ |
| High AI API Costs      | Usage capping, prompt optimization         |
| Inconsistent Dialogues | Clinical tuning and scripted reinforcement |
| Adoption Resistance    | Faculty onboarding, early pilot programs   |
| Privacy & Compliance   | HIPAA/FERPA audits and secure storage      |

---
