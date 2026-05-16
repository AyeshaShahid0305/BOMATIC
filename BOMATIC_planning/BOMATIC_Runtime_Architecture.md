# BOMATIC — Runtime Architecture

## Current Build Status (as of May 2026)

### What is ACTUALLY built and working:
- E1 Steps 1–4: file upload, text extraction, file classification, missing document detection, requirements extraction, legal trap detection
- E1 Checkpoint UI: displays classified files, requirements, risk flags
- E2: BoQ template detector and parser (FORMAT_1_CCW only) — no pricing, no Excel output
- E3: Section title list and GBB multiplier table only — no DOCX generation
- Basic FastAPI backend with database (PostgreSQL)
- Basic Next.js frontend (home page + E1 upload page)

### What is NOT yet built:
- E1 Steps 5–12: compliance matrix generation, framework mapping, bilingual detection, DOCX/XLSX output
- E2: pricing engine, catalog lookup, EoX checking, licensing calculator, Excel writeback
- E3: proposal generation, DOCX output, all AI narrative sections
- E4: does not exist
- E5: does not exist
- Pipeline coordinator: engines are not connected to each other
- Authentication: middleware exists but no user management
- Any downloadable output files

---

**Version:** 2.0 (replaces Hub-Spoke Architecture v1.0)
**Date:** 2026-05-09
**Change:** Complete redesign. Old version treated everything as Claude API calls. New version is hybrid: 65% deterministic code, 26% AI-with-validation, 9% pure AI.

---

## 1. First Commandment

**Never let the LLM do math, lookups, or rule-based validation. Those are code.**

BOMATIC is a deterministic system with AI assistance — not an AI system with deterministic guardrails.

---

## 2. Four Runtime Patterns

| Pattern | Role | Applied At | Rule |
|---|---|---|---|
| Neurosymbolic | Foundation theory | All engines | AI perceives, code validates — always |
| Hybrid Intelligence | Philosophy | E2 especially, all engines | Never let the LLM do math |
| Deterministic Guardrails | Pre/post gates around AI | E1, E4 | Code gate before AI, code gate after AI |
| Tool-use | AI reasons, code executes | E3, E5 | AI decides WHAT, code does IT |

---

## 3. Escalation Rule (all AI calls)

Every AI output that fails validation follows:

1. **Retry once** — code tells AI what was wrong, AI tries again with error injected
2. **Flag and proceed** — output passed to engineer with yellow warnings
3. **Human decides** — engineer fixes at checkpoint or accepts

The pipeline NEVER stops. The engineer ALWAYS receives output.

---

## 4. Per-Engine Runtime Flows

### 4.1 E1 — RFP Parser (Guardrails pattern)

**Character:** Mostly code with AI for NLP extraction. 8 deterministic steps, 2 AI-with-validation, 1 mixed.

```
RFP package → CODE: file classifier (regex 3-stage)
            → CODE: missing doc detector (regex reference extraction)
            → CODE: mandatory/optional regex (catches 80%)
            → AI CALL: ambiguous requirement interpretation (20%)
            │   ├── PRE-GATE: input is extracted text, not binary
            │   └── POST-GATE: classification matches regex patterns
            │         ├── PASS → add to requirements list
            │         ├── FAIL → retry once with error
            │         └── FAIL again → flag for engineer
            → CODE: vendor list extractor (Excel column parsing)
            → CODE: sector detector (lookup table)
            → CODE: framework selector (sector + country → frameworks)
            → AI CALL: compliance status assignment (judgment)
            │   └── POST-GATE: every control ID exists in framework DB
            → CODE: cross-reference linker (topic → TP section)
            → CODE: Excel matrix generation
            → REVIEWER: completeness check (Sonnet single-pass)
            → HUMAN CHECKPOINT: engineer reviews
```

**AI calls at runtime:** 2-3 narrow Sonnet calls
**Data consumed as code/DB:** Compliance frameworks, regex patterns, file taxonomy, standards registry, sector mapping
**Data consumed as AI context:** Past compliance matrices (few-shot examples for status assignment only)

---

### 4.2 E2 — BoM Engine (Hybrid Intelligence pattern)

**Character:** Almost entirely code. Zero pure-AI tasks. AI only for fuzzy SKU matching.

