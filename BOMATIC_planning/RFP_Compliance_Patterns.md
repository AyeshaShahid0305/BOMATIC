# RFP Compliance Patterns

**Version:** 1.0.0
**Date:** 2026-05-14
**Source:** Extracted from `docs/E1_RFP_Parser_Process_Flow.md` — all inline patterns organized into a single reference library.
**Used by:** E1 steps 1, 2, 3, 4, and 6. Cross-referenced as `RFP_Compliance_Patterns.md §1–§9`.

> **Pattern notation:** All patterns are written as JavaScript/TypeScript regex strings (case-insensitive flag `i` applied at runtime unless noted). Flags that should be applied: `/pattern/gi` for scanning full documents; `/pattern/i` for single-sentence classification. `\b` is a word boundary.

---

## §1 — Requirement Language Patterns

**Used by:** Step 3 (Requirements Extractor)
**Purpose:** Classify each extracted sentence as mandatory, optional, or conditional based on the requirement language it uses.
**Confidence threshold:** Mandatory signal beats optional when both appear in the same sentence. Conditional beats optional when both appear.

---

### §1.1 Mandatory Indicators

Non-compliance risks disqualification or penalty.

| # | Pattern | Confidence | Notes |
|---|---|---|---|
| M1 | `\b(shall)\b(?!\s+(not\|neither))` | 0.95 | Core mandatory keyword in formal procurement English |
| M2 | `\b(must)\b(?!\s+(not\|neither))` | 0.92 | Slightly less formal than "shall" but equally binding |
| M3 | `\b(required\s+to\|is\s+required\|are\s+required)\b` | 0.90 | Passive-voice mandatory |
| M4 | `\b(mandatory\|obligatory)\b` | 0.95 | Explicit mandatory declaration |
| M5 | `\b(will\s+be\s+disqualified\|failure\s+to\s+comply)\b` | 0.98 | Enforcement language — highest confidence |
| M6 | `\b(shall\s+not\|must\s+not\|is\s+prohibited)\b` | 0.93 | Negative mandatory (prohibition) |

**Real examples from Aramco RFPs:**
- "Vendor **shall** provide 24×7 technical support with 4-hour response time" → M1
- "All equipment **must** be new and unused" → M2
- "Failure to comply with SACS-002 **will result in** disqualification" → M5
- "It is **mandatory** that the proposed solution supports IPv6" → M4
- "Vendor **shall not** subcontract any portion without written approval" → M6

**False positive risks:**
- "The client shall have the right to…" — obligation on client, not vendor. Check subject of sentence.
- "shall be deemed" in definitions sections — definitional, not a vendor obligation.
- "must not" in specifications of what the product itself must not do vs. what the vendor must not do.

---

### §1.2 Optional Indicators

No penalty for missing. Scored positively if present.

| # | Pattern | Confidence | Notes |
|---|---|---|---|
| O1 | `\b(should\|may\|can\|could)\b` | 0.75 | Broad optional — "may" in particular can be permissive rather than recommendatory |
| O2 | `\b(recommended\|preferred\|desirable\|optional)\b` | 0.88 | Explicit optional declaration |
| O3 | `\b(it\s+is\s+(suggested\|advisable\|preferable))\b` | 0.85 | Formal optional hedging |
| O4 | `\b(where\s+possible\|if\s+feasible\|when\s+practicable)\b` | 0.82 | Effort-qualified optional |

**Real examples:**
- "The solution **should** support future expansion to 10,000 users" → O1
- "It is **preferred** that the vendor has prior experience in the oil and gas sector" → O2
- "The vendor **may** propose alternative solutions that meet the same objectives" → O1
- "**Where possible**, the solution should leverage existing infrastructure" → O4

**False positive risks:**
- "may be rejected" — this is a legal trap (§5), not an optional requirement.
- "may request" — client option, not vendor obligation.
- "should the vendor fail" — conditional, not optional.

---

### §1.3 Conditional Indicators

Depends on context, client discretion, or site conditions. May become mandatory post-award.

