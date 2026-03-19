# Care Plan Generation System — Design Document

**Project:** Automated Care Plan Generator  
**Client:** CVS Specialty Pharmacy  
**Version:** v0.1  
**Status:** Draft

---

## 1. Background & Problem Statement

CVS pharmacists currently spend **20–40 minutes per patient** manually generating care plans. This is:

- Required for **Medicare reimbursement** and **pharma compliance**
- A bottleneck due to **staff shortages** and a growing backlog

This system automates care plan generation using an LLM, triggered by a medical assistant filling out a web form.

---

## 2. Users

| User | Role |
|------|------|
| CVS Medical Assistant / Pharmacist | Inputs patient data, generates and prints care plan |
| Patient | Receives printed care plan — does **not** interact with the system |

---

## 3. Core Workflow

```
Medical Assistant fills web form
  → System validates inputs
  → System checks for duplicates (patient / provider / order)
  → LLM generates Care Plan
  → Assistant downloads / prints Care Plan
  → Export data for pharma reporting
```

---

## 4. Data Model

### 4.1 Inputs (Web Form Fields)

| Field | Type | Validation |
|-------|------|------------|
| Patient First Name | string | Required, letters only |
| Patient Last Name | string | Required, letters only |
| Patient MRN | string | Required, unique 6-digit number |
| Patient Primary Diagnosis | string | Required, valid ICD-10 code |
| Additional Diagnoses | list of strings | Optional, valid ICD-10 codes |
| Referring Provider Name | string | Required |
| Referring Provider NPI | string | Required, exactly 10 digits |
| Medication Name | string | Required |
| Medication History | list of strings | Optional |
| Patient Records | string OR PDF | Optional |

### 4.2 Output: Care Plan

One care plan is generated **per order (per medication)**. Each care plan must contain:

1. **Problem list** / Drug Therapy Problems (DTPs)
2. **Goals** (SMART format)
3. **Pharmacist interventions / plan**
4. **Monitoring plan & lab schedule**

---

## 5. Duplicate Detection Rules

| Scenario | Behavior | Reason |
|----------|----------|--------|
| Same patient + same medication + **same day** | ❌ **ERROR** — must block submission | Definite duplicate submission |
| Same patient + same medication + **different day** | ⚠️ **WARNING** — user can confirm and continue | Likely a refill |
| MRN matches, but name or DOB differs | ⚠️ **WARNING** — user can confirm and continue | Possible data entry error |
| Name + DOB match, but MRN differs | ⚠️ **WARNING** — user can confirm and continue | Possible same patient, different record |
| NPI matches, but Provider name differs | ❌ **ERROR** — must block and correct | NPI is a nationally unique identifier |
| NPI + Provider name both match | ✅ Reuse existing provider record | Normal case |
| MRN + name + DOB all match | ✅ Reuse existing patient record | Normal case |

---

## 6. Functional Requirements

| Feature | Priority | Notes |
|---------|----------|-------|
| Web form with input validation | ✅ Must Have | All fields validated on submit |
| Patient duplicate detection | ✅ Must Have | MRN + name/DOB cross-check |
| Order duplicate detection | ✅ Must Have | Same patient + medication + date |
| Provider deduplication | ✅ Must Have | NPI as unique key |
| LLM care plan generation | ✅ Must Have | Core value of the system |
| Care plan download | ✅ Must Have | User uploads to their own system |
| Export for pharma reporting | ✅ Must Have | Compliance requirement |

---

## 7. Non-Functional / Production Requirements

- **Every input is validated** — format, type, and business rules
- **Integrity rules always enforced** — no inconsistent data in the database
- **Errors are safe, clear, and contained** — no stack traces or PHI exposed to users
- **Code is modular and navigable** — layered architecture (View / Service / Repository)
- **Critical logic covered by tests** — unit tests + integration tests
- **Project runs end-to-end out of the box** — Docker, clone and run

---

## 8. Tech Stack (Planned)

| Layer | Technology |
|-------|------------|
| Backend | Python, Django, Django REST Framework |
| Frontend | React |
| Database | PostgreSQL |
| Async Tasks (local) | Celery + Redis |
| Async Tasks (AWS) | SQS + Lambda |
| LLM | Claude API or OpenAI API |
| Containerization | Docker, Docker Compose |
| Cloud | AWS (EC2, Lambda, RDS, SQS, S3) |
| Infrastructure | Terraform |
| Monitoring | Prometheus + Grafana |
| Testing | pytest |

---

## 9. Out of Scope (for now)

- Patient-facing portal
- Real-time collaboration between pharmacists
- Integration with existing CVS pharmacy systems
- Authentication / role-based access control (Phase 2)

---

## 10. Open Questions (Resolved)

| Question | Answer |
|----------|--------|
| Is care plan per patient or per order? | **Per order (per medication)** |
| Can user bypass a WARNING? | **Yes** — warning shows, user confirms and continues |
| Can user bypass an ERROR? | **No** — must fix before submitting |
| Who uses this system? | CVS medical assistants and pharmacists only |
| What format is the care plan export? | Text file (downloadable) |