```
Input (RFP mode): client BoQ → CODE: template type detector (column patterns)
                             → CODE: BoQ parser (5 type-specific parsers)
                             → CODE: SKU exact-match (DB query)
                             → AI CALL (rare): fuzzy SKU match for ambiguous descriptions
                             │   └── POST-GATE: matched SKU exists in catalog
                             → CODE: accessory selector (model → PSU/fan/rail/cord lookup)
                             → CODE: licensing calculator (device + tier + term → SKU)
                             → CODE: support selector (site criticality → tier → SKU)
                             → CODE: cables/spares calculator (line items × rate)
                             → CODE: validation engine (9 rules)
                             │   ├── PoE budget: sum(device draw) ≤ PSU budget
                             │   ├── EoX: every SKU checked against lifecycle DB
                             │   ├── Stacking: kit + modules + cables per topology
                             │   ├── PSU redundancy: primary ≠ secondary SKU
                             │   ├── Antenna count: 4 per C9120AXE, 0 per internal
                             │   ├── Fan count: chassis-specific
                             │   ├── DNA opt-out: valid, don't flag
                             │   ├── AP-only: valid, don't flag
                             │   └── License deps: required licenses present
                             → CODE: cost stack (CS-001 through CS-009)
                             │   ├── CS-001: currency conversion
                             │   ├── CS-002: vendor discount
                             │   ├── CS-003: inhouse margin (V34+ only)
                             │   ├── CS-004: overhead (7 components)
                             │   ├── CS-005: cost with overhead
                             │   ├── CS-006a/b: selling price (margin/markup mode)
                             │   ├── CS-007: extended sell with embed discounts
                             │   ├── CS-008: STCS sale (revenue share)
                             │   └── CS-009: VAT
                             → CODE: Excel TA workbook generation
                             → CODE: distributor export formatting
                             → HUMAN CHECKPOINT: engineer reviews BoM + pricing

Input (RFI mode): component list from E5 → same pipeline from SKU matching onward
```

**AI calls at runtime:** 0-1 (only if fuzzy SKU matching needed)
**Data consumed as code/DB:** ALL — cost stack formulas, validation rules, accessory tables, pricing DB, BoQ parsers, device specs
**Data consumed as AI context:** None

---

### 4.3 E3 — Proposal Engine (Tool-use pattern)

**Character:** Mixed — code for structure and data, AI for writing. 3 pure-AI narrative tasks.

```
All upstream artifacts arrive
  → CODE: template selector (project type → section list, lookup table)
  → CODE: boilerplate inserter (8 sections, parameterized templates)
  │   ├── Confidentiality agreement
  │   ├── Purpose of document
  │   ├── PM methodology (12-aspect table)
  │   ├── Assumptions (9 standard items)
  │   ├── Exclusions (8 standard items)
  │   ├── Terms & conditions (13 clauses)
  │   ├── Company profile
  │   └── Vendor product boilerplate
  → CODE: artifact inserter (embed compliance matrix, BoQ, diagrams)
  → AI CALL: executive summary (synthesis from all inputs)
  │   └── POST-GATE: mentions client name, vendors match BoM, 150-300 words
  → AI CALL: understanding of requirements (paraphrase from E1/E4 data)
  │   └── POST-GATE: covers all mandatory requirements
  → AI CALL: proposed solution narrative (describe E5 architecture)
  │   └── POST-GATE: references correct topology, no hallucinated products
  → CODE: scope/implementation section (milestone template + data)
  → CODE: G/B/B pricing tiers (base price × configurable multipliers)
  → CODE: format compliance checker (naming, page limits, section presence)
  → CODE: version tracking (Ver X.Y increment)
  → CODE: .docx generation (docx-js)
  → CODE: PDF generation (LibreOffice conversion)
  → REVIEWER: placeholder check, section count, vendor consistency (Sonnet)
  → HUMAN CHECKPOINT: engineer reviews full TP (heavy editing expected)
```

**AI calls at runtime:** 3 Opus calls (exec summary, understanding, proposed solution)
**Data consumed as code/DB:** TP template structure, boilerplate blocks, G/B/B multipliers, format rules
**Data consumed as AI context:** Tone/structure guidelines from playbook §6-7

---

### 4.4 E4 — Discovery Engine (Guardrails pattern)

**Character:** Balanced — code for templates and parsing, AI for interpretation.