| # | Pattern | Confidence | Notes |
|---|---|---|---|
| C1 | `\b(if\s+applicable\|where\s+required\|as\s+needed)\b` | 0.85 | Conditioned on applicability |
| C2 | `\b(at\s+(?:Saudi\s+Aramco(?:'s)?\|the\s+(?:client\|company)(?:'s)?)\s+(?:sole\s+)?discretion)\b` | 0.92 | Client-discretion conditional — Aramco-specific phrasing |
| C3 | `\b(unless\s+otherwise\s+(?:specified\|agreed\|directed))\b` | 0.88 | Default-with-override pattern |
| C4 | `\b(subject\s+to\|contingent\s+upon\|provided\s+that)\b` | 0.80 | Dependency conditional |

**Real examples:**
- "**If applicable**, the vendor shall comply with IKTVA requirements" → C1
- "Additional support resources may be requested **at Saudi Aramco's sole discretion**" → C2
- "**Unless otherwise specified**, all documentation shall be in English" → C3
- "**Subject to** site access approval, vendor shall complete installation within 90 days" → C4

**False positive risks:**
- "subject to" in payment clauses — financial context, not a technical requirement.
- "provided that" often introduces a sub-condition of an already-classified sentence.

---

### §1.4 Compound Sentence Splitter

Some sentences mix mandatory and optional requirements. The extractor splits at conjunctions before classifying each clause independently.

```regex
,?\s+\b(and|but|while|whereas|although|though|however)\b\s+
```

**Usage:** Split the sentence at the matched conjunction. Classify each resulting fragment independently using §1.1–§1.3.

**Example:** "The vendor shall provide installation services **and may** optionally provide training"
→ Fragment 1: "The vendor shall provide installation services" → mandatory (M1)
→ Fragment 2: "may optionally provide training" → optional (O1)

**Known limitation:** This splitter is naive. Conjunctions within noun phrases ("routing and switching") should not trigger a split. Apply only when the conjunction connects two finite verb clauses (i.e., both fragments have a subject and verb). Unresolved edge cases go to the engineer at Checkpoint 1.

---

## §2 — Evaluation Criteria Patterns

**Used by:** Step 6 (Evaluation Criteria Analyzer)
**Purpose:** Detect and extract scoring methodology, envelope structure, pass thresholds, and IKTVA scoring requirements.

---

### §2.1 General Scoring Detection

| # | Pattern | Notes |
|---|---|---|
| E1 | `\b(evaluation\s+criteria\|scoring\s+methodology\|assessment\s+criteria)\b` | Section heading detector |
| E2 | `\b(technical\s+score\|commercial\s+score\|weighted\s+score)\b` | Multi-envelope scoring |
| E3 | `\b(minimum\s+(?:acceptable\|passing)\s+score\|threshold)\b` | Pass/fail threshold present |
| E4 | `\b(envelope\s+(?:1\|2\|3\|A\|B\|C))\b` | Sequential envelope methodology |

**Aramco sequential envelope structure:**
- Envelope 1 (Administrative): pass/fail on documentation completeness
- Envelope 2 (Technical): scored against Technical Evaluation Questionnaire
- Envelope 3 (Commercial): only opened if Envelope 2 passes threshold

**Known pattern:** Standalone `Technical Evaluation Questionnaire.xlsx` in the RFP package. Sheet typically has 3-level compliance: `Supported / Will be Customized / Not Supported`. Typical weights: Technical 60%, Commercial 30%, Experience 10%. Typical pass threshold: 70% technical score.

---

### §2.2 IKTVA (Saudi Local Content) Scoring

IKTVA = In-Kingdom Total Value Add. Assessed separately from technical score. Referenced in KSA government and Aramco RFPs.

| # | Pattern | Notes |
|---|---|---|
| I1 | `\b(IKTVA\|In-Kingdom\s+Total\s+Value\s+Add\|local\s+content\s+(?:score\|percentage\|requirement))\b` | IKTVA section detector |
| I2 | `\b(Saudization\s+(?:ratio\|percentage\|requirement)\|Saudi\s+national(?:s)?\s+(?:employed\|ratio))\b` | Workforce localization |
| I3 | `\b(in-kingdom\s+(?:procurement\|manufacturing\|sourcing)\|locally\s+(?:manufactured\|sourced\|procured))\b` | Procurement localization |
| I4 | `\b(training\s+and\s+development\s+(?:investment\|spend\|program)\|knowledge\s+transfer\s+(?:plan\|requirement))\b` | Training investment scoring |

**Output when IKTVA detected:** Set `iktva.required = true`, extract `minimumScore` (e.g., "minimum IKTVA score of 30%") using pattern `minimum\s+IKTVA\s+(?:score\s+)?of\s+(\d+)%`.

