# E1 — RFP Package Parser + Compliance Matrix

## Complete Process Flow Documentation

**Engine:** E1
**Gate:** Gate 2
**Runtime pattern:** Deterministic Guardrails (code gate → AI → code gate)
**AI involvement:** Low — 2 narrow AI calls out of 12 steps. Code does 80%.
**AI model (when called):** Sonnet 4.6

---

## Implementation Classification Per Step

| Step | Name | Class | Implementation | AI call? | Failure handling |
|---|---|---|---|---|---|
| 1 | File classifier + router | (a) + (b) | Regex stages 1-2 are deterministic. Stage 3 content scan is AI-assisted. | Only if stages 1-2 fail (<0.7 confidence) | Below 0.5 → flag for engineer |
| 2 | Missing document detector | (a) | Regex extraction of references → set comparison. Pure code. | No | Always produces result |
| 3 | Requirements extractor | (a) + (b) | Regex catches 80% of mandatory/optional. AI interprets ambiguous 20%. | Yes — narrow call | Retry once → flag unclear items |
| 4 | Legal trap flagger | (a) | Regex pattern matching for 27 trigger patterns. Pure code. | No | Always produces result |
| 5 | Human checkpoint #1 | — | UI page. Engineer reviews. | No | Engineer decides |
| 6 | Eval criteria analyzer | (b) | AI extracts scoring structure from varied formats. Code validates. | Yes — narrow call | Flag if no criteria found |
| 7 | Vendor list extractor | (a) | Excel column parsing. Pure code. | No | Returns empty list if none found |
| 8 | Sector detector | (a) | Client name lookup → keyword scan → standard reference. Pure code. | No | Defaults to "general" |
| 9 | Compliance framework selector | (a) | Lookup table: sector + country → framework(s). Pure code. | No | Always produces result |
| 10 | Compliance matrix generator | (a) + (b) + (c) | Keyword matching is code. Status assignment is AI judgment. | Yes — for status assignment | Retry once → flag low-confidence rows |
| 11 | Cross-reference linker | (a) | Rule-based mapping: topic keywords → TP section. Pure code. | No | Defaults to §6 (Proposed Solution) |
| 12 | Human checkpoint #2 | — | UI page. Engineer reviews final matrix. | No | Engineer decides |

**Summary:** 8 deterministic steps, 2 AI-with-validation steps, 1 mixed step, 2 human checkpoints. AI calls total: 2-3 narrow Sonnet calls per pipeline run.

**Escalation rule (all AI steps):** Retry once with error message → if still fails, flag for engineer with warning → engineer always receives output, never nothing.

---

## Process Flow Overview

```
RFP Package (16+ files)
    │
    ▼
┌─────────────────────────┐
│  Step 1: File Classifier │ ← filename + folder + content keywords
│         + Router         │
└─────────┬───────────────┘
          │
    ┌─────┼─────────────────┐
    ▼     ▼                 ▼
┌──────┐ ┌──────────┐ ┌──────────┐
│Step 2│ │  Step 3   │ │  Step 4  │
│Missing│ │  Req.    │ │  Legal   │
│Doc    │ │Extractor │ │  Trap    │
│Detect.│ │          │ │  Flagger │
└──┬───┘ └────┬─────┘ └────┬─────┘
   │          │             │
   └──────────┼─────────────┘
              ▼
┌─────────────────────────┐
│ Step 5: Human Checkpoint │ ← confirm requirements, review gaps
│         #1               │
└─────────┬───────────────┘
          │
    ┌─────┼─────────────────┐
    ▼     ▼                 ▼
┌──────┐ ┌──────────┐ ┌──────────┐
│Step 6│ │  Step 7   │ │  Step 8  │
│Eval  │ │  Vendor   │ │  Sector  │
│Criter│ │  List     │ │  Detect. │
│Analyz│ │  Extract. │ │          │
└──┬───┘ └────┬─────┘ └────┬─────┘
   │          │             │
   └──────────┼─────────────┘
              ▼
┌─────────────────────────┐
│ Step 9: Compliance       │ ← NCA ECC / SAMA CSF / ISO 27001
│         Framework Select.│
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Step 10: Compliance      │ ← requirement → control mapping
│          Matrix Generator│
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Step 11: Cross-Reference │ ← requirement → TP section mapping
│          Linker          │
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Step 12: Human Checkpoint│ ← validate matrix, resolve gaps
│          #2              │
└─────────┬───────────────┘
          │
    ┌─────┼─────────────────┐
    ▼     ▼                 ▼
┌──────┐ ┌──────────┐ ┌──────────┐
│Output│ │  Output   │ │  Output  │
│Compli│ │  Req.     │ │  Risk    │
│Matrix│ │  Baseline │ │  Flags   │
│.xlsx │ │  .json    │ │  report  │
└──────┘ └──────────┘ └──────────┘
          │
          ▼
    Feeds E2, E4, E5
```

---

## Step 1: File Classifier + Router

**Purpose:** Decide what kind of document each file is before any content analysis begins.

**Input:** RFP package (16+ files in various formats: PDF, DOCX, XLSX, DWG, MSG)
**Output:** Classified file list with type, subtype, confidence score, and assigned downstream parser

### How it works

Three-stage classification, each stage more expensive than the last. The classifier stops as soon as it has high confidence.

#### Stage 1 — Filename pattern matching (instant, no AI needed)

Rules from `RFP_Compliance_Patterns.md §3`:

| Pattern in filename | Classification |
|---|---|
| `SACS-*`, `SAES-*`, `CAP-*`, `GI-*` | compliance / cybersecurity standard |
| `BOQ`, `BoQ`, `pricing`, `bill of quantities` | commercial / boq_template |
| `NDA`, `confidential`, `non-disclosure` | legal / nda |
| `bid bond`, `bank guarantee`, `performance bond` | legal / bid_bond |
| `CR`, `commercial registration`, `ZATCA`, `VAT` | admin / certificate |
| `evaluation`, `questionnaire`, `scoring` | commercial / evaluation_criteria |
| `T&C`, `terms and conditions` | legal / terms |
| `scope`, `SOW`, `requirements`, `specification` | technical / requirements |
| `drawing`, `.dwg`, `.vsdx`, `riser`, `layout` | technical / engineering_drawing |
| `local content`, `IKTVA`, `Saudization` | compliance / local_content |