```
Sales request arrives
  → CODE: customer lookup (DB query — existing client? previous projects?)
  → CODE OR AI: project type detection
  │   ├── If keywords obvious → CODE (regex match)
  │   └── If ambiguous → AI CALL with POST-GATE (validate against known types)
  → CODE: questionnaire generation (select from 60-question template)
  → CODE: emphasis matrix (project type → §2.4 sections, lookup table)
  → AI CALL (optional): question customization beyond template
  │   └── POST-GATE: validate against §2.4 structure
  → HUMAN CHECKPOINT: engineer reviews questionnaire before sending
  
  ── PAUSE: send to client, wait for response (days/weeks) ──
  
  → CODE: format detection (Excel vs Word vs email vs text)
  → CODE (if Excel): structured column parsing — deterministic
  → AI CALL (if free text): interpret unstructured response
  │   └── POST-GATE: extracted data validates against required fields
  → AI CALL: gap detection — identify incomplete/vague answers
  │   └── POST-GATE: gaps reference actual questions from questionnaire
  → CODE: requirements baseline builder (validate 5-category schema)
  → CODE: distributor formatter (template rendering)
  → HUMAN CHECKPOINT: engineer validates requirements baseline
```

**AI calls at runtime:** 2-4 Sonnet calls (depends on input format)
**Data consumed as code/DB:** Question template, emphasis matrix, requirements schema, distributor template
**Data consumed as AI context:** 204 real question examples (for customization only)

---

### 4.5 E5 — Design Engine (Tool-use pattern)

**Character:** Code-heavy with AI for design narratives and recommendations.

```
Requirements baseline from E4 + compliance from E1
  → CODE: methodology selector (decision tree: project type → PPDIOO variant)
  → AI CALL: topology recommendation (which of 5 patterns fits best)
  │   └── POST-GATE: recommended pattern is one of 5 valid patterns
  → CODE: sizing calculator (users/bandwidth → device model, deterministic formula)
  → CODE: vendor compatibility checker (model → compatible accessories, DB lookup)
  → AI CALL: HLD narrative sections (solution overview, architecture, security, HA)
  │   └── POST-GATE: references correct topology, mentions selected vendor
  → CODE: HLD template population (12-section docx generation)
  → CODE: diagram generation (draw.io XML from templates + topology data)
  → HUMAN CHECKPOINT: engineer reviews HLD
  
  → CODE: IP/VLAN planning (subnet calculation algorithm)
  → CODE: port map generation (device model → port count → assignment)
  → CODE: cable schedule (physical topology → cable list)
  → CODE: QoS policy generation (vendor-specific templates)
  → CODE: migration approach selector (decision tree)
  → AI CALL: LLD narrative sections (detailed design descriptions)
  │   └── POST-GATE: IP addresses are valid, port counts match device specs
  → CODE: LLD template population (21-section docx generation)
  → CODE: rack elevation generation (device specs → layout)
  → CODE: compatibility validation (optics, stacking, FortiOS version)
  → HUMAN CHECKPOINT: engineer reviews LLD
  
  → CODE: component list output (for E2 consumption)
```

**AI calls at runtime:** 3 Opus calls (topology recommendation, HLD narrative, LLD narrative)
**Data consumed as code/DB:** Topology patterns, sizing rules, device specs, compatibility data, draw.io templates, decision trees
**Data consumed as AI context:** Design principles, HLD/LLD structure rules from playbook §3

---

## 5. Knowledge Pack Consumption Summary

| Consumption method | Count | Examples |
|---|---|---|
| TypeScript functions | 11 | Cost stack formulas, validation rules, sizing calculator, classifiers, parsers |
| Database tables | 8 | Compliance frameworks, vendor catalogs, device specs, accessory matrix, FX/VAT rates |
| TypeScript lookups | 5 | Sector→framework, project type→sections, emphasis matrix, methodology selector |
| Static templates | 4 | Boilerplate blocks, questionnaire template, QoS policies, draw.io XML patterns |
| Configurable JSON | 3 | OH defaults, G/B/B multipliers, discount patterns |
| AI system prompt (only when AI is called) | 4 | Past compliance matrices, AI writing guidelines, question examples, design narrative rules |
| **Total** | **35** | **31 deterministic (89%), 4 AI context (11%)** |

---

## 6. Inter-Engine Data Flow

Engines never communicate directly. All data passes through the pipeline state.

### 6.1 RFP Mode

```
E1 (Parser) → complianceMatrix, requirementsBaseline, riskFlags, vendorList, sector
  ↓
E2 (BoM) → bomWorkbook, filledClientBoq, distributorExport, pricingSummary
  ↓
E3 (Proposal) → technicalProposal, financialProposal, submissionPdf
```

### 6.2 RFI Mode