---

## §3 — Filename Classification Patterns

**Used by:** Step 1, Stage 1 (File Classifier — instant, no file-open needed)
**Purpose:** Classify document type from filename alone before opening.
**Confidence threshold:** >0.8 to stop at Stage 1 without proceeding to Stage 2.
**Coverage:** Catches ~60% of RFP package files without opening them.

---

### §3.1 Pattern Table

| Category | Type/Subtype | Filename patterns | Confidence |
|---|---|---|---|
| compliance | cybersecurity_standard | `SACS-`, `SAES-`, `CAP-`, `GI-` | 0.97 |
| commercial | boq_template | `BOQ`, `BoQ`, `pricing`, `bill of quantities`, `bill_of_quantities` | 0.93 |
| legal | nda | `NDA`, `confidential`, `non-disclosure`, `non_disclosure` | 0.92 |
| legal | bid_bond | `bid bond`, `bid_bond`, `bank guarantee`, `bank_guarantee`, `performance bond`, `performance_bond` | 0.95 |
| admin | certificate | `CR`, `commercial registration`, `ZATCA`, `VAT`, `commercial_registration` | 0.88 |
| commercial | evaluation_criteria | `evaluation`, `questionnaire`, `scoring`, `TEQ`, `technical evaluation` | 0.90 |
| legal | terms | `T&C`, `terms and conditions`, `terms_and_conditions`, `TC`, `GTC` | 0.93 |
| technical | requirements | `scope`, `SOW`, `requirements`, `specification`, `tech spec`, `technical_spec` | 0.85 |
| technical | engineering_drawing | `drawing`, `.dwg`, `.vsdx`, `riser`, `layout`, `floor plan`, `network diagram` | 0.91 |
| compliance | local_content | `local content`, `local_content`, `IKTVA`, `Saudization` | 0.94 |
| correspondence | email | `\.msg$`, `\.eml$`, `clarification`, `Q&A`, `addendum`, `amendment` | 0.85 |

---

### §3.2 Regex Implementation

```typescript
const FILENAME_PATTERNS: [RegExp, string, string, number][] = [
  // [pattern, category, subtype, confidence]
  [/SACS-|SAES-|CAP-\d|GI-\d/i,                            'compliance',  'cybersecurity_standard',  0.97],
  [/\bBOQ\b|BoQ|pricing|bill.of.quantities/i,               'commercial',  'boq_template',            0.93],
  [/\bNDA\b|confidential|non.disclosure/i,                  'legal',       'nda',                     0.92],
  [/bid.bond|bank.guarantee|performance.bond/i,             'legal',       'bid_bond',                0.95],
  [/\bCR\b|commercial.registr|ZATCA|\bVAT\b/i,              'admin',       'certificate',             0.88],
  [/evaluation|questionnaire|scoring|\bTEQ\b/i,             'commercial',  'evaluation_criteria',     0.90],
  [/T&C|terms.and.conditions|\bGTC\b/i,                     'legal',       'terms',                   0.93],
  [/(?<![a-zA-Z])scope(?![a-zA-Z])|\bSOW\b|requirements|specification/i,         'technical',   'requirements',            0.85],
  [/drawing|\.dwg|\.vsdx|riser|layout|floor.plan/i,         'technical',   'engineering_drawing',     0.91],
  [/local.content|IKTVA|Saudization/i,                      'compliance',  'local_content',           0.94],
  [/\.msg$|\.eml$|clarification|Q&A|addendum|amendment/i,   'correspondence', 'email',                0.85],
];
```

**Note on `CR`:** The pattern `\bCR\b` is short and can appear in non-document contexts (e.g., "CR-001" as a change request). Apply only to the base filename stem, not path components.

---

## §4 — Reference Detection Patterns

**Used by:** Step 2 (Missing Document Detector)
**Purpose:** Identify references to external documents within RFP text. Cross-reference against package contents to flag missing documents.

---

### §4.1 Internal Cross-References

References to annexes, appendices, and sections within the RFP package itself.

```regex
(?:refer\s+to|as\s+per|see|in\s+accordance\s+with)\s+(Annex|Appendix|Attachment|Exhibit|Schedule)\s+[A-Z0-9]+
(?:paragraph|section|clause)\s+\d+[\.\d]*
```

**Real example:** "refer to Annex A for the detailed scope of work" — Diriyah VSS project. Annex A was not included in the package; this was a critical gap discovered manually.