This catches ~60% of files without opening them.

#### Stage 2 — Folder location (if filename is ambiguous)

| Folder name | Classification |
|---|---|
| `RFQ Document`, `RFP`, `Documents` | technical (default) |
| `BOQ`, `Pricing` | commercial |
| `Legal`, `NDA` | legal |
| `Compliance`, `Security`, `Standards` | compliance |
| `Submittals`, `Certificates` | admin |

#### Stage 3 — Content keyword scan (for files that don't match patterns)

Opens the file, extracts first 2-3 pages of text, and scans for classification keywords:

| Keywords found | Classification |
|---|---|
| "shall comply", "mandatory", "disqualified", "failure to" | technical / requirements |
| "unit price", "total price", "qty", "amount", "SAR", "USD" | commercial / pricing |
| "whereas", "hereby agrees", "indemnify", "liability", "jurisdiction" | legal |
| "cybersecurity", "access control", "encryption", "vulnerability", "NCA", "ISO 27001" | compliance |
| "authorized signatory", "chamber of commerce", "registration number" | admin / certificate |

#### Implementation

```typescript
function classifyFile(filename: string, folder: string, content?: string): Classification {
  // Stage 1: filename patterns
  const filenameMatch = matchFilenamePatterns(filename);
  if (filenameMatch.confidence > 0.8) return filenameMatch;
  
  // Stage 2: folder location
  const folderMatch = matchFolderPatterns(folder);
  if (folderMatch.confidence > 0.7) return folderMatch;
  
  // Stage 3: content keywords (opens file)
  const contentMatch = scanContentKeywords(content);
  return contentMatch; // always returns something, even if low confidence
}
```

Each stage returns a confidence score. If stage 1 matches with >0.8, it doesn't bother opening the file. This keeps the classifier fast — most RFP packages have descriptive filenames (Aramco numbers everything, government uses standard naming).

Files that score below 0.5 confidence after all three stages get flagged for human review at checkpoint 1 — "I couldn't classify this file, please tell me what it is."

The classifier also detects **file format** (PDF vs DOCX vs XLSX vs DWG) to route to the correct parser downstream — the requirements extractor needs text extraction, the BoQ parser needs Excel column analysis, and engineering drawings get flagged as "cannot auto-process" since DWG files require CAD software.

#### Testing criteria

- Classify all 16 files from Aramco Storage fixture matching manual_classification.json with 100% accuracy
- Unit test: 5 file types × 3 files each = 15 assertions
- Confidence threshold: >0.8 for filename matches, >0.7 for folder matches, >0.5 for content matches
- Files below 0.5 must be flagged for human review (not silently skipped)

---

## Step 2: Missing Document Detector

**Purpose:** Identify documents that are referenced in the RFP but not present in the package.

**Input:** Classified file list + extracted text from technical/legal documents
**Output:** List of missing documents with reference source, page number, and severity

### How it works

Scans all classified documents (especially technical requirements and scope docs) for phrases that reference external documents. Cross-references against the actual files in the package.

#### Reference detection patterns (from RFP_Compliance_Patterns.md §4)

**Internal cross-references:**
```regex
(?:refer\s+to|as\s+per|see|in\s+accordance\s+with)\s+(Annex|Appendix|Attachment|Exhibit|Schedule)\s+[A-Z0-9]+
(?:paragraph|section|clause)\s+\d+[\.\d]*
```

**Aramco engineering standards (detected by code pattern):**
```regex
SACS-\d{3}     # Saudi Aramco Cybersecurity Standards (e.g., SACS-002)
SAES-[A-Z]-\d{3}  # Saudi Aramco Engineering Standards
SAEP-\d+       # Saudi Aramco Engineering Procedures
GI-\d+\.\d+    # General Instructions
CAP-\d+        # Cybersecurity Architecture Patterns
SAMSS-\d+      # Saudi Aramco Materials System Specifications
```

**External standards:**
```regex
ISO\s+\d{4,5}(?:[-:]\d{4})?    # ISO standards (e.g., ISO 27001:2022)
NIST\s+(?:SP\s+)?800-\d+       # NIST special publications
NCA\s+ECC                       # NCA Essential Cybersecurity Controls
NFPA\s+\d+                      # Fire protection standards
API\s+\d+                       # American Petroleum Institute standards
```

**Generic reference language:**
```regex
(?:the\s+attached|enclosed\s+herewith|accompanying\s+document)
(?:as\s+defined\s+in|pursuant\s+to|subject\s+to\s+the\s+provisions\s+of)
```

#### Cross-reference logic

```typescript
function detectMissingDocuments(
  classifiedFiles: ClassifiedFile[],
  extractedText: Map<string, string>
): MissingDocument[] {
  const missing: MissingDocument[] = [];
  const availableFiles = classifiedFiles.map(f => f.filename.toLowerCase());
  
  for (const [filename, text] of extractedText) {
    const references = extractReferences(text); // returns [{ref, pattern, page, line}]
    
    for (const ref of references) {
      // Check if referenced document exists in package
      const found = availableFiles.some(f => 
        f.includes(ref.normalized) || fuzzyMatch(f, ref.normalized) > 0.8
      );
      
      if (!found) {
        missing.push({
          referencedDoc: ref.ref,
          referencedIn: filename,
          page: ref.page,
          line: ref.line,
          pattern: ref.pattern,
          severity: classifySeverity(ref), // 'critical' if compliance standard, 'warning' if appendix
        });
      }
    }
  }
  return missing;
}
```

#### Severity classification