```
E4 (Discovery) → questionnaire → [client responds] → requirementsBaseline
  ↓
E5 (Design) → hldDocument, lldDocument, diagrams, ipVlanPlan, componentList
  ↓
E2 (BoM) → bomWorkbook, distributorExport, pricingSummary
  ↓
E3 (Proposal) → technicalProposal, financialProposal, submissionPdf
```

### 6.3 What Each Engine Reads from Upstream

| Engine | Reads from | Specific artifacts |
|---|---|---|
| E1 | Nothing (first in RFP mode) | — |
| E2 | E1 or E5 | vendorList, requirementsBaseline (E1) or componentList (E5) |
| E3 | E1, E2, E4, E5 | Everything — compliance matrix, BoM, requirements, diagrams |
| E4 | Nothing (first in RFI mode) | — |
| E5 | E1 and/or E4 | requirementsBaseline, frameworksSelected |

---

## 7. Human Checkpoints

10 checkpoints across 5 engines. Each is a UI page where the engineer reviews, edits, approves, or requests revision.

| # | Engine | Checkpoint | Revision max |
|---|---|---|---|
| 1 | E1 | Confirm requirements + file classifications | 3 |
| 2 | E1 | Validate compliance matrix | 3 |
| 3 | E2 | Confirm SKU selections | 3 |
| 4 | E2 | Review full BoM with pricing | 3 |
| 5 | E3 | Review full TP (heavy editing expected) | 3 |
| 6 | E4 | Review questionnaire before sending | 3 |
| 7 | E4 | Validate requirements baseline | 3 |
| 8 | E5 | Confirm design approach | 3 |
| 9 | E5 | Review HLD | 3 |
| 10 | E5 | Review LLD | 3 |

Revision loop: engineer notes → engine re-processes affected steps only → max 3 loops → then manual editing.

---

## 8. Automated Reviewer (Runtime GAN)

Single-pass Sonnet check between engine output and human checkpoint. Not a full adversarial loop — catches obvious failures so engineer's time isn't wasted.

| Engine | Reviewer checks |
|---|---|
| E1 | Every mandatory requirement has a framework mapping? Any "compliant" status contradicts the proposed solution? |
| E2 | Every SKU exists in catalog? Prices match price list? PoE budget adds up? PSU primary ≠ secondary? |
| E3 | Client name correct? Vendors match BoM? All boilerplate sections present? No placeholder text remaining? |
| E4 | All mandatory sections covered for this project type? Requirements baseline has all 5 categories? |
| E5 | Selected topology is one of 5 valid patterns? No IP overlaps? Port count within device capacity? |

---

## 9. What This Architecture Does NOT Do

- **No AI for math, lookups, or rule validation.** Those are TypeScript functions and DB queries.
- **No always-on AI context.** Only 4 of 35 knowledge packs load into AI prompts, and only when AI is actually called.
- **No agent-to-agent communication.** Engines pass data through pipeline state, never directly.
- **No framework dependency.** No LangGraph, CrewAI, Semantic Kernel. TypeScript + Claude API + Postgres.
- **No RAG.** Knowledge packs are curated files consumed as code/DB, not vector search.
- **Pipeline never stops on AI failure.** Retry → flag → human decides. Always.

---

## 10. Existing Codebase Integration

| Existing Component | Location | Hybrid Role | Changes Needed |
|---|---|---|---|
| Cisco Catalog API adapter | `src/lib/adapters/catalog` | Deterministic SKU/price lookup | Preserve. Extend with EoX queries. |
| Validation engine (8 rules) | `src/lib/validation/` | Deterministic validation | Extend with Shahid's 9 rules + Fortinet rules. |
| Excel export | `src/lib/export/xlsx` | Deterministic TA workbook generation | Extend with TA V35 121-column structure. |
| Document parsers | To build | Deterministic PDF/DOCX/XLSX ingestion | New. Use pdfplumber, python-docx, openpyxl. |
| Cost stack formulas | To build | Deterministic TypeScript functions (CS-001→CS-009) | New. From Tender_Analyzer_Model.md §2. |
| Compliance framework DB | To build | Deterministic control lookup | New. From NCA_ECC2_2024.json + SAMA_CSF.json + ISO_27001.json. |
| BoQ template parser | To build | Deterministic 5-type parser | New. From BoQ_Template_Patterns.md. |
| Fortinet price DB | To build | Deterministic SKU→price lookup | New. Parse from quarterly price list Excel. |
| Device specs lookup | To build | Deterministic model→specs query | New. From BOMATIC_Device_Specs.json. |