**Severity:** Critical if the referenced annex/appendix contains technical scope. High if it contains commercial terms. Low if informational.

---

### §4.2 Aramco Engineering Standards

Detected by standard code patterns. Their absence from the package is always Critical severity — cannot assess compliance without the standard document.

```regex
SACS-\d{3}        # Saudi Aramco Cybersecurity Standards (e.g., SACS-002, SACS-012)
SAES-[A-Z]-\d{3}  # Saudi Aramco Engineering Standards (e.g., SAES-Q-001)
SAEP-\d+          # Saudi Aramco Engineering Procedures
GI-\d+\.\d+       # General Instructions (e.g., GI-0002.710)
CAP-\d+           # Cybersecurity Architecture Patterns
SAMSS-\d+         # Saudi Aramco Materials System Specifications
```

**Known corpus:** Aramco DMM7++ fixture references SACS-002, SACS-012, and SAES-Q-001. These three are confirmed to appear in real RFPs from the STC project archive.

---

### §4.3 External / International Standards

Absent from package = Medium severity (can be sourced publicly).

```regex
ISO\s+\d{4,5}(?:[-:]\d{4})?    # ISO standards (e.g., ISO 27001:2022, ISO 9001:2015)
NIST\s+(?:SP\s+)?800-\d+        # NIST Special Publications (e.g., NIST SP 800-53)
NCA\s+ECC                        # NCA Essential Cybersecurity Controls (KSA)
NFPA\s+\d+                       # Fire protection standards (e.g., NFPA 72)
API\s+\d+                        # American Petroleum Institute standards (e.g., API 650)
```

**Bonus patterns encountered in MENA corpus (not in original spec):**
```regex
SAMA\s+CSF           # Saudi Arabian Monetary Authority Cybersecurity Framework
IEC\s+\d{5}          # IEC electrical standards
TIA-\d+              # Telecom Infrastructure Association standards
```

---

### §4.4 Generic Reference Language

Low severity — may be informational or already included under a different filename.

```regex
(?:the\s+attached|enclosed\s+herewith|accompanying\s+document)
(?:as\s+defined\s+in|pursuant\s+to|subject\s+to\s+the\s+provisions\s+of)
```

**False positive risk:** "as defined in this document" — self-referential, not an external reference. Check that the reference points outward (to a different document) before flagging.

---

## §5 — Legal Trap Patterns

**Used by:** Step 4 (Legal Trap Flagger)
**Purpose:** Detect clauses that risk disqualification, penalty, or unfavorable post-award terms.
**Total:** 27 patterns — 9 critical, 9 high, 9 medium.

> Patterns marked **(spec)** appear verbatim in the E1 spec. Patterns marked **(inferred)** are derived from the MENA procurement corpus and consistent with the spec's category descriptions.

---

### §5.1 Category 1 — CRITICAL: Automatic Disqualification Triggers (9 patterns)

These are pass/fail. Non-compliance causes immediate rejection regardless of technical score.
**Action:** Display at top of Checkpoint 1 UI. Engineer must confirm action taken.

| # | Pattern | Source | Real-world trigger |
|---|---|---|---|
| D1 | `\b(bid\s+bond\|bank\s+guarantee\|performance\s+bond)\b.*\b(required\|mandatory\|shall\s+submit)\b` | spec | "Bid bond of 2% of bid value required with submission" |
| D2 | `\b(closing\s+date\|submission\s+deadline\|latest\s+date\s+for\s+submission)\b` | spec | "Closing date: 15-March-2026 at 14:00 AST. Bids received after this time will not be considered." |
| D3 | `\b(sealed\s+envelope\|original\s+and\s+\d+\s+copies\|hardcopy\s+submission)\b` | spec | "One original and three copies in sealed envelopes" |
| D4 | `\b(naming\s+convention\|file\s+format\|shall\s+be\s+submitted\s+in)\b` | spec | "Files shall be submitted in PDF format with naming convention: [Co.]_[OP-No.]_Technical.pdf" |
| D5 | `\b(prequalified\s+vendors\s+only\|restricted\s+to\|eligible\s+bidders)\b` | spec | "This RFP is restricted to prequalified vendors on Aramco's approved list" |
| D6 | `\b(conflict\s+of\s+interest\s+declaration\|anti-bribery\|non-collusion)\b` | spec | "Vendors must submit a signed anti-bribery and non-collusion declaration" |
| D7 | `\b(valid\s+(?:commercial\s+)?registr\|CR\s+number\|chamber\s+of\s+commerce\s+certif)\b.*\b(required\|mandatory\|shall\s+(?:be\s+)?submit)\b` | inferred | "Valid Commercial Registration (CR) required — must be in vendor's legal name" |
| D8 | `\b(power\s+of\s+attorney\|authorized\s+signatory\|notarized)\b.*\b(required\|mandatory\|shall)\b` | inferred | "Bid must be signed by an authorized signatory supported by a notarized power of attorney" |
| D9 | `\b(bid\s+(?:validity\|shall\s+remain\s+valid)\|validity\s+period\s+of\s+(?:the\s+)?(?:bid\|offer\|proposal))\b.*\b(\d+\s+(?:day\|week\|month)s?)\b` | inferred | "Bid shall remain valid for 180 days from closing date. Bids with shorter validity will be rejected." |