| Reference type | Severity | Rationale |
|---|---|---|
| SACS/SAES/CAP standards | Critical | Compliance failure — cannot assess without the standard |
| Annex/Appendix with technical scope | Critical | May contain mandatory requirements |
| Schedule/Attachment with commercial terms | High | May affect pricing or payment terms |
| ISO/NIST/NCA references | Medium | Can be sourced publicly if not in package |
| Generic "see attached" references | Low | May be informational |

#### Real-world example

From the Diriyah VSS project (confirmed by Shahid): the RFP referenced "Annex A — Detailed Scope of Work" but the annex was not included in the package. The detector would flag:

```json
{
  "referencedDoc": "Annex A — Detailed Scope of Work",
  "referencedIn": "RFP_Terms_and_Conditions.pdf",
  "page": 12,
  "line": "refer to Annex A for the detailed scope of work",
  "severity": "critical",
  "action": "Request from client before proceeding"
}
```

#### Testing criteria

- Detect 3+ known missing references in Aramco DMM7++ fixture (which references SACS-002, SACS-012, etc.)
- No false positives on documents that ARE present in the package
- Correctly classify severity: SACS references = critical, generic references = low
- Unit test: 5 reference patterns × 2 cases (present + missing) = 10 assertions

---

## Step 3: Requirements Extractor

**Purpose:** Parse all technical documents and extract every requirement, classifying each as mandatory, optional, or conditional.

**Input:** Text extracted from all technical and compliance documents
**Output:** Structured requirements list with ID, text, classification, source file, page

### How it works

Uses NLP-based classification of requirement language. The classifier is built from regex patterns extracted from 33+ real mandatory examples, 22+ optional examples, and 26+ conditional examples in `RFP_Compliance_Patterns.md §1`.

#### Requirement language patterns

**Mandatory indicators (must do — non-compliance risks disqualification):**
```regex
\b(shall)\b(?!\s+(not|neither))
\b(must)\b(?!\s+(not|neither))  
\b(required\s+to|is\s+required|are\s+required)\b
\b(mandatory|obligatory)\b
\b(will\s+be\s+disqualified|failure\s+to\s+comply)\b
\b(shall\s+not|must\s+not|is\s+prohibited)\b
```

Real examples from Aramco RFPs:
- "Vendor **shall** provide 24×7 technical support with 4-hour response time"
- "All equipment **must** be new and unused"
- "Failure to comply with SACS-002 **will result in** disqualification"
- "It is **mandatory** that the proposed solution supports IPv6"
- "Vendor **shall not** subcontract any portion without written approval"

**Optional indicators (nice to have — no penalty for missing):**
```regex
\b(should|may|can|could)\b
\b(recommended|preferred|desirable|optional)\b
\b(it\s+is\s+(suggested|advisable|preferable))\b
\b(where\s+possible|if\s+feasible|when\s+practicable)\b
```

Real examples:
- "The solution **should** support future expansion to 10,000 users"
- "It is **preferred** that the vendor has prior experience in the oil and gas sector"
- "The vendor **may** propose alternative solutions that meet the same objectives"
- "**Where possible**, the solution should leverage existing infrastructure"

**Conditional indicators (depends on context — may become mandatory):**
```regex
\b(if\s+applicable|where\s+required|as\s+needed)\b
\b(at\s+(?:Saudi\s+Aramco(?:'s)?|the\s+(?:client|company)(?:'s)?)\s+(?:sole\s+)?discretion)\b
\b(unless\s+otherwise\s+(?:specified|agreed|directed))\b
\b(subject\s+to|contingent\s+upon|provided\s+that)\b
```

Real examples:
- "**If applicable**, the vendor shall comply with IKTVA requirements"
- "Additional support resources may be requested **at Saudi Aramco's sole discretion**"
- "**Unless otherwise specified**, all documentation shall be in English"
- "**Subject to** site access approval, vendor shall complete installation within 90 days"

#### Extraction process

```typescript
interface Requirement {
  id: string;                    // R-001, R-002, ...
  text: string;                  // Full requirement sentence
  classification: 'mandatory' | 'optional' | 'conditional';
  confidence: number;            // 0-1 score
  sourceFile: string;            // Which file it came from
  page: number;
  indicators: string[];          // Which keywords triggered the classification
  section: string;               // RFP section heading (if available)
  relatedStandards: string[];    // Any referenced standards (SACS-002, ISO 27001, etc.)
}

function extractRequirements(text: string, sourceFile: string): Requirement[] {
  const sentences = splitIntoSentences(text);
  const requirements: Requirement[] = [];
  let reqCounter = 1;
  
  for (const sentence of sentences) {
    const mandatoryMatch = matchMandatoryPatterns(sentence);
    const optionalMatch = matchOptionalPatterns(sentence);
    const conditionalMatch = matchConditionalPatterns(sentence);
    
    // Skip sentences with no requirement language
    if (!mandatoryMatch && !optionalMatch && !conditionalMatch) continue;
    
    // Determine classification by strongest signal
    let classification: 'mandatory' | 'optional' | 'conditional';
    let confidence: number;
    let indicators: string[];
    
    if (mandatoryMatch && mandatoryMatch.score > (optionalMatch?.score || 0)) {
      classification = 'mandatory';
      confidence = mandatoryMatch.score;
      indicators = mandatoryMatch.indicators;
    } else if (conditionalMatch && conditionalMatch.score > (optionalMatch?.score || 0)) {
      classification = 'conditional';
      confidence = conditionalMatch.score;
      indicators = conditionalMatch.indicators;
    } else {
      classification = 'optional';
      confidence = optionalMatch?.score || 0.5;
      indicators = optionalMatch?.indicators || [];
    }
    
    requirements.push({
      id: `R-${String(reqCounter++).padStart(3, '0')}`,
      text: sentence.trim(),
      classification,
      confidence,
      sourceFile,
      page: sentence.page,
      indicators,
      section: sentence.sectionHeading || '',
      relatedStandards: extractStandardReferences(sentence.text),
    });
  }
  
  return requirements;
}
```

