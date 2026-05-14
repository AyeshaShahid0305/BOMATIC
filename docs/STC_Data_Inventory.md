# STC Knowledge Base — Data Inventory

**Generated:** 2026-05-08
**Source:** `/stc-knowledge/` (13 zip archives extracted + 7 loose files)
**Purpose:** Map all available STC project data against the BOMATIC Capability Matrix (16 rows, 6 gates)

---

## Section 1 — File System Summary

### Total Extracted Volume

| Metric | Value |
|---|---|
| Total files (excluding .zip) | 9,166 |
| Total size (extracted) | ~21 GB |
| Unique project/client areas | 42 |
| Unique opportunities (OP-xxxxx) | 307 |

### File Counts by Extension

| Extension | Count | Category |
|---|---|---|
| .pdf | 3,350 | Documents / drawings |
| .dwg | 1,940 | AutoCAD drawings |
| .xlsx | 1,307 | Spreadsheets |
| .docx | 960 | Word documents |
| .msg | 811 | Email correspondence |
| .rar | 140 | Compressed archives |
| .xls | 123 | Legacy spreadsheets |
| .xlsb | 114 | Binary spreadsheets |
| .jpg/.jpeg/.JPG | 119 | Images |
| .pptx | 93 | Presentations |
| .png/.PNG | 82 | Images |
| .doc/.DOC | 43 | Legacy Word documents |
| .$sf / .FDB | 58 | Revit temp/database |
| .vsdx | 19 | Visio drawings |
| .txt | 18 | Text notes |
| .rvt | 15 | Revit models |
| .csv/.CSV | 3 | CSV data |
| .drawio | 11 | Draw.io diagrams |
| .xlsm | 10 | Macro-enabled spreadsheets |
| .nwc | 10 | Navisworks |
| .mpp | 6 | MS Project |
| .ifc | 8 | BIM/IFC |
| Other (.dat, .log, .tif, .edb, .lnk, .bmp, .sdr, .f2k, .ppt, .dwl2) | 34 | Miscellaneous |

### Folder Sizes (Extracted Archives)

| Folder | Size | Primary Content |
|---|---|---|
| 50 CALCULATIONS-...001 | 112 MB | NCD electrical calculations (PDF) |
| DGCL Checklists-...001 | 404 KB | Diriyah design compliance checklists (XLSX) |
| STC-...010 | 2.1 GB | NCD drawings, MSC, Nesma, Tabuk, OGF opportunities |
| STC-...001 | 2.2 GB | Major client folders: ARO, Chemanol, MSC, NCD, Tabuk, OGF |
| STC-...003 | 2.1 GB | Nesma, NCD, OGF, SME Bank |
| STC-...004 | 2.2 GB | NCD RFQ/BOQ, OGF (Sudair, DMM7, Palo Alto), Nesma |
| STC-...005 | 2.5 GB | NCD, OGF (Sabic, storage, seismic, Palo Alto) |
| STC-...006 | 2.3 GB | NCD electrical CAD, OGF (UCaaS, WAED, servers FA) |
| STC-...007 | 2.7 GB | NCD, OGF (blockchain, servers FA, RTDA) |
| STC-...008 | 2.4 GB | NCD, OGF (Aramco UC FA, digitizing DC) |
| STC-...009 | 2.4 GB | OGF (Aramco SFC, computing devices, Malafati) |
| STC-...011 | 2.3 GB | NCD, OGF (DMM7, WAED, IP Phones, xFusion servers) |
| STC-...012 | 682 MB | OGF (VSAT, Palo Alto FA, video conference) |

### Classification Summary (Automated)

| Classification | Count | % |
|---|---|---|
| drawing | 3,682 | 40.2% |
| other | 2,016 | 22.0% |
| pricing | 841 | 9.2% |
| proposal | 802 | 8.8% |
| correspondence | 707 | 7.7% |
| financial-proposal | 437 | 4.8% |
| specification | 412 | 4.5% |
| questionnaire | 100 | 1.1% |
| compliance-matrix | 58 | 0.6% |
| BoM | 58 | 0.6% |
| datasheet | 45 | 0.5% |
| template | 8 | 0.1% |

---

## Section 2 — Complete File-by-File Catalog (Pass 1 & Pass 2)

### 2.1 Root-Level Files (7 files, 125 MB)