---

### §5.2 Category 2 — HIGH: Discretionary Rejection Triggers (9 patterns)

Client has grounds to reject but is not obligated to. Engineer must verify compliance.
**Action:** Flag as HIGH in Checkpoint 1. Engineer should confirm before submission.

| # | Pattern | Source | Real-world trigger |
|---|---|---|---|
| R1 | `\b(incomplete\s+submission\|missing\s+document\|partial\s+response)\b.*\b(may\s+be\s+rejected\|reserves\s+the\s+right)\b` | spec | "Incomplete submissions may be rejected at the client's sole discretion" |
| R2 | `\b(minimum\s+score\|threshold\|passing\s+mark)\b.*\b(\d+%\|\d+\s+points)\b` | spec | "Vendors scoring below 70% on the technical evaluation will not proceed to commercial review" |
| R3 | `\b(minimum\s+\d+\s+years?\s+experience\|demonstrated\s+track\s+record\|similar\s+projects)\b` | spec | "Minimum 5 years experience in similar network infrastructure projects required" |
| R4 | `\b(annual\s+turnover\|financial\s+capability\|audited\s+financial\s+statements)\b` | spec | "Audited financial statements for the last 3 years shall be submitted with the bid" |
| R5 | `\b(?:ISO\s+\d{4,5}\|certif(?:ied\|ication)\s+(?:required\|mandatory))\b.*\b(?:hold\|possess\|maintain\|current\|valid)\b` | inferred | "Vendor must hold valid ISO 9001:2015 certification from an accredited body" |
| R6 | `\b(local\s+(?:partner\|agent\|representative\|presence)\|in-kingdom\s+(?:office\|presence)\|Saudi\s+agent)\b.*\b(required\|mandatory\|shall)\b` | inferred | "Vendor must have an in-kingdom presence or an authorized Saudi agent" |
| R7 | `\b(reference\s+(?:project\|letter\|site\|list)\|similar\s+(?:project\|scope\|work)\b.*\b(shall\s+(?:be\s+)?provid\|required\|mandatory))\b` | inferred | "Three reference projects of similar scope and value shall be provided" |
| R8 | `\b(bid\s+(?:price\|amount)\s+(?:shall\|must)\s+(?:remain\s+)?(?:fixed\|firm)\|no\s+price\s+escalation\|firm\s+(?:and\s+)?fixed\s+price)\b` | inferred | "Prices shall be firm and fixed for the duration of the contract with no escalation" |
| R9 | `\b(technical\s+pass(?:ing)?\s+(?:mark\|threshold\|score)\|minimum\s+technical\s+(?:score\|marks?))\b.*\b(\d+%\|\d+\s+(?:marks?\|points?))\b` | inferred | "Minimum technical passing mark: 65 points out of 100. Bids below this threshold are disqualified." |

---

### §5.3 Category 3 — MEDIUM: Contract Risk / Post-Award Triggers (9 patterns)

These apply post-award but inform how the proposal is priced and scoped. Liquidated damages and warranty periods directly affect E2 margin calculations.
**Action:** Flag as MEDIUM. Include in risk section of financial proposal.