#### Edge cases

- **Negated mandatory:** "The vendor shall **not** be required to provide training" — this is an exclusion, not a requirement. The `(?!\s+(not|neither))` negative lookahead in the mandatory regex handles this, but the surrounding context must also be checked.
- **Compound sentences:** "The vendor shall provide installation services and **may** optionally provide training" — one sentence, two requirements (one mandatory, one optional). The extractor should split compound sentences at conjunctions.
- **Arabic content:** Some government RFPs have bilingual requirements. Arabic requirement language uses different keywords ("يجب" = must, "ينبغي" = should). Month 1 focuses on English extraction; Arabic is flagged for human review.

#### Testing criteria

- Extract requirements from Aramco Storage `Comments.docx` — count within 10% of manual classification
- Mandatory/optional/conditional split matches manual classification
- No false positives on non-requirement sentences (e.g., descriptions, definitions)
- Integration test: 1 fixture file, 3 assertions (count, split, no false positives)

---

## Step 4: Legal Trap Flagger

**Purpose:** Detect clauses that could lead to disqualification, penalties, or unfavorable contract terms if missed.

**Input:** Text from all legal and commercial documents
**Output:** Risk flags with severity, source, and recommended action

### How it works

Scans for three categories of risk patterns from `RFP_Compliance_Patterns.md §5`.

#### Category 1: Automatic disqualification triggers (9 patterns)

These cause immediate rejection if not complied with:

```regex
# Bid bond / financial guarantee requirements
\b(bid\s+bond|bank\s+guarantee|performance\s+bond)\b.*\b(required|mandatory|shall\s+submit)\b

# Submission deadline
\b(closing\s+date|submission\s+deadline|latest\s+date\s+for\s+submission)\b

# Format mandates
\b(sealed\s+envelope|original\s+and\s+\d+\s+copies|hardcopy\s+submission)\b
\b(naming\s+convention|file\s+format|shall\s+be\s+submitted\s+in)\b

# Eligibility / prequalification
\b(prequalified\s+vendors\s+only|restricted\s+to|eligible\s+bidders)\b

# Declaration requirements
\b(conflict\s+of\s+interest\s+declaration|anti-bribery|non-collusion)\b
```

Real example: "Bids received after the closing date of 15-March-2026 at 14:00 AST **will not be considered under any circumstances**."

**Action:** Flag as CRITICAL. Display prominently at checkpoint 1. These are pass/fail items.

#### Category 2: Discretionary rejection triggers (9 patterns)

These give the client grounds to reject but aren't automatic:

```regex
# Incomplete submission
\b(incomplete\s+submission|missing\s+document|partial\s+response)\b.*\b(may\s+be\s+rejected|reserves\s+the\s+right)\b

# Non-compliance with evaluation criteria
\b(minimum\s+score|threshold|passing\s+mark)\b.*\b(\d+%|\d+\s+points)\b

# Experience requirements
\b(minimum\s+\d+\s+years?\s+experience|demonstrated\s+track\s+record|similar\s+projects)\b

# Financial requirements
\b(annual\s+turnover|financial\s+capability|audited\s+financial\s+statements)\b
```

**Action:** Flag as HIGH. Engineer should verify compliance before submission.

#### Category 3: Contract breach / termination triggers (9 patterns)

These apply post-award but affect how the proposal should be written:

```regex
# Liquidated damages
\b(liquidated\s+damages|penalty\s+clause|delay\s+penalty)\b.*\b(\d+%|SAR|USD)\b

# Termination for convenience
\b(terminate\s+for\s+convenience|without\s+cause|at\s+any\s+time)\b

# Unlimited liability
\b(unlimited\s+liability|no\s+cap\s+on\s+liability|full\s+liability)\b

# IP ownership
\b(all\s+intellectual\s+property|work\s+product\s+shall\s+belong|assigns\s+all\s+rights)\b

# Insurance requirements
\b(professional\s+indemnity\s+insurance|public\s+liability\s+insurance)\b.*\b(\d+.*(?:million|SAR|USD))\b
```

**Action:** Flag as MEDIUM. Include in risk assessment for proposal pricing. Liquidated damages affect margin calculation in E2.

#### Compliance deadline extractor

In addition to pattern matching, the flagger extracts specific deadlines with exact timeframes:

```typescript
interface ComplianceDeadline {
  event: string;          // "Bid submission"
  deadline: string;       // "15-March-2026 14:00 AST"
  daysRemaining: number;  // Calculated from current date
  source: string;         // "T&C Section 3.2"
  severity: 'critical' | 'high';
}
```

Real deadlines found in Aramco RFPs:
- Bid submission closing date
- Bid validity period (typically 90-180 days)
- Bid bond validity (typically bid validity + 30 days)
- Questions/clarifications deadline
- Pre-bid meeting date
- Performance bond submission (within N days of award)

#### Testing criteria

- Detect all 3 disqualification triggers in Aramco Storage fixture
- No false positives on non-risk language
- Correctly classify severity: bid bond = critical, IP ownership = medium
- Extract at least 2 deadlines with correct dates
- Unit test: 9 automatic triggers × 1 positive + 1 negative = 18 assertions

---

## Step 5: Human Checkpoint #1

**Purpose:** Engineer reviews extracted requirements, file classifications, missing documents, and risk flags before proceeding to compliance mapping.

**Input:** All outputs from steps 1-4
**Output:** Approved (proceed) or revision requested (re-run steps 2-4 with notes)

### What the engineer reviews

The checkpoint UI page displays four sections:

#### Section A: File Classification Results

| File | Detected Type | Confidence | Action |
|---|---|---|---|
| Purchase_Requisition.docx | technical / requirements | 0.95 | ✓ Correct |
| BOQ_4203193153.xlsx | commercial / boq_template | 0.92 | ✓ Correct |
| FMG_Facilities.pdf | technical / site_spec | 0.78 | ✓ Correct |
| Meeting_Notes.msg | ??? | 0.35 | ⚠ Needs manual classification |