| # | File | Size | Classification | Summary | Matrix Rows |
|---|---|---|---|---|---|
| 1 | `COMPLIANCE REVIEW REPORT NCD 20230810.docx` | 6.2 MB | compliance-matrix | NCD Car Park Diriyah — full code compliance report covering architectural, structural, electrical, mechanical, FLS compliance tables with links to stamped drawings. Covers UMA, NWC, SEC, GDCD, MOI, SIO, MOMRA authority requirements. 547 paragraphs, 8 tables. | R2, R8, R12, R16 |
| 2 | `DG-NCD-408-0000-BNH-RPT-NS-000002.docx` | 45.7 MB | specification | NCD Car Park 100% Detailed Design report — Architecture, Interior Design, Traffic Analysis, Parking Design, Fire & Life Safety, Waste Management, Vertical Transport, Security Systems, IT Systems, AV Systems, Acoustics. 2,838 paragraphs, 99 tables. | R5, R6, R8, R12, R16 |
| 3 | `DG-NCD-408-0000-BNH-RPT-NS-000002 (1).docx` | 38.8 MB | specification | Earlier revision of above with additional sections: Accessibility, Architectural Details, MEP narrative. 4,608 paragraphs, 118 tables, 151 headings. | R5, R6, R8, R12, R16 |
| 4 | `DG-NCD-408-0000-BNH-RPT-NS-000002.pdf` | 15.7 MB | specification | PDF export of the NCD detailed design report (same content as #2). | R8, R12, R16 |
| 5 | `DG-NCD-408-0000-BNH-RPT-NS-000005.pdf` | 14.2 MB | specification | NCD project report — likely MEP or structural calculation supplement. | R8, R16 |
| 6 | `DG-NCD-408-0000-BNH-PLN-BM-000002.xlsx` | 1.2 MB | specification | Master Information Delivery Plan (MIDP) for Diriyah NCD — 16 sheets covering all disciplines (Architectural, Mechanical, Electrical, Public Health, Structural, Civil, Geotechnical, VT, Acoustics, FLS, ICT-AV-Security, Interior Design, Signage). Client: Diriyah Gate Company Limited, Org: Binyah. | R8, R16 |
| 7 | `100% DD Revised Submission P3 NCD Car Park.pptx` | 6.7 MB | proposal | NCD Car Park design presentation — 100% Detailed Design submission for Phase 3. | R13 |

### 2.2 DGCL Checklists (6 files, <1 MB)

All are Diriyah Gate Company Limited (DGCL) asset design compliance checklists in .xlsx format with multi-stage review sheets (Concept Design, Schematic Design, Detailed Design).

| # | File | Classification | Summary | Matrix Rows |
|---|---|---|---|---|
| 1 | `Waste Management Asset Design Checklist.xlsx` | compliance-matrix | 5 sheets: Cover, Instructions, Concept/Schematic/Detailed Design review stages | R2, R8 |
| 2 | `Sustainability Asset Design Checklist.xlsx` | compliance-matrix | DGCL Sustainability Checklist V1.0 | R2, R8 |
| 3 | `Environment Asset Design Checklist.xlsx` | compliance-matrix | Environment Design Checklist | R2, R8 |
| 4 | `Public Realm+Landscape Asset Design Checklist.xlsx` | compliance-matrix | 4 sheets: 100% CD, 100% SD, 100% DD, Original | R2, R8 |
| 5 | `Safety&Security Asset Design Checklist.xlsx` | compliance-matrix | 3 sheets: CD, SD, DD | R2, R8 |
| 6 | `Smart Cities Asset Design Checklist.xlsx` | compliance-matrix | 5 sheets: Cover, Instructions, Concept/Schematic/Detail Design | R2, R8 |

### 2.3 NCD Project (3,831 files, 10.6 GB)

The NCD (Northern Cultural District) project is the Diriyah Smart Parking / Car Park asset. This is the largest single project area. **Only 334 non-drawing files are cataloged in detail below; 3,497 DWG files are logged in Section 3.**

**Key readable files within NCD:**

| # | File | Size | Classification | Summary | Matrix Rows |
|---|---|---|---|---|---|
| 1 | `NCD/Solutions Documents/TP/TP_OP-2023-121577_NCD_Low Current_Ver-3.5-Final.docx` | ~14 MB | proposal | Final Technical Proposal for NCD Car Park Low Current Systems (OP-2023-121577). Includes solution architecture for ICT, security, AV, parking systems. Multiple versions (V1.0 through V3.5-Final). | R8, R12, R16 |
| 2 | `NCD/Solutions Documents/BOM.docx` | ~1 MB | BoM | NCD Bill of Materials document for low current systems. | R10, R12, R16 |
| 3 | `NCD/Solutions Documents/PnL/OP-2023-121577-PLv13_24-NCD-1.0-Shahid Khan.xlsx` | ~0.5 MB | financial-proposal | Shahid's P&L workbook for NCD — P&L v13.24 template with sheets: Factors & Summary by Category, Detailed Bid Costing, Summary by Element, Levels, Type and Currencies, Suppliers, UPL Cost, CPQ. **Bilingual headers (Arabic + English).** | R10, R11, R15 |
| 4 | `NCD/Solutions Documents/PnL/OP-2023-121577-PLv13_24-NCD-2.0-Shahid Khan.xlsx` | ~0.5 MB | financial-proposal | Updated P&L version 2.0 for NCD. | R10, R11, R15 |
| 5 | `NCD/Solutions Documents/PnL/OP-2023-121577-NCD Low Current and Passive Infrastructure_Domingo-2.0.xlsx` | ~0.5 MB | financial-proposal | Alternate P&L by Domingo Ariola covering passive infrastructure. | R10, R11, R15 |
| 6 | `NCD/RFQ Document/BOQ/BOQ.xlsx` | ~1 MB | BoM | Client's BoQ template — 4 sheets: General Requirements, MAIN BOQ, Day Work BOQ, Provisional Sum BOQ. Main BOQ has REF/DESCRIPTION/QTY/UNIT/RATE/TOTAL columns. Covers substructure, MEP, fit-out. | R2, R10 |
| 7 | `NCD/RFQ Document/BOQ/P3 Carpark Add-Omit BOQ_R01.xlsx` | ~0.3 MB | BoM | Add/Omit variation BoQ for Phase 3 Car Park. | R10 |
| 8 | `NCD/Solutions Documents/Quote/Cisco/01Oct2023/BoM.xlsx` | ~0.1 MB | BoM | Cisco equipment BoM — Part Number / Description / Service Duration / Qty. Includes C9500-48Y4C-A, C9300-48U-E, C9300-DNA-A-3Y, access points, wireless controllers. | R10 |
| 9 | `NCD/Solutions Documents/Quote/Cisco/NCD (2).xlsx` | ~0.2 MB | pricing | Cisco quotation for NCD. | R10, R15 |
| 10 | `NCD/Solutions Documents/Quote/Cisco/01Oct2023/Binyah__Diriyah_Smart_Parking_Project__Updated.xlsx` | ~0.2 MB | pricing | Cisco price estimate for Diriyah Smart Parking. | R10, R15 |
| 11 | `NCD/Solutions Documents/Quote/Giza/30Aug2023/OP-2023-121577-NCD Low Current_DAriola-All-in-GIZA.xlsx` | ~0.5 MB | pricing | Giza Systems quote for NCD low current. | R10, R15 |
| 12 | `NCD/Gathering Sheet.xlsx` | ~0.1 MB | questionnaire | 3 sheets: ICT, Security, Design. Headers: S/N, Floor, IDF Zones, Rack, Fire Alarm Panel, Voice outlets. Discovery data collection. | R3, R5 |
| 13 | `NCD/NCD clarifications.xlsx` | ~0.1 MB | questionnaire | Clarification questions for NCD project. | R2, R3 |
| 14 | `NCD/parking notes.txt` | <1 KB | other | Single-line reference to drawing DG-NCD-408-0000-BNH-DWG-AR-500-0005104. | R8 |
| 15 | `NCD/Latest Documents 20Aug2023/.../COMPLIANCE REVIEW REPORT NCD 20230810.docx` | 6.2 MB | compliance-matrix | Duplicate of root-level compliance report. | R2, R8, R12 |
| 16 | `NCD/Latest Deisgn 04April2023/.../Specifications/Load Schedules/MDB-LL-01/02/03.xlsx` | ~0.3 MB ea | specification | Electrical load schedules for main distribution boards. | R8 |
| 17 | `NCD/Latest Deisgn 04April2023/.../Luminaire Schedule/ELE-SCH-XXX_Luminaire.xlsx` | ~0.1 MB | specification | Luminaire schedule for NCD. | R8 |
| 18 | `NCD/Latest Documents 20Aug2023/.../ID Specifications/DG-NCD-408-0000-BNH-SPC-ID-000003/4/5/6.xlsx` | 8-48 MB | specification | Interior design specifications (large files, detailed finish schedules). | R8 |
| 19 | `NCD/90 Response to Comments/DGCL Checklists/*.xlsx` | <1 MB ea | compliance-matrix | Same 6 DGCL checklists duplicated within NCD folder. | R2, R8 |

**NCD also contains:**
- 1,708 PDFs (engineering drawings in PDF format, datasheets, specifications)
- 44 JPG images (site photos, renderings)
- 27 PNG images
- 15 RVT files (Revit BIM models)
- 29 FDB/29 $sf files (Revit support files)
- 10 NWC files (Navisworks coordination models)
- 8 IFC files (BIM exchange format)
- Various other binary files

### 2.4 OGF - All (Opportunity Global Folder) (3,932 files, 7.1 GB, 244 opportunities)

This is the master folder containing all of Shahid's opportunity-specific project files organized by year (2019-2025) and type (Normal Opportunities, RFP, FA/Frame Agreements, POC). **This is the richest source of pre-sales workflow data.**

**Key structural patterns identified:**

1. **Tender Analyzer (TA)** workbooks — the primary financial analysis tool used by STC Solutions (STCS). Two versions found:
   - **PLv12/v13 (older):** Sheets: Factors & Summary by Category, Summary by Element, Detailed Bid Costing, Levels, Type and Currencies, Vendors/Suppliers, UPL Cost, CPQ
   - **TA 2016B V32-V35 (newer):** Sheets: Summary for Management, Guide & RACI, CHARTER, BoQ, PRESALES COSTING SUMMARY, FINANCIAL SUMMARY, Risk Calculator, CASH FLOW, STANDARD PRICING TABLE, multiple Analyse by Level/Vendor/Element sheets, Share Revenue, MIC, CAPEX MIC
   - **Bilingual (Arabic + English)** column headers throughout

2. **Technical Proposals (TP)** — standard naming: `TP_OP-YYYY-XXXXXX_Client_Scope_Ver-X.docx`. Consistently structured with executive summary, solution architecture, implementation methodology, project management sections.

3. **Quotes/Pricing** — vendor-specific price estimates from Cisco CCW, distributor quotes, and internal pricing sheets.

4. **RFP/RFI packages** — client requirement documents, compliance matrices, questionnaires.

5. **Correspondence (.msg)** — email threads with vendors (Cisco, Fortinet, Palo Alto, Dell, HPE, Cray, NVidia), distributors (Ingram Micro, Westcon), and internal teams.

**Top 15 OGF Opportunities by File Count:**

| Opportunity | Files | Client/Scope | Key Deliverables Found |
|---|---|---|---|
| OP-184121 | 353 | Aramco Smart City Systems | TP, pricing, compliance, RFP package |
| OP-010886 | 280 | Aramco Supercomputer (Cray) | TA, TP, vendor MoMs, Juniper switching |
| OP-2023-134657 | 173 | Aramco Computing Devices Lease | TP, RFP package, pricing |
| OP-2023-136618 | 126 | NVidia Supercomputer | Site surveys, pricing, TP |
| OP-2024-147007 | 123 | Aramco DMM7++ Seismic Expansion | TP (HPE + STCS), specifications |
| OP-0767 | 117 | Early MSC/MLS project | Various |
| OP-2022-103615 | 108 | Aramco VSAT Communication | TP, RFI response, Aramco forms |
| OP-167515 | 107 | Aramco UCaaS | TP (Cisco Hybrid Solution), vendor quotes |
| OP-181414 | 106 | Aramco Servers Frame Agreement | TP (89 proposal files), responsibility matrix |
| OP-2025-154381 | 101 | Saudi Aramco Storage Cluster | TP, DDN/HPE datasheets, pricing |
| OP-2021-49405 | 98 | IHPSSS | TP, specifications |
| OP-2021-55870 | 94 | Various | Financial proposals, correspondence |
| OP-2022-90896 | 87 | Aramco Digitizing DC Operations | TA, TP, correspondence |
| OP-2021-56089 | 85 | Aramco Aviation RFP | Questionnaires, TA, correspondence |
| OP-2022-80222 | 77 | Various | Proposals, correspondence |

**OGF Deliverable Type Breakdown:**
- 624 proposal documents (TP versions, vendor TPs, write-ups)
- 547 correspondence files (vendor/distributor/internal emails)
- 491 pricing files (vendor quotes, price lists, CCW estimates)
- 319 specification files (datasheets, technical specs)
- 306 financial proposal files (Tender Analyzers, P&L sheets)
- 67 questionnaire files (RFI/RFP clarification docs)
- 45 datasheet files (vendor product datasheets)
- 37 BoM files (Bills of Material/Quantities)
- 27 compliance matrix files
- 7 template files

**Key Individual Files in OGF (sampled and read):**

| File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| OP-2025-154381/.../TP_OP-2025-154381_Saudi Aramco_High Performance Storage Hardware_Ver2.0.docx | proposal | 51.6 MB Technical Proposal for Aramco High Performance Storage, DDN + HPE solution | R8, R12 |
| OP-2024-147007/.../TP_OP-2024-147007_Aracmo_DMM7 Expansion_Ver1.docx | proposal | 32 MB Technical Proposal for Aramco seismic processing compute expansion | R8, R12 |
| OP-184121/.../OP-184121-Saudi Aramco-Smart City Systems-TP-V3.0.docx | proposal | 26.8 MB Aramco Smart City integrated systems TP | R8, R12 |
| OP-010886-TA 2016 V31_03-Cray-Volta-5 Years-V1.xlsx | financial-proposal | 5 MB Tender Analyzer with 40+ sheets: management summary, bid info, RFQ, factors, authority matrix, cost UPL, proposal, cash flow, lessons learned, handover | R10, R11, R15, R16 |
| OP-185734-Solutions By STC-Statement of Compliance-MCSA EMNS.xlsx | compliance-matrix | Statement of compliance for Mass Notification service | R2 |
| Technical Evaluation Questionnaire.xlsx | questionnaire | 3 sheets: Cover, Guidance, Technical Evaluation — client technical evaluation form | R2, R3 |
| Private Cloud_Vmware_Pricing Excercise.xlsx | pricing | VMware private cloud pricing for 5-year RFP response with resource mapping | R4, R10, R15 |
| UCaaS-Vendors Scorecard-V1.xlsx | other | Vendor comparison scorecard for UCaaS solutions | R1 |
| OP-181414-Aramco Servers FA-Responsibility Matrix-v1.0.xlsx | specification | Scope requirements and responsibility assignment for servers FA | R2, R11 |
| Aramco-Almidra Project-GA-Clarifications-00.xlsx | questionnaire | Clarification questions/replies for Al Midra project | R2, R3 |
| WAF Devices Activation Contract-STCS Questions.xlsx | questionnaire | Internal questions for WAF activation contract | R2 |

### 2.5 Nesma & Partners (433 files, 1.4 GB, 10 opportunities)

Key projects: Al Shaykh Island Hotel, AVR Project (OP-2024-147554), R10 Hotel (Red Sea), Microsoft EA Renewal, New Building Infrastructure.

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| OP-2024-147554 AVR Project/PnL/OP-2024-147554-Tender Analyzer 2016B V34_18-V4 Sent.xlsx | financial-proposal | 4.5 MB Tender Analyzer V34 for AVR Project — full financial analysis with 24 sheets | R10, R11, R15 |
| Copy of Sindalah_Mainland_BOQ v3.1.xlsx | BoM | Active BoQ with Part Number, Description, Service Duration, Qty columns + SOW breakdown | R10 |
| compliance sheet.xlsx | compliance-matrix | Comply / Not Comply columns with notes | R2 |
| RAP-COMPLIANCE-V1.3 Filled-MyTel.xlsx | compliance-matrix | Filled RAP compliance sheet | R2 |
| OP-2021-33682-PLv13_11-CCTV-1.0-Shahid Khan.xlsx | financial-proposal | P&L for CCTV project — bilingual | R10, R11, R15 |
| SPARK_Dry_Port__NESMA__36_Months_.xlsx | pricing | Cisco service estimate for 36 months | R4, R10 |
| OP-111879 PLv12_4-IPTV-1.0-Shahid Khan.xlsx | pricing | IPTV pricing — PL v12.4 format | R10, R15 |
| Ummahat Alshaykh Hotel H11 Nodes.xlsx | pricing | Hotel ICT and CCTV+AC node pricing with quantities per room type | R10, R15 |
| 182 .dwg files (538 MB) | drawing | Hotel infrastructure AutoCAD drawings | R8 |

### 2.6 Tabuk Emara (247 files, 205 MB)

Security, network, wireless, and HCS project for Tabuk Emirate.

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| TabukEmarah_Fortinet_Technical_Proposal_v2.docx | proposal | 15.6 MB Fortinet security TP for Tabuk Emirate — multi-vendor | R8, R12 |
| D-2017-16984-PLv12_4-HCS-2.5-Shahid Khan.xlsx | pricing | P&L v12.4 — HCS pricing with 7 sheets: Factors & Summary, Element Summary, Detailed Bid Costing, Levels, Vendors, UPL Cost | R10, R11, R15 |
| emarat tabok DB-2017-16984-PLv1-Security enhancement-Sarah Alkadhi P&L.xlsx | financial-proposal | Security enhancement P&L by Sarah AlKadhi | R10, R11, R15 |
| Copy of D-2017-16984-PLv11_5-Network and WI-FI-V1.1-Nashaat Badr.xlsx | pricing | Network and WiFi pricing | R10, R15 |
| Copy of 04 Pricing v427 Cloud Collaboration Services.xlsm | pricing | Cloud collaboration pricing with TCO, bandwidth calc, sales tab | R10, R15 |
| Information Gathering.txt | questionnaire | Discovery notes: 500 users, MPLS, Cisco ASA, Symantec endpoint, DR requirements | R3, R5 |
| 30+ .msg files | correspondence | Emails with Ingram Micro, STC teams re: security solutions, TrendMicro, FireEye | R9 |
| 9 .vsdx files | drawing | Visio network diagrams | R8 |
| 10 .log files | other | Syslog/audit logs | R6 |

### 2.7 MSC (73 files, 67 MB, 10 opportunities)

Mohammed Salem Al Cathami (MSC) project area covering HCS, Fortinet Security, access points, routers.

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| OP-237876 Fortinet Security (multiple files) | proposal/pricing | Fortinet managed security services proposal and pricing | R8, R10, R12 |
| OP-076686-PLv12_4-MLS,MSS,Shabik-1.0/2.0/3.0-Shahid Khan.xlsx | financial-proposal | Three versions of P&L for MLS/MSS/Shabik | R10, R11, R15 |
| OP-098027 HCS, OP-167764 HCS Updated, OP-2021-56010-HCS-New | pricing/BoM | HCS (Hosted Collaboration Solution) iterations | R10 |
| OP-2022-103336 Access points (Meraki) | pricing | Meraki access point pricing with distributor quotes | R10 |
| 5 .pptx presentations | proposal | Customer-facing presentations | R13 |
| 4 .vsdx Visio diagrams | drawing | Network topology diagrams | R8 |

### 2.8 ARO (64 files, 158 MB, 6 opportunities)

ARO Drilling — barcode, meeting rooms, corporate network, SmartNet renewals.

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| TP_OP-2024-146637_ARO_Barcode_Ver-2.docx | proposal | 15.2 MB Barcode scanning solution TP | R8, R12 |
| OP-2024-149062/.../TP_OP-2024-149062_ARO_Meeting Room_Ver-1.docx | proposal | Meeting room solution TP | R8, R12 |
| BoQ Aro Drilling NET&ERP Price.xlsx | BoM | ARO Drilling Microsoft Enterprise Agreement BoQ | R10 |
| OP-2024-146637-Tender Analyzer 2016B V34_03-(v2.0).xlsx | financial-proposal | Full Tender Analyzer V34 with 24 sheets including BoQ, financial summary, cash flow, risk calculator | R10, R11, R15 |
| OP-2024-150797-Tender Analyzer 2016B V34_18-Sent-12/36 Months.xlsx | financial-proposal | SmartNet renewal TA — 12 and 36 month options | R10, R15 |
| Clarification Form RFP Corporate Network Service.xlsx | questionnaire | RFP clarification form | R2, R3 |
| CISCO Network Hardware and services Pricing List.xlsx | pricing | Cisco pricing reference | R4, R10 |
| Smartnet-36 Months.xlsx | pricing | SmartNet renewal pricing | R10 |

### 2.9 Chemanol (10 files, 5 MB, 1 opportunity)

Chemanol IP Telephony / HCS project (OP-2022-90572).

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| OP-2022-90572-HCS-Technical_Proposal-Shahid-V1.docx | proposal | Chemanol HCS technical proposal | R8, R12 |
| OP-2022-90572-PLv13_16-HCS-1.0-Shahid Khan.xlsx | financial-proposal | P&L v13.16 — bilingual | R10, R11, R15 |
| ECB-STC OLD NEW-Solutions.xlsx | other | STC old vs new solutions comparison | R6 |
| 3 .msg emails | correspondence | Customer emails re: IP telephony | R9 |

### 2.10 Sudair (29 files, 121 MB, 1 opportunity)

Sudair industrial city forecasting project (OP-2024-149107).

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| TP_OP-2024-149107_Sudair_Forcasting_Ver-V1.docx | proposal | 51.9 MB Sudair forecasting TP | R8, R12 |
| ACWA proposal shared files/General technical description.docx | proposal | 42 MB ACWA Power technical description | R8 |
| .drawio files (x2) | drawing | Network diagrams in draw.io format | R8 |
| .png files (x3) | other | Architecture/topology diagrams | R8 |

### 2.11 Sabic (106 files, 118 MB, 1 opportunity)

SABIC EoL Servers replacement project (OP-2024-150965).

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| TP_OP-2024-150965_SABIC_EoL Servers_Ver-2.docx | proposal | 16.3 MB SABIC server replacement TP | R8, R12 |
| Multiple vendor quotes and specifications | pricing/specification | Server specifications, pricing from various vendors | R4, R10 |

### 2.12 SME Bank (100 files, 149 MB, 7 opportunities)

SME Bank (Monsha'at) — Microsoft, data center, cloud migration projects.

| Key File | Classification | Summary | Matrix Rows |
|---|---|---|---|
| Multiple TP documents | proposal | Cloud migration, data center, IT infrastructure TPs | R8, R12 |
| P&L and pricing sheets | financial-proposal/pricing | Multiple financial analysis workbooks | R10, R11, R15 |
| 25 .msg emails | correspondence | Internal/external coordination | R9 |
| bittitan.txt | pricing | BitTitan pricing URL reference for cloud migration | R10 |

### 2.13 Other Client Projects (Remaining 30 project areas, ~380 files)

| Project | Files | Key Content | Matrix Rows |
|---|---|---|---|
| Rizayat | 46 | Multi-version proposals and pricing | R10, R12, R15 |
| NesmaKent | 29 | IT Infrastructure BoQ (Infrastructure+CyberSecurity BOM sheets), P&L, correspondence | R10, R11, R15 |
| RMS | 25 | Proposals, pricing, Visio diagrams | R8, R10, R12 |
| STC Kuwait | 24 | Compliance matrices, BoQ, proposals | R2, R10, R12 |
| SE | 19 | PDFs, specifications | R8 |
| Osool | 17 | SD-WAN TP, compliance matrices, questionnaires | R2, R3, R8, R12 |
| Red Sea Gateway Terminal | 16 | P&L workbooks, correspondence | R10, R11, R15 |
| National Marine | 13 | CUCM P&L (4 versions by Shahid), correspondence | R10, R11, R15 |
| Saudi Electricity | 11 | PDFs, specifications | R8 |
| ARASCO | 10 | Fortinet firewall P&L, correspondence | R10, R15 |
| Sharbiny | 10 | Pricing sheets, proposals | R10, R12 |
| Deqat | 9 | Proposals, P&L workbooks | R10, R12, R15 |
| GASCO | 9 | SD-WAN TP, P&L (Shahid), Fortinet correspondence | R8, R10, R12, R15 |
| Riyadh Food Industries | 9 | Pricing sheets | R10, R15 |
| QNB | 8 | Word docs and PDFs | R12 |
| Kadana | 6 | Passive infrastructure P&L (Shahid), correspondence | R10, R11, R15 |
| Extra | 3 | Pen testing proposal and pricing | R12 |
| Hadeed | 6 | Tender Analyzer V35, proposals | R10, R11, R12, R15 |
| Dehwali Optical | 7 | Avaya Call Center P&L (Shahid), Cisco pricing | R10, R15 |
| AFCO compound | 3 | DSLAM pricing | R10 |
| AMLAK | 3 | Tender Analyzer V35 (two versions) | R10, R15 |
| Abdulrahman Al Mousa | 6 | Co-Location pricing (3 versions, Shahid) | R10, R15 |
| Mawred Albaraka | 3 | Fortinet pricing (Shahid) | R10 |
| Rabigh | 4 | IPT pricing | R10 |
| Riyadh Int'l Catering | 6 | Specifications and pricing | R10 |
| Roshn | 6 | P&L, pricing, correspondence | R10, R15 |
| SEDCO | 4 | Pricing | R10 |
| Thiqah | 6 | Pricing, correspondence | R10 |
| Quality Control Services | 7 | Pricing | R10 |

### 2.14 Text Files (18 files — All Read)

| # | File | Classification | Summary | Matrix Rows |
|---|---|---|---|---|
| 1 | Notes for VSAT Terminal PA development.txt | other | Vendor requirements for 5-year VSAT PA: BOM, datasheets, compliance statements, system diagrams, warranty, factory test | R2, R10 |
| 2 | BB notes and auumptions.txt | other | MCSA Emergency Mass Notification sizing: 95K licenses, ~1.64M SMS/yr, exclusions | R3, R5, R11 |
| 3 | Information Gathering.txt | questionnaire | Tabuk Emara discovery: 500 users, MPLS, Cisco ASA, Symantec, DR needs | R3, R5, R6 |
| 4 | Material RFQ/Notes.txt | other | Seismic HPC submission checklist: TP template, compliance sheet, spare parts list | R2 |
| 5 | POC/details.txt | other | CWDM/REP ring POC criteria: convergence, performance, 80km distance/attenuation | R7 |
| 6 | SITE1-SW1#sh running-config.txt | specification | Cisco switch config: 10GigE REP, 8 GigE VLAN 10 access ports | R6, R7 |
| 7 | SITE3-SW1#sh running-config.txt | specification | Cisco switch config: mid-ring REP node, VLAN 10 SVI | R6, R7 |
| 8 | Aramco Servers FA/Notes.txt | other | Clarification questions: rack pricing, responsibility matrix, cabling, SCOM | R2, R3 |
| 9 | SITE1#sh rep topology.txt | other | REP topology verification: 3-node ring confirmed operational | R7 |
| 10 | Dell MoM.txt | correspondence | Dell meeting: Compellent/Unity vs Huawei storage comparison, encryption compliance | R9 |
| 11 | cray question and MoM.txt | correspondence | Cray Supercomputer: 99.67% SLA vs Tier 1 DC, security hardening responsibility | R9 |
| 12 | OP-167881-Notes.txt | questionnaire | Sutherland pre-sales questions: VM bandwidth, licensing, storage IOPS, DNS sizing | R3, R4 |
| 13 | Juniper switches.txt | correspondence | Aramco Supercomputer networking: Juniper QFX preference, L3/BGP + L2 requirements | R9 |
| 14 | Project Notes.txt | other | Aramco disk storage: data migration is customer-owned, tools/licenses must be bid | R2 |
| 15 | Notes - HPE.txt | other | Nesma AVR vendor shortlist: Mytel IPT, Fortinet security, Infoblox, Pandox | R9 |
| 16 | Seismic HPC/Notes.txt | other | Scope note: I&C services + decommission services | R11 |
| 17 | parking notes.txt | other | Drawing reference: DG-NCD-408-0000-BNH-DWG-AR-500-0005104 | R8 |
| 18 | bittitan.txt | pricing | BitTitan pricing URL for cloud migration tool | R10 |

### 2.15 Email Correspondence (.msg files — 100 sampled, 707 total)

Emails span 2017-2024 and cover:

**Vendor communications:** Cisco, Fortinet, Palo Alto, Dell, HPE, Cray, NVidia, xFusion, PNY, Cobham (VSAT), Hughes
**Distributor communications:** Ingram Micro, Westcon, Exclusive Networks, StarLink, Horizon Informatics
**Internal teams:** STCS pre-sales (Shahid Khan, Amr Elessawy, Domingo Ariola, Mohamed Aldessoki), sales (Sarah AlKadhi, Yasser Bassune, Satam Almutairi), management
**Clients:** Aramco, MSC, Chemanol, GASCO, Nesma, Tabuk Emara, ARO

**Topics covered:** RFQ submissions, vendor pricing requests, BoM clarifications, project kick-offs, technical discussions, distributor negotiations. All map to R9 (Vendor Engagement) and R1 (Qualification/coordination).

---

## Section 3 — Large Files and Drawings (Logged Only)

### 3.1 DWG Files (1,940 files, ~2.4 GB)

| Project | Count | Size | Likely Content |
|---|---|---|---|
| NCD | 1,882 | ~2.4 GB | NCD Car Park detailed design drawings: Electrical (fire alarm, lighting, power, ELV), Mechanical (HVAC, plumbing), Architectural, Structural, Civil, ICT, Security — both CAD source and exported formats |
| Nesma & Partners | 58 | 538 MB | Hotel infrastructure drawings (Sindalah/Ummahat Alshaykh, AVR Project) |

All DWG files follow the Diriyah naming convention: `DG-NCD-408-0000-BNH-DWG-{discipline}-{level}-{number}` where discipline = AR (architectural), EL (electrical), ME (mechanical), PH (public health), ST (structural), CI (civil).

### 3.2 Large PDFs (>10 MB, 47 files)

| File | Size | Project | Likely Classification |
|---|---|---|---|
| R10-H12D03-AKT-RPT-IC-0004.pdf | 147 MB | Nesma & Partners | ICT report for Red Sea hotel |
| DG-NCD-408-0000-BNH-CAL-EL-000001.pdf | 97 MB | NCD | Electrical calculations (also in 50 CALCULATIONS folder) |
| DG-NCD-408-0000-DYG-RPT-ID-000003.pdf | 88 MB | NCD | Interior design report |
| Structural Calculations Report.pdf | 79 MB | NCD | Structural engineering calculations |
| Accenture Smart City Technical Proposal.pdf | 75 MB | OGF - All | Competitor/reference TP for Aramco Smart City |
| NCD-Car Park Structural Basis of Design.pdf | 61 MB | NCD | Structural design basis document |
| server_manual_e_G262-ZO0_A00.pdf | 33 MB | OGF - All | Server hardware manual (datasheet) |
| DG-NCD-408-0000-BNH-SCH-ID-000007.pdf | 33 MB | NCD | Interior design schedule |
| NCD-P3 Electrical Calculations.pdf | 31 MB | NCD | Electrical calculations |
| R10-H12D03-AKT-RPT-IC-0003.pdf | 27 MB | Nesma & Partners | ICT report |
| ARAMCO.pdf / Safety Program.pdf (x2) | 24 MB | OGF - All | Aramco safety documentation |
| DG-NCD-408-0000-BNH-SCH-ID-000002.pdf | 23 MB | NCD | Interior design schedule |
| NCD Car Park-Datasheets-FAS-01.pdf (x2) | 21 MB | NCD | Fire alarm system datasheets |
| DG-NCD-408-0000-BNH-DWG-AR-700-005006.pdf | 22 MB | NCD | Architectural drawing (PDF export) |
| Remaining 32 files | 10-21 MB | Mixed | Various engineering drawings, specifications, reports |

### 3.3 RAR Archives (140 files)

132 RAR files are within OGF - All opportunities (likely containing additional documents that were not extracted). Notable locations:
- OP-2022-103615 VSAT (Aramco forms)
- Various Aramco FA/RFP packages
- Vendor documentation bundles

---

## Section 4 — Skipped Files (Cannot Read)

| File Type | Count | Reason |
|---|---|---|
| .rar | 140 | Compressed archives — not extracted (may contain additional documents) |
| .jpg/.jpeg/.JPG | 119 | Images — site photos, screenshots, renderings |
| .pptx (>20 MB) | ~10 | Large PowerPoint presentations — binary, not parsed |
| .png/.PNG | 82 | Images — diagrams, screenshots |
| .$sf / .FDB | 58 | Revit temp/database files — not parseable |
| .vsdx | 19 | Visio diagrams — binary format |
| .rvt | 15 | Revit BIM model files — binary |
| .dat | 11 | Data files — unknown format |
| .nwc | 10 | Navisworks coordination files — binary |
| .log | 10 | Log files (mainly Tabuk Emara syslog captures) |
| .ifc | 8 | BIM/IFC exchange files — binary |
| .mpp | 6 | MS Project schedules — binary |
| .drawio | 11 | Draw.io XML diagrams — partially readable but not prioritized |
| .tif | 3 | TIFF images |
| .edb | 3 | Exchange database files |
| .lnk | 2 | Windows shortcut files |
| .bmp/.sdr/.f2k/.dwl2/.ppt | 5 | Miscellaneous binary |
| **Total** | **512** | |

---

## Section 5 — Gap Analysis per Capability Matrix Row

### Row 1: Lead/Opportunity Qualification (Gate 1 — Facilitate)

**Needs:** Intake form, scoring template (BANT/MEDDPICC), project type classifier, industry/headcount/sites data.
**Covered:** Partial — opportunity codes (OP-xxxxx) and folder structure imply qualification happened. Some discovery notes (Tabuk Emara Info Gathering, Sutherland Notes) show informal qualification data.
**Missing:**
- No formal qualification memos or intake forms found
- No BANT/MEDDPICC scoring templates
- No CRM exports or opportunity records
- No standardized project type classification
**Status: PARTIALLY COVERED** — informal data exists but no structured qualification artifacts.

### Row 2: RFP Package Parser + Compliance Matrix (Gate 2 — SWEET SPOT #1)

**Needs:** RFP ingestion engine, compliance framework DB, complete RFP packages, compliance matrices.
**Covered:** Strong —
- 6 DGCL compliance checklists (structured, multi-stage review)
- NCD COMPLIANCE REVIEW REPORT (full code compliance with 8 tables)
- RAP-COMPLIANCE-V1.3 (Nesma)
- Statement of Compliance for MCSA (OGF)
- Osool Requirements Compliance Matrix
- STC Kuwait compliance matrices (6 files)
- 100+ RFP/questionnaire files across OGF opportunities
- NCD BOQ shows client's structured template format
**Missing:**
- Complete end-to-end RFP packages with all 16+ files intact (most are split across folders)
- NCA ECC-2 2024 control list (compliance framework DB)
- ISO 27001:2022 Annex A controls
- Standardized compliance matrix template
**Status: PARTIALLY COVERED** — compliance examples exist, but no complete "before and after" RFP-to-compliance workflow sample.

### Row 3: RFI Questionnaire Generator (Gate 2 — SWEET SPOT #4)

**Needs:** Questionnaire generator per project type, Playbook §2.4 template, previous questionnaires.
**Covered:** Partial —
- Tabuk Emara Information Gathering.txt — real discovery notes (500 users, current-state details)
- NCD Gathering Sheet.xlsx — structured ICT/Security/Design discovery form
- NCD clarifications.xlsx — project clarifications
- Clarification Form RFP Corporate Network Service (ARO)
- Sutherland OP-167881 Notes — pre-sales scoping questions
- BB notes and assumptions (MCSA sizing)
**Missing:**
- No Playbook §2.4 Section A-F questionnaire templates in executable form
- No standardized discovery questionnaire documents
- No completed RFI response examples
**Status: PARTIALLY COVERED** — informal discovery artifacts exist but no structured questionnaire templates.

### Row 4: RFQ Pricing Response (Gate 2 — Semi-automate)

**Needs:** Item list parser, vendor catalog DB, pricing engine, FX rates, VAT.
**Covered:** Strong —
- 841 pricing files across all projects
- Cisco CCW estimates and price lists
- Distributor quotes from Ingram Micro, Westcon, Exclusive Networks
- VMware pricing exercises
- Fortinet pricing (from Shahid's existing data)
- SmartNet renewal pricing
**Missing:**
- No structured vendor catalog database
- No FX rate management
- No VAT calculation templates
**Status: PARTIALLY COVERED** — extensive pricing samples but no automated pricing engine infrastructure.

### Row 5: Technical Discovery & Site Surveys (Gate 2 — Facilitate)

**Needs:** Site survey checklist, current-state assessment templates, meeting notes.
**Covered:** Partial —
- Tabuk Emara Information Gathering (field notes with site details)
- NVidia DGX H100 Pre-delivery Site Survey (5 MB, OGF)
- BB notes and assumptions (sizing for MCSA)
- NCD Detailed Design Report (includes traffic analysis, parking design, site conditions)
**Missing:**
- No standardized site survey checklist templates
- No current-state assessment templates
- Very few site survey reports
**Status: MINIMALLY COVERED** — a few examples exist but no systematic discovery tooling.

### Row 6: Existing Network Assessment (Gate 2 — Semi-automate)

**Needs:** Config file parser, inventory parser, network data exports.
**Covered:** Minimal —
- SITE1-SW1 and SITE3-SW1 running configs (Cisco switch configs from CWDM POC)
- SITE1 REP topology output
- Tabuk Emara syslog captures (10 .log files)
- Chemanol ECB old/new solutions comparison
**Missing:**
- No Lansweeper/DNA Center/Auvik exports
- No SNMP/inventory dumps
- No NetFlow/sFlow data
- No systematic config collection
**Status: MINIMALLY COVERED** — only a few isolated config captures.

### Row 7: Technical Demos, Workshops, PoCs (Gate 2-3 — Cannot Automate)

**Needs:** Human-driven activities.
**Covered:** Some evidence —
- CWDM/REP POC files (details.txt, switch configs, topology verification)
- Various meeting notes referencing demos and workshops
**Status: N/A (CANNOT AUTOMATE)** — evidence exists that PoCs were conducted.

### Row 8: Design + HLD/LLD Authorship (Gate 3 — SWEET SPOT #5)

**Needs:** Design methodology selector, HLD/LLD templates, diagrams, vendor reference architectures.
**Covered:** Strong —
- NCD Detailed Design Report (2,838+ paragraphs, 99+ tables — comprehensive reference)
- 802 proposal documents (many contain HLD sections)
- 11 .drawio files (programmatically-accessible diagram format)
- 19 .vsdx Visio diagrams
- 1,940 DWG AutoCAD drawings (NCD + Nesma)
- NCD MIDP (16-sheet master information delivery plan)
- Tabuk Emara Fortinet TP with security architecture
- Multiple Aramco TPs with solution architectures
**Missing:**
- No standalone HLD or LLD template documents
- No IP/VLAN planning spreadsheets
- No sizing calculator templates
- No PPDIOO methodology reference documents
**Status: WELL COVERED** — extensive design output exists as reference material, but no standalone reusable templates.

### Row 9: Vendor Engagement (Gate 4 — Cannot Automate)

**Needs:** Human-driven vendor communications.
**Covered:** Extensive —
- 707 correspondence files (MSG emails with Cisco, Fortinet, Palo Alto, Dell, HPE, Cray, NVidia, distributors)
- Dell MoM (storage comparison meeting)
- Cray MoM (SLA and security discussions)
- Juniper switches meeting notes
- HPE notes for Nesma AVR
**Status: N/A (CANNOT AUTOMATE)** — rich correspondence corpus showing vendor engagement patterns.

### Row 10: BoM Construction — Dual Mode (Gate 4 — SWEET SPOT #2)

**Needs:** Client BoQ parser, SKU lookup, vendor catalog, quantities from design, pricing.
**Covered:** Very Strong —
- 58 BoM files + 841 pricing files + 437 financial proposal files
- NCD BOQ.xlsx — complete client BoQ template (General Requirements, MAIN BOQ, Day Work, Provisional Sum)
- NCD Cisco BoM — Part Number / Description / Service Duration / Qty with real Cisco SKUs
- Sindalah Mainland BOQ v3.1 — Active BoQ + SOW breakdown
- NesmaKent IT Infrastructure BOQ — Infrastructure + CyberSecurity BOM sheets
- ARO Barcode BoQ — within Tender Analyzer (bilingual headers, vendor/supplier columns)
- Tender Analyzer BoQ sheet structure: Item#, Category, Vendor, Supplier, Element, Part Number, Description, Unit, Qty, pricing columns
- Hundreds of P&L workbooks showing how BoMs feed into financial analysis
**Missing:**
- No structured vendor catalog database
- No automated SKU lookup capability
- No cable/patch calculator
- No accessory selector (PSU, fans, rails)
**Status: WELL COVERED** — extensive real BoM examples in both client template (RFP mode) and generated-from-scratch (RFI mode) formats.

### Row 11: Professional Services Scoping (Gate 4 — Semi-automate)

**Needs:** Role-day estimation, day-rate card, past services estimates, travel policy.
**Covered:** Partial —
- Tender Analyzer workbooks contain PRESALES COSTING SUMMARY and FINANCIAL SUMMARY sheets
- Some TPs include implementation methodology with phased timelines
- Older P&L templates have "Detailed Bid Costing" sheets with service line items
- BB notes show services sizing (MCSA - 95K licenses)
- Seismic HPC notes mention I&C and decommission services scope
**Missing:**
- No standalone day-rate card by country/role
- No standardized role-day estimation templates
- No travel/per-diem reference data
- No services SoW templates
**Status: PARTIALLY COVERED** — services costs are embedded in TAs but no standalone templates.

### Row 12: Proposal Authorship / Technical Proposal (Gate 5 — SWEET SPOT #3)

**Needs:** All Gate 2-4 artifacts, NTT TP template, company profile, past proposals.
**Covered:** Very Strong —
- 802 proposal documents across all projects
- Consistent TP naming: `TP_OP-YYYY-XXXXXX_Client_Scope_Ver-X.docx`
- Multiple complete TPs with standard sections: executive summary, solution architecture, implementation methodology, project management
- Full version histories (V1.0 through V3.5 for NCD, V1 through V3 for WAED)
- Multi-vendor TPs (Cisco, Fortinet, Palo Alto, Dell, HPE, DDN, NVidia, Cray)
- Vendor-provided TPs (Cloudera, DDN, HPE, OpenText, ZINAD)
- Government RFP TPs (Aramco — with strict formatting)
- 93 PowerPoint presentations
**Missing:**
- No NTT standard TP template (this is from Phase 1)
- No company profile document
- No standardized proposal template extracted separately
**Status: WELL COVERED** — rich corpus of real proposals for training and reference.

### Row 13: Customer Presentations (Gate 5 — Facilitate)

**Needs:** Slide deck generator, executive deck template.
**Covered:** Partial —
- 93 .pptx files across projects
- NCD 100% DD Revised Submission (design presentation)
- MSC presentations (5 files)
**Missing:**
- No standardized executive deck template
- No financial deck template
- No competitive positioning templates
**Status: PARTIALLY COVERED** — presentation examples exist but no templates.

### Row 14: Internal Collaboration (Gate 5 — Cannot Automate)

**Needs:** Human-driven collaboration.
**Covered:** Evidence in correspondence showing internal coordination between pre-sales, sales, and delivery.
**Status: N/A (CANNOT AUTOMATE)**

### Row 15: Margin Review & Deal Approval (Gate 5 — Semi-automate)

**Needs:** Cost stack calculator, margin policy, approval matrix, vendor SPF forms.
**Covered:** Strong —
- 437 financial proposal files (Tender Analyzers with full cost stacks)
- Tender Analyzer V34/V35 includes: Summary for Management, Financial Summary, Risk Calculator, Cash Flow, Standard Pricing Table, Share Revenue analysis, CAPEX MIC
- Older P&L templates (V12/V13) include: Factors & Summary, Detailed Bid Costing, UPL Cost, CPQ
- Both templates show: List Price, Discount, B2B Sale, STCS Sale, margins by category
- Categories tracked: Cloud & DC, Communication & Internet, Cyber Security, Digital Services, Digital Transformation, Managed Services, System Integration, Outsourcing
**Missing:**
- No company margin policy document
- No approval authority matrix (referenced in older TA as "AuthorityMatrix" sheet but not populated in samples)
- No vendor SPF forms
**Status: WELL COVERED** — the Tender Analyzer IS the cost stack calculator and margin review tool.

### Row 16: Handover-to-Delivery (Gate 6 — Facilitate)

**Needs:** Artifact compiler, handover checklist, document packager.
**Covered:** Partial —
- Older Tender Analyzer has "Handover" sheet (seen in OP-010886 Cray TA)
- Complete project folders show artifact organization (TP, BoM, P&L, quotes, drawings, specs in structured folders)
- NCD project has the most complete artifact set across all 6 gates
**Missing:**
- No standalone handover checklist template
- No formal deal handover memo example
- No artifact compilation automation
**Status: MINIMALLY COVERED** — artifacts exist but no formal handover documentation.

---

## Section 6 — Summary Table: Build Readiness by Gate/Row

| Row | Gate | Responsibility | Sweet Spot | Data Status | Build Readiness |
|---|---|---|---|---|---|
| 1 | 1 | Qualification | — | PARTIAL | NEEDS MORE DATA — no qualification templates found |
| **2** | **2** | **RFP Parser + Compliance** | **#1** | **PARTIAL** | **CAN START — compliance examples exist; need complete RFP packages + NCA/ISO frameworks** |
| **3** | **2** | **RFI Questionnaire** | **#4** | **PARTIAL** | **CAN START — discovery examples exist; need Playbook §2.4 template digitized** |
| 4 | 2 | RFQ Pricing | — | PARTIAL | CAN START — extensive pricing samples; need vendor catalog DB |
| 5 | 2 | Discovery & Site Surveys | — | MINIMAL | NEEDS MORE DATA — few site survey examples |
| 6 | 2 | Network Assessment | — | MINIMAL | NEEDS MORE DATA — almost no config/inventory data |
| 7 | 2-3 | Demos/PoCs | — | N/A | CANNOT AUTOMATE |
| **8** | **3** | **Design + HLD/LLD** | **#5** | **STRONG** | **CAN BUILD — rich design corpus, draw.io files, architecture references** |
| 9 | 4 | Vendor Engagement | — | N/A | CANNOT AUTOMATE |
| **10** | **4** | **BoM Construction** | **#2** | **STRONG** | **CAN BUILD — extensive BoM/BoQ examples in both modes, Tender Analyzer BoQ structure** |
| 11 | 4 | Services Scoping | — | PARTIAL | CAN START — embedded in TAs but no standalone templates |
| **12** | **5** | **Proposal Authorship** | **#3** | **STRONG** | **CAN BUILD — 800+ real proposals, consistent structure, multi-vendor** |
| 13 | 5 | Presentations | — | PARTIAL | NEEDS TEMPLATE — examples exist but no standard template |
| 14 | 5 | Internal Collaboration | — | N/A | CANNOT AUTOMATE |
| 15 | 5 | Margin Review | — | STRONG | CAN BUILD — Tender Analyzer IS the tool; well-understood structure |
| 16 | 6 | Handover | — | MINIMAL | NEEDS MORE DATA — no formal handover docs |

### Summary Counts

| Readiness | Count | Rows |
|---|---|---|
| **CAN BUILD now** | 5 | R8 (Design), R10 (BoM), R12 (Proposal), R15 (Margin) + R4 (RFQ Pricing partial) |
| **CAN START** (partial data) | 4 | R2 (RFP Parser), R3 (RFI Questionnaire), R4 (RFQ), R11 (Services) |
| **NEEDS MORE DATA** | 4 | R1 (Qualification), R5 (Discovery), R6 (Assessment), R16 (Handover) |
| **NEEDS TEMPLATE** | 1 | R13 (Presentations) |
| **CANNOT AUTOMATE** | 3 | R7 (PoCs), R9 (Vendor), R14 (Collaboration) |

---

## Section 7 — Recommendations

### What Shahid Still Needs to Provide

1. **Complete RFP packages (HIGH PRIORITY)** — 2-3 end-to-end packages showing all 16+ input files AND the output (compliance matrix, BoM, TP). Ideally one government (Aramco/Diriyah) and one private sector. The NCD project comes closest but the RFP input files are scattered.

2. **Palo Alto price list** — confirmed he can get this (per Planning Handoff doc). Needed for multi-vendor BoM automation.

3. **Qualification templates** — any BANT/MEDDPICC scoring sheets, opportunity intake forms, or CRM export examples.

4. **Site survey checklists** — standardized forms used for on-site discovery visits.

5. **Handover documentation** — a formal deal handover memo or kick-off pack from a completed deal.

6. **Services rate card** — day rates by role and country, travel/per-diem tables.

7. **Company profile document** — standard STCS company profile used in proposals.

8. **Presentation templates** — standard executive, technical, and financial deck templates.

### What Can Be Sourced Publicly

1. **NCA ECC-2 2024 controls** — available from the National Cybersecurity Authority website (partially public).

2. **ISO 27001:2022 Annex A controls** — open-source control mappings available from multiple security frameworks (NIST CSF mapping, OSCAL).

3. **Vendor reference architectures** — Cisco CVDs (Validated Designs), Fortinet reference architectures, Palo Alto best practice guides — all available through partner portals.

4. **PPDIOO methodology** — Cisco's Plan-Prepare-Design-Implement-Operate-Optimize is publicly documented.

### What Needs to Be Built

1. **Vendor catalog database** — structured DB from existing price list files (Cisco, Fortinet, Palo Alto). The raw data exists in the knowledge base and Shahid's uploads.

2. **Tender Analyzer parser** — the TA workbook is the spine of the financial workflow. Both V13 (7 sheets) and V34/V35 (24 sheets) formats need reverse-engineering into a data model.

3. **TP template extractor** — analyze the ~800 existing TPs to extract the standard section structure and build a reusable template engine.

4. **Compliance framework DB** — map NCA ECC-2, ISO 27001, SAMA CSF controls into a queryable structure for compliance matrix generation.

5. **Discovery questionnaire engine** — digitize Playbook §2.4 Sections A-F into a dynamic questionnaire that adapts per project type (cybersecurity, network, collaboration) and vertical (government, energy, banking, hospitality).

6. **BoQ template parser** — build a parser that understands client BoQ Excel formats (the NCD BOQ and Tender Analyzer BoQ sheet provide two concrete examples with known column structures).

### Key Insight: The Tender Analyzer is Ground Truth

The Tender Analyzer workbook (found in both older PLv12/v13 and newer TA 2016B V32-V35 formats) is the single most important data structure in this knowledge base. It contains:
- BoQ (Bill of Quantities) with bilingual headers
- Presales costing summary
- Financial summary with margins
- Cash flow projections
- Standard pricing tables
- Multi-dimensional analysis (by level, vendor, element, supplier)
- Management summary
- Risk calculator (V35+)
- Share revenue analysis

**There are 437+ Tender Analyzer instances across this data set.** Reverse-engineering this workbook into a data model should be the first technical priority for Sweet Spots #2 (BoM) and #5 (Margin Review).

---

*End of STC Data Inventory. Generated by automated cataloging of 9,166 files across 42 project areas.*