| # | Pattern | Source | Real-world trigger |
|---|---|---|---|
| M1 | `\b(liquidated\s+damages\|penalty\s+clause\|delay\s+penalty)\b.*\b(\d+%\|SAR\|USD)\b` | spec | "Liquidated damages: 0.5% per week of delay, capped at 10% of contract value" |
| M2 | `\b(terminate\s+for\s+convenience\|without\s+cause\|at\s+any\s+time)\b` | spec | "Client may terminate the contract for convenience with 30 days written notice" |
| M3 | `\b(unlimited\s+liability\|no\s+cap\s+on\s+liability\|full\s+liability)\b` | spec | "Vendor accepts unlimited liability for losses arising from negligence" |
| M4 | `\b(all\s+intellectual\s+property\|work\s+product\s+shall\s+belong\|assigns\s+all\s+rights)\b` | spec | "All intellectual property developed under this contract shall belong to the client" |
| M5 | `\b(professional\s+indemnity\s+insurance\|public\s+liability\s+insurance)\b.*\b(\d+.*(?:million\|SAR\|USD))\b` | spec | "Professional indemnity insurance: minimum SAR 5,000,000 per occurrence" |
| M6 | `\b(force\s+majeure\|act\s+of\s+(?:God\|nature)\|beyond\s+(?:(?:the\s+)?(?:reasonable\s+)?control))\b` | inferred | "Neither party shall be liable for delays caused by force majeure events" |
| M7 | `\b(governing\s+law\|jurisdiction\|arbitration\|dispute\s+resolution)\b.*\b(Kingdom\s+of\s+Saudi\s+Arabia\|KSA\|Saudi\|UAE\|DIFC)\b` | inferred | "This contract shall be governed by the laws of the Kingdom of Saudi Arabia" |
| M8 | `\b(variation\s+order\|change\s+order\|scope\s+(?:change\|variation))\b.*\b(prior\s+(?:written\s+)?(?:approval\|consent)\|shall\s+not\s+(?:be\s+)?(?:carried\s+out\|commenced))\b` | inferred | "No variation shall be carried out without prior written approval from the client" |
| M9 | `\b(warranty\|defect(?:s)?\s+liability\s+period\|guarantee\s+period)\b.*\b(\d+\s+(?:year\|month)s?)\b` | inferred | "Defects liability period: 24 months from date of practical completion" |

---

## §6 — Folder Classification Patterns

**Used by:** Step 1, Stage 2 (Folder location fallback when filename is ambiguous)
**Confidence threshold:** >0.7 to stop at Stage 2 without opening the file.
**Applies when:** Stage 1 filename match returned confidence <0.8.

| Folder name pattern | Category | Confidence |
|---|---|---|
| `RFQ Document`, `RFP`, `Documents`, `Tender Documents` | technical (default) | 0.72 |
| `BOQ`, `Pricing`, `Commercial`, `Financial` | commercial | 0.78 |
| `Legal`, `NDA`, `Contracts`, `Agreements` | legal | 0.80 |
| `Compliance`, `Security`, `Standards`, `Cybersecurity` | compliance | 0.80 |
| `Submittals`, `Certificates`, `Admin`, `Administrative` | admin | 0.75 |

**Regex implementation:**

```typescript
const FOLDER_PATTERNS: [RegExp, string, number][] = [
  [/BOQ|pricing|commercial|financial/i,            'commercial',       0.78],
  [/legal|NDA|contract|agreement/i,                'legal',            0.80],
  [/compliance|security|standards|cybersecurity/i, 'compliance',       0.80],
  [/submittal|certificate|admin/i,                 'admin',            0.75],
  [/RFQ|RFP|document|tender/i,                     'technical',        0.72],  // catch-all last
];
```

**Note:** Folder patterns are evaluated in order above. First match wins. "Technical (default)" is intentionally last — it is the catch-all for ambiguous folders.

---

## §7 — Content Keyword Patterns

**Used by:** Step 1, Stage 3 (Content scan — file must be opened)
**Confidence threshold:** >0.5 sufficient to classify. Files below 0.5 after Stage 3 are flagged for human review.
**Input:** First 2–3 pages of extracted text from the file.

| # | Keywords / Pattern | Classification | Notes |
|---|---|---|---|
| K1 | `shall comply\|mandatory\|disqualif\|failure to\|required` | technical / requirements | High overlap with §1.1 mandatory patterns; `disqualif` catches both disqualified and disqualification; `required` catches "is required", "required to", etc. |
| K2 | `unit price\|total price\|\bqty\b\|amount.*(?:SAR\|USD)\|\bSAR\b.*total` | commercial / pricing | Financial table language |
| K3 | `whereas\|hereby agrees\|indemnify\|liability\|jurisdiction\|governing law` | legal | Formal contract preamble language |
| K4 | `cybersecurity\|access control\|encryption\|vulnerability\|\bNCA\b\|ISO 27001` | compliance | Security-specific terms |
| K5 | `authorized signatory\|chamber of commerce\|registration number\|ZATCA` | admin / certificate | Official certification language |