The engineer can:
- Confirm or reclassify any file
- Mark files as "not relevant" (e.g., duplicate, outdated version)
- Add files that were missed (e.g., received separately via email)

#### Section B: Missing Document Flags

| Referenced Document | Referenced In | Page | Severity | Action |
|---|---|---|---|---|
| SACS-002 Third Party Cybersecurity | Purchase Requisition | 14 | Critical | Request from client |
| Annex A — Detailed Scope | T&C Document | 12 | Critical | Request from client |
| ISO 27001:2022 | Compliance Section | 8 | Medium | Source publicly |

The engineer can:
- Mark as "obtained" (if they already have it from another source)
- Mark as "not needed" (if the reference is informational, not mandatory)
- Mark as "requested from client" (and the pipeline pauses until received)

#### Section C: Requirements Summary

```
Total requirements extracted: 42
  Mandatory: 28 (67%)
  Optional:  10 (24%)
  Conditional: 4 (9%)

Low confidence extractions (< 0.7): 3
  R-015: "The solution should ideally support..." → classified as optional (0.62)
  R-023: "Subject to approval, vendor will..." → classified as conditional (0.58)
  R-038: "It is expected that..." → classified as mandatory (0.65)
```

The engineer can:
- Reclassify any requirement
- Merge duplicate requirements
- Add requirements that were missed
- Delete false positives

#### Section D: Risk Flags

Displayed as a prioritized list:

```
CRITICAL (2):
  🔴 Bid bond of 2% required — deadline: 15-March-2026
  🔴 SACS-002 compliance mandatory — standard not in package

HIGH (3):
  🟡 Minimum 5 years experience in similar projects required
  🟡 Financial statements for last 3 years required
  🟡 Submission naming convention: "[Company]_[OP-Number]_Technical.pdf"

MEDIUM (4):
  🟠 Liquidated damages: 0.5% per week of delay, capped at 10%
  🟠 Termination for convenience with 30-day notice
  🟠 All IP transfers to client upon payment
  🟠 Professional indemnity insurance: minimum SAR 5,000,000
```

### Revision loop

If the engineer requests revision:
- Revision notes are injected into the next engine call
- Steps 2-4 re-run with the corrections
- Maximum 3 revision loops before escalating to manual editing
- Each revision only re-processes the flagged items, not the entire package

### Testing criteria

- Checkpoint page renders all 4 sections with correct data from fixture
- Approve action advances pipeline state to step 6
- Revision action re-triggers steps 2-4 with engineer notes included
- Reject action halts pipeline with reason logged

---

## Step 6: Evaluation Criteria Analyzer

**Purpose:** Extract how the client will score and evaluate the proposal, including weightings, pass/fail criteria, and scoring methodology.

**Input:** Commercial and technical documents (especially evaluation criteria docs, questionnaires)
**Output:** Structured evaluation criteria with categories, weights, and thresholds

### How it works

Searches for evaluation methodology in three places (from RFP_Compliance_Patterns.md §2):

#### Source 1: Standalone evaluation document

Some RFPs include a separate `Technical Evaluation Questionnaire.xlsx` (found in OP-2023-136618). This typically has:
- 3-level compliance system: Supported / Will be Customized / Not Supported
- Category weightings (e.g., Technical 60%, Commercial 30%, Experience 10%)
- Minimum passing threshold (e.g., 70% technical score required)

#### Source 2: Evaluation section within RFP document

```regex
\b(evaluation\s+criteria|scoring\s+methodology|assessment\s+criteria)\b
\b(technical\s+score|commercial\s+score|weighted\s+score)\b
\b(minimum\s+(?:acceptable|passing)\s+score|threshold)\b
\b(envelope\s+(?:1|2|3|A|B|C))\b  # Sequential envelope evaluation
```

#### Source 3: Aramco-specific evaluation patterns

Aramco uses a sequential envelope evaluation:
1. **Envelope 1 (Administrative):** Pass/fail on documentation completeness
2. **Envelope 2 (Technical):** Scored against Technical Evaluation Questionnaire
3. **Envelope 3 (Commercial):** Only opened if Envelope 2 passes threshold

Plus IKTVA scoring:
- Local content percentage
- Saudization ratio
- In-kingdom procurement value
- Training and development investment

#### Output structure

```typescript
interface EvaluationCriteria {
  methodology: 'sequential_envelope' | 'weighted_score' | 'pass_fail' | 'best_value';
  envelopes: {
    name: string;           // "Technical", "Commercial", "Administrative"
    weight: number;         // 0-100
    passThreshold: number;  // Minimum score to pass (0 if not specified)
    criteria: {
      name: string;         // "System Architecture"
      weight: number;       // Within this envelope
      scoringScale: string; // "Supported/Customized/Not Supported" or "1-10"
    }[];
  }[];
  iktva: {
    required: boolean;
    minimumScore: number;   // e.g., 30%
    categories: string[];   // What's scored
  } | null;
  disqualificationCriteria: string[]; // Pass/fail items
}
```

#### Testing criteria

- Extract evaluation methodology from Technical Evaluation Questionnaire.xlsx in fixture
- Correctly identify sequential envelope methodology when present
- Extract IKTVA requirements when referenced
- Return null/empty for projects with no evaluation criteria (valid case)

---

## Step 7: Vendor List Extractor

**Purpose:** Extract the client's preferred or mandatory vendor list from the BoQ or RFP documents.

**Input:** BoQ Excel file + technical requirements documents
**Output:** List of preferred/required vendors with product categories

### How it works

Vendor preferences appear in three places:

#### Source 1: BoQ Excel — Product_Vendors tab

The Diriyah ESS_BoQ has a dedicated `Product_Vendors` tab listing approved vendors per product category. The extractor looks for sheet names containing "vendor", "brand", "manufacturer", or "OEM".

