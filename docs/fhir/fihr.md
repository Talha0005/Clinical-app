# FHIR Patient Resource: Protocol & Structure

## 1. FHIR Protocol Overview
- **FHIR**: HL7’s modern healthcare interoperability standard.
- Uses **RESTful APIs**, HTTP methods, and formats like JSON/XML.
- Built upon **Resources**, **Profiles/Extensions**, and **Implementation Guides**.

## 2. Patient Resource Structure
- Represents demographic/admin data for subjects of care.
- Core fields include:
  - *identifier*, *name*, *telecom*, *gender*, *birthDate*
  - *address*, *maritalStatus*, *multipleBirth*, *contact*, *communication*
  - Links to *generalPractitioner*, *managingOrganization*, *Person*, *RelatedPerson*.
- Customisable via jurisdictional **profiles** (e.g. US Core) and **extensions**.

## 3. Interoperability & Implementation Advantages
- Modular structure promotes scalable, real-time data use.
- Integrates well with modern web and security standards.
- Underpins use-cases like patient portals, referrals, and analytics.

## References
- Base FHIR and Patient structure: FHIR Specification :contentReference[oaicite:32]{index=32}  
- Customisation via Profiles & IGs: HL7 FHIR components :contentReference[oaicite:33]{index=33}  
- RESTful protocol and resource interaction: FHIR data model & deep dive :contentReference[oaicite:34]{index=34}  
- Extensions and regional profiles (e.g. US Core): US Core Patient guidance :contentReference[oaicite:35]{index=35}  
- Benefits of modern architecture and implementation: CapMinds, Sigma guides :contentReference[oaicite:36]{index=36}  
- Developer best practices & resources: FHIR developer practices :contentReference[oaicite:37]{index=37}  

Here’s a project-ready markdown section that explains **your JSON model** (the Bundle you shared) — what each bit is for, how it relates to FHIR, and the intent behind the design. I’ve kept UK spelling and cited the relevant FHIR pages for the key ideas.

---

# Our Patient Bundle: Structure & Intent (FHIR-shaped, file-based JSON)

We store a **FHIR-shaped Bundle** of resources as plain JSON files. Using a Bundle keeps related items together while allowing each entry to stand alone if needed. We use **`type: "collection"`** because it’s simply “a set of resources collected into a single package” for persistence/sharing, not a transaction. ([build.fhir.org][1], [hapifhir.io][2])

## A. Bundle header

* **`resourceType: "Bundle"` / `type: "collection"` / `timestamp`** — groups the patient and all related facts captured at a point in time. In FHIR, a *collection* imposes no special processing rules beyond persistence, which suits a file-store. ([build.fhir.org][1])

---

## B. Core identities

### Patient (`Patient/patient-001`)

Holds demographics and admin data for the person receiving care: name, gender, date of birth. In FHIR, **Patient** is the canonical record for the subject of care, even when different local terms (member, subscriber) are used. ([build.fhir.org][3])

**Intent:** Provide a stable anchor (`Patient/patient-001`) that other resources reference (via `subject` or `patient`) so you can pull a coherent longitudinal record.

### Practitioner (`Practitioner/practitioner-001`) and Organisation (`Organization/organization-001`)

Clinicians and provider entities that participate in care. They’re referenced (e.g., as performers, authors, or participants) by clinical and scheduling resources. ([build.fhir.org][3])

**Intent:** Identify “who” delivered care and “which” organisation is responsible, enabling audit, attribution and filtering by provider.

---

## C. Clinical history & problems

### Conditions (e.g., `Condition/condition-001`, `-002`, `-003`)

Record problems/diagnoses (e.g., hypertension, type 2 diabetes, suspected upper respiratory infection). We set:

* `code` (prefer Terminologies like SNOMED CT),
* `clinicalStatus` (e.g., active),
* `subject → Patient/...`,
* optional `encounter` link when the diagnosis was made within a specific visit.
  In FHIR, **Condition** tracks problems/diagnoses that have risen to a level of clinical concern. ([build.fhir.org][4])

**Intent:** Maintain a clear, queryable problem list over time, with optional encounter context for provenance.

### Procedure (`Procedure/procedure-001`)

Captures past or current procedures (e.g., appendicectomy), linking back to the patient via `subject`. ([build.fhir.org][4])

**Intent:** Preserve important historical interventions that inform risk, follow-up and contraindications.

### FamilyMemberHistory (`FamilyMemberHistory/familymemberhistory-001`)

Represents familial conditions (e.g., father with type 2 diabetes) linked via `patient`. This influences risk profiles and screening. ([build.fhir.org][4])

**Intent:** Encode family history drivers for risk assessment and care planning.

---

## D. Encounters (visits) & observations

### Encounter (`Encounter/encounter-001`, `-002`)

The **actual interaction** with the healthcare system (finished or in-progress), with `class`, `period`, `reasonCode`, and `subject → Patient/...`. Encounters provide the clinical context for findings and diagnoses. (FHIR treats **booking** separately as `Appointment`; an Encounter is the delivered care event.) ([build.fhir.org][3])

**Intent:** Time-box clinical activity so measurements, diagnoses and orders can be traced to a specific visit.

### Observation (e.g., smoking status, blood pressure, HbA1c)

Atomic clinical measurements or assertions with:

* `code` (ideally LOINC/SNOMED where applicable),
* `value[x]` (e.g., `valueQuantity`, `valueString`, `valueCodeableConcept`),
* `effectiveDateTime`,
* `subject → Patient/...`.
  Observation is the workhorse for vitals, labs and many clinical facts. ([build.fhir.org][5])