**Regex implementation:**

```typescript
const CONTENT_PATTERNS: [RegExp, string, string][] = [
  [/shall comply|mandatory|disqualif|failure to|required/i,                 'technical',   'requirements'],
  [/unit price|total price|\bqty\b|amount.{0,20}(?:SAR|USD)|\bSAR\b.{0,20}total/i, 'commercial', 'pricing'],
  [/whereas|hereby agrees|indemnify|\bliability\b|jurisdiction|governing law/i,      'legal',       'general'],
  [/cybersecurity|access control|encryption|vulnerability|\bNCA\b|ISO 27001/i,       'compliance',  'cybersecurity'],
  [/authorized signatory|chamber of commerce|registration number|ZATCA/i,            'admin',       'certificate'],
];
```

**Scoring:** Each matched pattern adds 0.2 to the confidence score for that category. Multiple matches accumulate (max 1.0). If two categories both score >0.5, the higher score wins; tie goes to the engineer for review.

---

## §8 — Deadline Extraction Patterns

**Used by:** Step 4 (Compliance Deadline Extractor, part of Legal Trap Flagger)
**Purpose:** Extract specific dates and timeframes from legal/commercial documents. Feeds `ComplianceDeadline[]` output.

---

### §8.1 Date Formats

All formats observed in the Aramco/MENA RFP corpus:

```regex
# DD-Month-YYYY (confirmed in Aramco RFP example: "15-March-2026")
\b(\d{1,2})[-\s](January|February|March|April|May|June|July|August|September|October|November|December)[-\s](\d{4})\b

# DD-Mon-YYYY abbreviated
\b(\d{1,2})[-\s](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[-\s](\d{4})\b

# DD/MM/YYYY (common in Saudi government RFPs)
\b(\d{1,2})/(\d{1,2})/(\d{4})\b

# YYYY-MM-DD (ISO format, less common but appears in digital RFPs)
\b(\d{4})-(\d{2})-(\d{2})\b

# "Nth of Month YYYY" (formal English)
\bthe\s+(\d{1,2})(?:st|nd|rd|th)\s+of\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b
```

---

### §8.2 Time Formats

```regex
# HH:MM AST (confirmed format from Aramco example: "14:00 AST")
\b(\d{1,2}):(\d{2})\s*(AST|GST|UTC[+-]\d+)?\b

# HH:MM hrs
\b(\d{1,2}):(\d{2})\s*(?:hrs?|hours?)\b

# 12-hour clock
\b(\d{1,2}):(\d{2})\s*(AM|PM)\b
```

**Note:** AST = Arabia Standard Time (UTC+3). All extracted deadlines should be stored with UTC offset for `daysRemaining` calculation.

---

### §8.3 Relative Period Patterns

Used for post-award obligations (warranty periods, bond validity, etc.):

```regex
# "within N days/weeks/months of [event]"
\bwithin\s+(\d+)\s+(business\s+)?days?\s+of\s+(award|signing|PO\s+issuance|contract\s+execution|handover)\b

# "N days from [event]"
\b(\d+)\s+(calendar\s+|business\s+)?days?\s+from\s+(the\s+)?(date\s+of\s+)?(award|signing|issuance|commencement)\b

# "N months/years"
\b(\d+)\s+(calendar\s+)?months?\b
\b(\d+)\s+years?\b
```

---

### §8.4 Deadline Context Anchors

The date/time patterns above will match any date in the document. Use these anchors to distinguish deadline dates from reference/historical dates:

```regex
# Submission anchors
\b(closing\s+date|submission\s+deadline|latest\s+(?:date\s+)?(?:for\s+)?submission|bid\s+due\s+date)\b

# Bond validity anchors
\b(bid\s+bond\s+validity|guarantee\s+validity|bond\s+shall\s+remain\s+valid)\b

# Clarification anchors
\b(questions?\s+(?:and\s+clarifications?\s+)?deadline|last\s+date\s+for\s+(?:queries|clarifications))\b

# Meeting anchors
\b(pre-bid\s+(?:meeting|conference)|site\s+visit\s+date|mandatory\s+(?:attendance|site\s+visit))\b
```