```typescript
function extractVendorListFromBoQ(workbook: ExcelWorkbook): VendorPreference[] {
  // Check for dedicated vendor tab
  const vendorSheet = workbook.sheets.find(s => 
    /vendor|brand|manufacturer|oem|approved/i.test(s.name)
  );
  
  if (vendorSheet) {
    return parseVendorSheet(vendorSheet);
  }
  
  // Check for vendor column in BoQ sheet
  const boqSheet = workbook.sheets.find(s => /boq|bill/i.test(s.name));
  if (boqSheet) {
    const vendorCol = findColumnByHeader(boqSheet, /vendor|brand|oem|manufacturer/i);
    if (vendorCol) {
      return extractVendorColumn(boqSheet, vendorCol);
    }
  }
  
  return []; // No vendor preferences found
}
```

#### Source 2: RFP document text

```regex
\b(preferred\s+vendor|approved\s+vendor|approved\s+brand)\b
\b(Cisco|Fortinet|Palo\s+Alto|HPE|Dell|Juniper|Aruba|Huawei)\b
\b(or\s+equivalent|or\s+equal|or\s+approved\s+alternative)\b
```

Real example from Diriyah RFP screenshots: "refer to Client's Preferred Vendor List in BoQ xl file"

#### Source 3: Specification documents

Some RFPs specify vendors indirectly by referencing specific product models:
- "Cisco Catalyst 9300 series or equivalent" → Cisco preferred
- "FortiGate 600F or equivalent" → Fortinet preferred

#### Output structure

```typescript
interface VendorPreference {
  vendor: string;          // "Cisco", "Fortinet"
  category: string;        // "Switching", "Firewall", "Wireless"
  status: 'required' | 'preferred' | 'or_equivalent';
  source: string;          // "Product_Vendors tab" or "RFP Section 4.2"
  specificModels: string[]; // ["C9300-48U", "C9300-24U"] if mentioned
}
```

#### Testing criteria

- Extract vendor list from Diriyah ESS_BoQ Product_Vendors tab
- Detect "or equivalent" language correctly (status = 'or_equivalent', not 'required')
- Return empty list for RFPs with no vendor preferences (valid case)

---

## Step 8: Sector Detector

**Purpose:** Determine the client's industry sector to select the correct compliance framework.

**Input:** Client name, RFP content, project scope
**Output:** Detected sector with confidence score

### How it works

Three detection methods:

#### Method 1: Client name lookup

Known clients from the STC project corpus (42 project areas):

| Client name pattern | Sector |
|---|---|
| Aramco, Saudi Aramco | oil_and_gas |
| SME Bank, Riyad Bank, Al Rajhi | banking |
| Diriyah, Ministry of *, Emara | government |
| Nesma, Red Sea, Sindalah | hospitality |
| SABIC, Chemanol, Yanbu | petrochemical |
| STC, Mobily, Zain | telecom |
| King * Hospital, KFSHRC | healthcare |

#### Method 2: Content keyword analysis

```regex
# Oil & Gas
\b(upstream|downstream|refinery|drilling|pipeline|FEED|EPC|brownfield|greenfield)\b

# Banking / Finance
\b(core\s+banking|ATM|branch\s+network|SWIFT|PCI\s+DSS|card\s+processing)\b

# Government
\b(e-government|Etimad|government\s+portal|ministry|municipal|citizen\s+services)\b

# Healthcare
\b(hospital|clinic|PACS|HIS|EMR|patient|medical|healthcare)\b

# Hospitality
\b(hotel|resort|guest\s+room|IPTV|hospitality|PMS|key\s+card)\b

# Telecom
\b(BSS|OSS|core\s+network|RAN|5G|spectrum|subscriber|MVNO)\b
```

#### Method 3: Compliance standard references

If the RFP references specific standards, the sector is implied:
- SAMA CSF → banking
- NCA ECC → government (or any Saudi entity)
- SACS/SAES → oil_and_gas (Aramco specifically)
- ADHICS → healthcare (UAE)
- PDPL → any Saudi entity (Personal Data Protection Law)

#### Output

```typescript
interface SectorDetection {
  sector: 'oil_and_gas' | 'banking' | 'government' | 'hospitality' | 'healthcare' | 'telecom' | 'petrochemical' | 'general';
  confidence: number;
  method: 'client_lookup' | 'content_keywords' | 'standard_reference';
  evidence: string;  // What triggered the detection
}
```

#### Testing criteria

- Detect "oil_and_gas" for Aramco fixtures with >0.9 confidence
- Detect "government" for NCD fixture
- Fall back to "general" when no sector-specific signals found
- Client name lookup takes priority over content keywords

---

## Step 9: Compliance Framework Selector

**Purpose:** Select the applicable compliance framework(s) based on the detected sector and country.

**Input:** Detected sector + country (from project metadata)
**Output:** Selected framework(s) with justification

### How it works

A deterministic mapping — no AI needed:

| Sector | Country | Primary Framework | Secondary Framework |
|---|---|---|---|
| government | KSA | NCA ECC-2:2024 | ISO 27001:2022 |
| banking | KSA | SAMA CSF | NCA ECC-2:2024 + ISO 27001 |
| oil_and_gas | KSA (Aramco) | NCA ECC-2:2024 + SACS-002 | ISO 27001 |
| healthcare | KSA | NCA ECC-2:2024 | ADHICS (future) |
| telecom | KSA | NCA ECC-2:2024 | ISO 27001 |
| hospitality | KSA | NCA ECC-2:2024 | ISO 27001 |
| any | UAE | ISO 27001 | NESA |
| any | International | ISO 27001 | NIST CSF |

Additionally, if the RFP explicitly references a standard (detected in step 2 or step 3), that standard is always included regardless of the mapping above.