**Intent:** Keep measurements normalised and time-stamped for trending, rules and analytics.

---

## E. Allergies & sensitivities

### AllergyIntolerance (`AllergyIntolerance/allergyintolerance-001`)

Records a patient’s allergies/intolerances with `code`, `clinicalStatus`, `verificationStatus`, optional `reaction[]`, and `patient → Patient/...`. ([build.fhir.org][3])

**Intent:** Capture decision-critical sensitivities that must be checked before prescribing or administering.

---

## F. Medications

### MedicationRequest (`MedicationRequest/medicationrequest-001`)

Represents an order/request for medication (e.g., metformin), with:

* `medicationCodeableConcept` (use national drug dictionaries where available),
* `status`,
* `authoredOn`,
* `subject → Patient/...`.
  In FHIR, **MedicationRequest** is the order; usage is separately represented by **MedicationAdministration**/**MedicationStatement** if required. ([build.fhir.org][6])

**Intent:** Model the “prescribed” view simply; you can layer in dispense/administration later without changing identifiers or links.

---

## G. Plans of care

### CarePlan (`CarePlan/careplan-001`)

Describes intended management (e.g., chronic disease management over a defined period) linked via `subject → Patient/...`. CarePlans often reference goals/activities and related problems. ([build.fhir.org][3])

**Intent:** Summarise longitudinal intent and activities (e.g., reviews, education, monitoring) across encounters.

---

## H. Linking model (how it all hangs together)

* **Back-references to the patient**:
  Most clinical resources point at the patient using **`subject`** (Condition, Observation, Procedure) or **`patient`** (AllergyIntolerance, Immunization). This is the standard FHIR linking pattern. ([build.fhir.org][3])
* **Encounter context**:
  When a problem or observation is tied to a specific visit, include `encounter` on that resource. This improves provenance and workflow reconstruction. ([build.fhir.org][3])
* **Codes where possible**:
  Prefer standard code systems (e.g., **SNOMED CT** for conditions/procedures; **LOINC** for labs/measurements) to make data computable and interoperable. (FHIR Observation/Condition pages highlight use of standard terminologies.) ([build.fhir.org][5])

---

## I. Why a single file “collection” works for us

* **Portable**: One Bundle file travels as a self-contained package across environments or services. ([build.fhir.org][1])
* **Composable**: Each entry remains a normal resource; later you can expose a FHIR API without re-modelling. ([build.fhir.org][1])
* **Incremental**: You can append or curate entries over time; it mirrors how a record grows without forcing a specific server behaviour. ([build.fhir.org][1])

---

## J. Minimal validation rules (pragmatic)

* Every clinical entry **must reference** the patient (`subject` or `patient`). This emulates FHIR’s **Patient compartment** pattern and keeps queries simple. ([build.fhir.org][3])
* Each resource should have a **stable `id`** within the file so cross-links (e.g., Condition → Encounter) remain resolvable. (This mirrors how resource identities work in FHIR.) ([build.fhir.org][3])
* Use **codes + human-readable `text`** together where practical — machines can compute, clinicians can read. (Common guidance on Observation/Condition coding.) ([build.fhir.org][5])

---

## K. Extending later (roadmap)

* Add **MedicationDispense/Administration/Statement** to reflect what was supplied, given, or actually taken — all remain linked to the same patient and often derived from the MedicationRequest. ([build.fhir.org][6])
* Introduce **DiagnosticReport** to wrap lab panels and reference your Observation results; add **Specimen** if you need sample provenance. ([build.fhir.org][5])
* Publish a lightweight **CapabilityStatement** if/when you expose a FHIR-style API so clients know what you support. ([build.fhir.org][3])

---

### References

* FHIR **Bundle** (R5 build; *collection* behaviour and grouping rationale). ([build.fhir.org][1])
* FHIR **Patient** (purpose and use as subject of care). ([build.fhir.org][3])
* FHIR **Condition** (scope & usage for problem lists/diagnoses). ([build.fhir.org][4])
* FHIR **Observation** (value, coding, effective time; workhorse of measurements). ([build.fhir.org][5])
* FHIR **MedicationRequest** (orders vs administration/statement/dispense). ([build.fhir.org][6])

---

If you’d like, I can drop this into your existing document and add a small legend that maps **your fields** to the **nearest FHIR element names** for quick developer onboarding.

[1]: https://build.fhir.org/bundle.html?utm_source=chatgpt.com "Bundle - FHIR v6.0.0-ballot2"
[2]: https://hapifhir.io/hapi-fhir/apidocs/hapi-fhir-structures-r4/org/hl7/fhir/r4/model/Bundle.BundleType.html?utm_source=chatgpt.com "Bundle.BundleType (HAPI FHIR Structures - FHIR R4 8.5.0-SNAPSHOT API)"
[3]: https://build.fhir.org/patient.html?utm_source=chatgpt.com "Patient - FHIR v6.0.0-ballot2"
[4]: https://build.fhir.org/condition.html?utm_source=chatgpt.com "Condition - FHIR v6.0.0-ballot2"
[5]: https://build.fhir.org/observation.html?utm_source=chatgpt.com "Observation - FHIR v6.0.0-ballot2"
[6]: https://build.fhir.org/medicationrequest.html?utm_source=chatgpt.com "MedicationRequest - FHIR v6.0.0-ballot2"