**Usage:** Scan for context anchors first. Within ±3 lines of a matched anchor, extract the date/time using §8.1–§8.2 patterns. This avoids false positives from dates in boilerplate, signatures, or version histories.

---

## §9 — Maintenance Notes

---

### §9.1 How to Add a New Pattern

1. **Identify the section** (§1–§8) the pattern belongs to based on its function.
2. **Write the regex** against at least 3 real positive examples and 2 negative examples from the corpus.
3. **Assign a confidence score:** Start at 0.80. Lower if the pattern has high false positive risk; raise above 0.90 only if the pattern is syntactically unambiguous (e.g., `SACS-\d{3}`).
4. **Add a real example** from an actual Aramco/MENA RFP — do not use invented examples.
5. **Document false positive risks** in the Notes column.
6. **Increment the version** in the header (patch for new patterns, minor for restructuring).
7. **Update the test file mapping** in §9.2.

---

### §9.2 Test File Mapping

| Fixture | Covers | Expected results |
|---|---|---|
| `backend/storage/OP-2025-154381/test_rfp.txt` | §1, §3, §4 | ≥3 mandatory requirements, ≥1 missing document reference |
| Aramco DMM7++ fixture (when added) | §4.2 | SACS-002, SACS-012, SAES-Q-001 detected as critical missing |
| Aramco Storage fixture | §3, §5 | All 16 files classified; bid bond + SACS-002 flagged as CRITICAL |
| Diriyah ESS_BoQ | §3.1 (boq_template) | Classified as commercial/boq_template; vendor tab parsed |
| `Comments.docx` (Aramco Storage) | §1 | Requirement count within 10% of manual count |

---

### §9.3 Known Limitations

**Arabic content:**
Arabic requirement language (`يجب` = must, `ينبغي` = should, `لا يجوز` = shall not) is not covered by §1 patterns. v1.0 focuses on English extraction only. Arabic sentences are passed through without classification and flagged at Checkpoint 1 for manual review. Do not extend §1 for Arabic without a proper corpus of ≥50 labeled examples.

**Image-only PDFs:**
PDFs that are scanned images without embedded text return empty strings from the text extractor. The Stage 3 content scan (§7) will score 0.0 on all categories — the file will be flagged for human review. This is correct behavior. Do not attempt OCR in v1.0.

**Compound mandatory/negative:**
"The vendor shall not be required to provide training" — the negative lookahead `(?!\s+(not|neither))` in M1/M2 handles the immediate negation, but "shall not be required" (negation on "required", not "shall") can still misfire. The sentence should be reclassified as an exclusion, not a mandatory requirement. Flag any sentence matching both M1/M2 and M6 (`shall not`) for manual review at Checkpoint 1.

**"May" ambiguity:**
Pattern O1 (`\bmay\b`) matches both "vendor may provide" (optional) and "bids may be rejected" (legal trap, §5 Category 2). The legal trap check (§5) runs before optional classification. If a sentence matches both O1 and any §5 pattern, §5 wins.

**Short filenames and abbreviations:**
`CR` (§3.1 admin/certificate) can collide with "CR-001" as a change request number in engineering documents. Apply the filename pattern only to the base filename stem (strip path and extension first).

**Bid validity vs. contract validity:**
Pattern D9 in §5.1 targets bid validity (pre-award). Pattern M9 in §5.3 targets defects liability (post-award). Sentences containing both "bid" and "validity" go to D9; sentences containing "contract", "defect", "warranty", or "guarantee" go to M9. When unclear, flag for engineer.

---

### §9.4 Pattern Count Reference

| Section | Patterns |
|---|---|
| §1 Requirement language | 6 mandatory + 4 optional + 4 conditional + 1 splitter = **15** |
| §2 Evaluation criteria | 4 scoring + 4 IKTVA = **8** |
| §3 Filename classification | 10 filename patterns | 
| §4 Reference detection | 2 internal + 6 Aramco standards + 5 external + 2 generic = **15** |
| §5 Legal traps | 9 critical + 9 high + 9 medium = **27** |
| §6 Folder classification | **5** |
| §7 Content keywords | **5** |
| §8 Deadline extraction | 5 date + 3 time + 4 period + 4 anchor = **16** |
| **Total** | **101** |