```typescript
function selectFrameworks(
  sector: SectorDetection,
  country: string,
  explicitlyReferencedStandards: string[]
): SelectedFramework[] {
  // Start with sector+country mapping
  const frameworks = SECTOR_FRAMEWORK_MAP[sector.sector]?.[country] || DEFAULT_FRAMEWORKS;
  
  // Add any explicitly referenced standards
  for (const standard of explicitlyReferencedStandards) {
    if (!frameworks.some(f => f.id === standard)) {
      frameworks.push({ id: standard, source: 'explicitly_referenced', priority: 'high' });
    }
  }
  
  return frameworks;
}
```

#### Testing criteria

- Aramco + KSA → NCA ECC + SACS-002 + ISO 27001
- Banking + KSA → SAMA CSF + NCA ECC + ISO 27001
- Unknown sector + KSA → NCA ECC + ISO 27001 (safe default)
- Explicitly referenced NIST CSF always included regardless of sector

---

## Step 10: Compliance Matrix Generator

**Purpose:** Map each extracted requirement to framework controls and assign compliance status.

**Input:** Requirements baseline (from step 3), selected frameworks (from step 9), proposed solution context
**Output:** Compliance matrix with requirement-to-control mappings and compliance status

### How it works

Three-step matching process:

#### Step 10a: Keyword-to-control mapping

For each requirement, the generator searches the framework control descriptions for keyword matches.

Example: Requirement "Vendor shall implement anti-virus protection with daily signature updates" matches:
- NCA ECC-2:2024 control 2-10 (Vulnerability Management)
- ISO 27001:2022 control 8.7 (Protection against malware)
- SACS-002 TPC control for endpoint protection

The matching uses the structured framework JSONs (NCA_ECC2_2024.json, SAMA_CSF.json, ISO_27001_2022_Annex_A.json) which contain control IDs, names, and domain descriptions.

```typescript
function mapRequirementToControls(
  requirement: Requirement,
  frameworks: SelectedFramework[]
): ControlMapping[] {
  const mappings: ControlMapping[] = [];
  
  for (const framework of frameworks) {
    const controls = loadFrameworkControls(framework.id);
    
    for (const control of controls) {
      const similarity = calculateSimilarity(requirement.text, control.description);
      
      if (similarity > MAPPING_THRESHOLD) { // 0.6
        mappings.push({
          requirementId: requirement.id,
          frameworkId: framework.id,
          controlId: control.id,
          controlName: control.name,
          similarity,
        });
      }
    }
  }
  
  // Sort by similarity, keep top 3 matches per framework
  return mappings
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 3 * frameworks.length);
}
```

#### Step 10b: Compliance status assignment

For each requirement × control pair, assigns one of four statuses:

| Status | Meaning | When to use |
|---|---|---|
| **Compliant** | Fully addressed by proposed solution | Solution meets or exceeds the requirement |
| **Partial** | Addressed with conditions or limitations | Solution covers most but not all aspects |
| **Non-Compliant** | Not addressed | Solution cannot meet this requirement |
| **Alternative Offered** | Met differently than specified | Solution achieves the same outcome via a different approach |

The status is initially assigned by comparing the requirement against the 58 past compliance matrices from the STC corpus. If similar requirements were historically marked as "Comply" for similar solution types, the generator assigns "Compliant" as a draft.

This is the step where the automated reviewer (from the Testing Protocol) is most valuable — it checks: "Does every mandatory requirement have a status? Are there any 'Compliant' assignments that contradict the proposed solution?"

#### Step 10c: Gap detection

After mapping, the generator identifies two types of gaps:

**Coverage gaps:** Framework controls that have NO corresponding requirement from the RFP. This means the client didn't ask about it, but the framework requires it. The engineer may want to proactively address these in the proposal.

**Orphan requirements:** RFP requirements that map to NO framework control. These are custom client needs outside standard frameworks — they still need to be addressed but don't map to a compliance standard.

#### Output: Compliance matrix (.xlsx)

Column structure per playbook §6.2:

| Column | Description | Source |
|---|---|---|
| Req # | R-001, R-002, ... | Step 3 |
| RFP Requirement Text | Full requirement sentence | Step 3 |
| Classification | Mandatory / Optional / Conditional | Step 3 |
| Framework | NCA ECC / SAMA CSF / ISO 27001 / SACS-002 | Step 9 |
| Control ID | 2-10-1, 8.7, TPC-42 | Step 10a |
| Control Name | Vulnerability Management, Malware protection | Step 10a |
| Status | Compliant / Partial / Non-Compliant / Alternative | Step 10b |
| TP Section | §10.2 (where this will be addressed in the proposal) | Step 11 |
| Notes | Engineer comments, conditions, alternatives | Checkpoint 2 |
| Gap Type | None / Coverage Gap / Orphan Requirement | Step 10c |

#### Testing criteria

- Map 5 known requirements from Aramco Storage to correct NCA ECC controls
- At least 3 of 5 mappings match Shahid's actual compliance matrix
- Detect at least 1 coverage gap and 1 orphan requirement
- Generate valid .xlsx file that opens without errors
- Integration test: 5 requirement→control mappings verified

---

## Step 11: Cross-Reference Linker

**Purpose:** Map each requirement to the TP section where it will be addressed, creating traceability from RFP to proposal.

**Input:** Requirements baseline + compliance matrix + TP template structure (from TP_Template_Model.md)
**Output:** Updated compliance matrix with TP section references

### How it works

Uses the master TP section structure (16 sections from TP_Template_Model.md §1) to assign each requirement to the appropriate proposal section.

#### Mapping rules

| Requirement topic | TP Section |
|---|---|
| Architecture, design, topology | §6 — Proposed Solution |
| Hardware specifications, models | §6 — Proposed Solution + §Annexure (BoQ) |
| Software, licensing | §6 — Proposed Solution |
| Security, cybersecurity, access control | §10 — Security |
| Compliance, standards, certifications | §9 — Compliance Matrix |
| SLA, uptime, availability | §8 — SLA / Support |
| Implementation, timeline, milestones | §7 — Scope + Implementation |
| Training, knowledge transfer | §7 — Scope |
| Warranty, maintenance, support | §8 — SLA / Support |
| Payment terms, pricing | Not in TP (separate commercial proposal) |
| Experience, references, CVs | §15 — Company Profile + Annexure |
| Local content, IKTVA, Saudization | §9 — Compliance Matrix |

