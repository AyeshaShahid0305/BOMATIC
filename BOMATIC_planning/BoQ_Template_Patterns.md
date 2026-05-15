# BoQ Template Patterns

**Purpose:** Define the column structures and detection rules for each of the 5 BoQ input formats that E2's parser must handle.
**Status:** Format 1 documented from fixture. Formats 2–5 to be defined from STC corpus samples.

---

## How the parser uses this document

E2's template type detector (Step 1 of the BoM pipeline) reads column headers and sheet names from the incoming Excel file and matches them against the patterns below. Once a format is identified, the corresponding typed parser is invoked. All parsers normalize their output to the same internal `BoQLineItem` schema before SKU matching begins.

### Internal `BoQLineItem` schema (all formats normalize to this)

```typescript
interface BoQLineItem {
  partNumber:  string | null;   // Cisco/vendor SKU, null if description-only row
  description: string;          // Free-text description
  qty:         number;          // Quantity
  unitPrice:   number | null;   // List price in source currency, null if not provided
  totalPrice:  number | null;   // qty × unitPrice, null if not provided
  currency:    string;          // "USD", "SAR", etc. — detected from header or metadata
  serviceDurationMonths: number | null; // null for hardware, 12/36/60 for subscriptions
  lineType:    'hardware' | 'software' | 'service' | 'accessory' | 'unknown';
}
```

### Detection priority

The detector runs these checks in order and stops at the first match with confidence > 0.8:

1. Sheet name patterns
2. Column header exact match
3. Column header fuzzy match (normalised lowercase, stripped punctuation)
4. Cell value patterns in the first data row (e.g., Cisco SKU regex `[A-Z0-9]{3,}-[A-Z0-9-]+`)

---

## Format 1 — Simple Cisco SKU List

**Source file:** `backend/storage/e1_test_fixtures/BOQ_4203193153.xlsx`
**Origin:** Aramco RFQ. Minimal flat list of Cisco part numbers with quantities and unit prices.
**Read date:** 2026-05-15

### Sheet structure

| # | Sheet name | Purpose |
|---|---|---|
| 1 | `Main BOQ` | Single sheet — complete BoQ |

### Column structure (`Main BOQ`)

| Column | Header (exact) | Data type | Required | Notes |
|---|---|---|---|---|
| A | `Part Number` | string | Yes | Cisco PID / SKU (e.g., `C9300-48U-A`) |
| B | `Description` | string | Yes | Free-text product description |
| C | `Qty` | integer | Yes | Quantity |
| D | `Unit Price (USD)` | float | Yes | List price per unit in USD |
| E | `Total Price (USD)` | float | Derived | `Qty × Unit Price` — may be pre-filled or blank |

### Sample rows (from fixture)

| Part Number | Description | Qty | Unit Price (USD) | Total Price (USD) |
|---|---|---|---|---|
| C9300-48U-A | Cisco Catalyst 9300 48-port UPOE | 5 | 8,500 | 42,500 |
| C9300-NM-8X | Cisco Catalyst 9300 8x10GE Network Module | 5 | 1,200 | 6,000 |
| DNA-A-48-3Y | Cisco DNA Advantage 48-port 3-year license | 5 | 950 | 4,750 |

### Detection rules

```typescript
// Sheet name match
sheetName.toLowerCase() === 'main boq'                     // confidence 0.9

// Column header match (all 5 present → high confidence)
headers.includes('Part Number') &&
headers.includes('Description') &&
headers.includes('Qty') &&
headers.some(h => h.startsWith('Unit Price')) &&
headers.some(h => h.startsWith('Total Price'))             // confidence 0.95

// Fallback: first data cell matches Cisco SKU pattern
/^[A-Z][A-Z0-9]{1,}-[A-Z0-9]/.test(firstDataCell)        // confidence 0.7
```

### Parser behaviour

- **Header row:** Row 1 (always — no merged header rows or title rows above)
- **Data rows:** Row 2 onward, until first fully empty row
- **Currency:** Read from `Unit Price` column header parenthetical — `(USD)` → `"USD"`, `(SAR)` → `"SAR"`. Default `"USD"` if absent.
- **Line type detection:** Inferred from `Part Number` prefix and `Description` keywords:
  - `CON-*`, `SVS-*`, `SP-*` → `service`
  - `*-DNA-*`, `*-LIC-*`, `*-SW*`, `*-3Y`, `*-5Y` suffix → `software`
  - Everything else → `hardware` or `accessory` (resolved later by catalog lookup)
- **Total Price:** Recalculated as `qty × unitPrice` even if pre-filled, to catch rounding differences.
- **Empty / section-header rows:** Rows where `Part Number` is null and `Qty` is null are skipped.

### Limitations of this format

- No `Service Duration` column — subscription term must be inferred from SKU suffix (`-3Y`, `-5Y`, `-1Y`).
- No `Discount` column — list price only; discounts applied later in E2 cost stack (CS-002).
- No site, location, or module grouping — flat list with no hierarchy.
- No currency-conversion metadata — single-currency document assumed.

### Real-world extension (Cisco CCW export)

Production CCW estimates from the STC corpus (`Routing_Switching.xlsx`, `Wireless_2.xlsx`) extend this format with additional columns. When these files become available, the Format 1 parser should be extended to handle the full CCW column set:

| Additional column | CCW header | Notes |
|---|---|---|
| Smart Account flag | `Smart Account Mandatory` | "Yes" or "-" |
| Service duration | `Service Duration (Months)` | "---" for hardware, "36" for 3-year |
| Lead time | `Estimated Lead Time (Days)` | Integer days |
| Pricing term | `Pricing Term` | Usually blank |
| Discount % | `Disc(%)` | Applied against list price |
| Unit net price | `Unit Net Price` | List minus discount |
| Extended net price | `Extended Net Price` | `qty × unit net price` |

The footer section of CCW exports also adds `Product Total`, `Service Total`, `Subscription Total`, and `Total Price` summary rows — these must be detected and excluded from line-item parsing (they are not BoQ rows).

---

## Format 2 — Tender Analyzer BoQ Sheet (STCS Internal)

**Status:** To be defined.
**Source:** TA 2016B V34/V35 workbooks from OGF corpus — `BoQ` sheet within the multi-sheet Tender Analyzer.
**Key columns (from STC Data Inventory):** Item#, Category, Vendor, Supplier, Element, Part Number, Description, Unit, Qty, pricing columns. Bilingual Arabic + English headers.

---

## Format 3 — Construction / Civil BoQ (Client Template)

**Status:** To be defined.
**Source:** `NCD/RFQ Document/BOQ/BOQ.xlsx` — 4 sheets: General Requirements, MAIN BOQ, Day Work BOQ, Provisional Sum BOQ.
**Key columns (from STC Data Inventory):** REF / DESCRIPTION / QTY / UNIT / RATE / TOTAL — construction-style with section subtotals.

---

## Format 4 — Aramco RFQ Excel

**Status:** To be defined.
**Source:** `Aramco_4203193153.xlsx` and similar `Aramco_42031xxxxx.xlsx` files from OGF corpus.
**Key columns:** Aramco-specific format; exact structure requires reading the files from the STC corpus.

---

## Format 5 — Part-List with SOW Breakdown

**Status:** To be defined.
**Source:** `Copy of Sindalah_Mainland_BOQ v3.1.xlsx` from Nesma corpus.
**Key columns (from STC Data Inventory):** Part Number / Description / Service Duration / Qty + separate SOW breakdown sheet.

---

## Parser selection flowchart

```
Incoming Excel file
        │
        ▼
Does sheet named "Main BOQ" exist?
  Yes → Check for Part Number / Description / Qty / Unit Price columns
          Match → Format 1 parser
        No ↓
Does sheet named "BoQ" exist within a multi-sheet workbook (24+ sheets)?
  Yes → Check for bilingual headers / Item# / Category / Vendor columns
          Match → Format 2 parser (Tender Analyzer BoQ)
        No ↓
Does sheet named "MAIN BOQ" (uppercase) exist with REF + UNIT + RATE columns?
  Yes → Format 3 parser (Construction BoQ)
        No ↓
Does filename match /Aramco_42\d{8}/i?
  Yes → Format 4 parser (Aramco RFQ)
        No ↓
Does a sheet contain Part Number + Service Duration + SOW breakdown sheet?
  Yes → Format 5 parser (Part-List + SOW)
        No ↓
  Confidence < 0.5 → Flag for engineer: "Unrecognised BoQ format"
```