```typescript
function linkRequirementToTPSection(requirement: Requirement): string {
  const topicKeywords = extractTopics(requirement.text);
  
  for (const [topics, section] of TOPIC_SECTION_MAP) {
    if (topicKeywords.some(t => topics.includes(t))) {
      return section;
    }
  }
  
  return '§6'; // Default: Proposed Solution (catch-all for technical requirements)
}
```

This is a relatively simple mapping step. The value is that E3 (Proposal Engine) can later use these references to know which requirements belong in which section, ensuring every mandatory requirement is addressed somewhere in the proposal.

#### Testing criteria

- Every mandatory requirement has a TP section assigned (no nulls)
- Security requirements map to §10, not §6
- Commercial requirements correctly flagged as "not in TP"

---

## Step 12: Human Checkpoint #2

**Purpose:** Engineer validates the complete compliance matrix before it becomes an input to downstream engines (E2, E3, E5).

**Input:** Completed compliance matrix with all mappings, statuses, TP section links, and gap analysis
**Output:** Approved matrix (proceeds to downstream engines) or revision (re-runs steps 9-11)

### What the engineer reviews

#### Section A: Compliance Matrix Preview

Full matrix displayed as an interactive table. Engineer can:
- Change compliance status per row (Compliant ↔ Partial ↔ Non-Compliant ↔ Alternative)
- Edit notes per row
- Override framework control mapping
- Override TP section assignment

#### Section B: Gap Summary

```
Coverage gaps (framework controls with no matching RFP requirement): 8
  NCA ECC 2-8 (Cryptography) — not mentioned in RFP but required by ECC
  NCA ECC 3-1 (Business Continuity) — not mentioned in RFP
  ...

Orphan requirements (RFP requirements with no framework control): 3
  R-037: "Vendor shall provide on-site spare parts inventory" — no framework match
  R-041: "Solution shall support Arabic language interface" — no framework match
  ...
```

Engineer decides:
- Coverage gaps: "Address proactively in proposal" or "Skip — not relevant to this project type"
- Orphan requirements: "Add to scope" or "Flag as exclusion"

#### Section C: Automated Review Results

If the automated reviewer (from Testing Protocol) ran, its findings are displayed:

```
Reviewer score: 78/100
Issues found:
  ⚠ R-012 marked as Compliant but proposed solution doesn't include FortiSandbox (referenced in requirement)
  ⚠ 3 mandatory requirements have no compliance status assigned
  ⚠ R-029 maps to NCA ECC 2-5 (Network Security) but TP section is §8 (SLA) — should be §10 (Security)?
```

### After approval

The approved compliance matrix becomes a frozen artifact in the pipeline state. It feeds three downstream engines:
- **E2 (BoM):** Uses compliance requirements to ensure proposed equipment meets security standards
- **E3 (Proposal):** Inserts the matrix as §9 and uses TP section references to structure the proposal
- **E5 (Design):** Uses compliance requirements to inform security zone design and framework selection

#### Testing criteria

- Checkpoint page renders matrix with all columns from step 10
- Engineer can modify status, notes, and mappings
- Approved matrix is stored as frozen artifact in pipeline state
- Revision re-triggers steps 9-11 only (not steps 1-8)

---

## Outputs

### Output 1: Compliance Matrix (.xlsx)

The primary deliverable of E1. Column structure defined in step 10. Typically 20-100 rows depending on RFP complexity.

File naming: `e1_{opportunityId}_compliance_matrix_v{N}.xlsx`
Example: `e1_OP-2025-154381_compliance_matrix_v1.xlsx`

### Output 2: Requirements Baseline (JSON)

Structured data consumed by downstream engines. Contains all requirements with classifications, mapped to framework controls and TP sections.

```json
{
  "opportunityId": "OP-2025-154381",
  "totalRequirements": 42,
  "mandatory": 28,
  "optional": 10,
  "conditional": 4,
  "sector": "oil_and_gas",
  "frameworks": ["NCA_ECC", "SACS-002", "ISO_27001"],
  "requirements": [
    {
      "id": "R-001",
      "text": "Vendor shall provide 24×7 technical support with 4-hour response time",
      "classification": "mandatory",
      "frameworkMappings": [
        {"framework": "NCA_ECC", "control": "2-9-1", "status": "Compliant"}
      ],
      "tpSection": "§8",
      "notes": ""
    }
  ],
  "gaps": {
    "coverageGaps": [...],
    "orphanRequirements": [...]
  }
}
```

### Output 3: Risk Flags Report

Summary of all legal, compliance, and disqualification risks identified in step 4.

```json
{
  "critical": [
    {"flag": "Bid bond 2% required", "deadline": "2026-03-15", "source": "T&C §3.2"},
    {"flag": "SACS-002 compliance mandatory — standard not in package", "source": "Tech Spec §7"}
  ],
  "high": [...],
  "medium": [...],
  "deadlines": [
    {"event": "Bid submission", "date": "2026-03-15T14:00+03:00", "daysRemaining": 45}
  ]
}
```

### Downstream consumers

| Output | Consumed by | How it's used |
|---|---|---|
| Compliance matrix | E3 (Proposal) | Inserted as §9 of the TP |
| Requirements baseline | E2 (BoM) | Sizing inputs, vendor constraints |
| Requirements baseline | E4 (Discovery) | Cross-reference if RFI mode follows |
| Requirements baseline | E5 (Design) | Security requirements → zone design |
| Risk flags | E3 (Proposal) | Inform assumptions and exclusions sections |
| Vendor list | E2 (BoM) | Constrain SKU selection to preferred vendors |
| Evaluation criteria | E3 (Proposal) | Structure proposal to match scoring methodology |
