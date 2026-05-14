# BOMatic — Shahid Ground Truth Reference

**Source:** Shahid Khan's real work artifacts from NTT DATA / Dimension Data Saudi Arabia. These are the actual outputs our product needs to match and the actual workflow it needs to automate.

---

## 1. Presales engineer daily workflow (Shahid's checklist)

This is the 10-step workflow our product automates. Steps 1–4 are Phase 1 scope. Steps 5–7 are Phase 2–3.

| Step | Task | SLA | Our product coverage |
|---|---|---|---|
| 1 | Receive request (email from sales) | — | Phase 2: email intake monitoring |
| 2 | Update tracking sheet (opportunity name, customer, technology, date, status) | — | Phase 1: intake record in database |
| 3 | Check requirement clarity → if unclear, request clarification | — | Phase 1: agent flags "insufficient information" |
| 4 | Build estimate in CCW (select SKUs, licenses, support, check EoL, validate quantities, apply standard config) | 48hr (Cisco), 5-day (non-Cisco) | Phase 1: core agent workflow |
| 5 | Create Cisco Deal ID + apply discounts | — | Phase 3: deal registration |
| 6 | Create DD-Direct quote → match CCW estimate 100% → fix mismatches | — | Phase 3: distributor reconciliation |
| 7 | Share quote with account manager (attach CCW estimate or distributor quote) | — | Phase 2: send-to-customer |
| 8 | Update tracking sheet (quote ref, status, submission date, comments) | — | Phase 1: audit log + status tracking |

| 9 | Follow-ups (pending clarifications, distributor responses, tracking sheet) | — | Phase 3: dashboard + notifications |

**Key insight:** Step 6 is the "stare and compare" step — matching CCW estimate with DD-Direct distributor quote 100%. This is exactly the distributor reconciliation feature for Phase 3.

---

## 2. Output format specification

All three of Shahid's real estimates follow the same Price Estimate template. Our CSV/XLSX export must match this format.

### Header section
```
Price Estimate
[Company Name]                          (e.g., NTT Data)
[Legal Entity]                          (e.g., Dimension Data Saudi Arabia)
[City, Region]
[Address]
[Country]
[Phone]
"Price Estimate for planning and information purposes only and is not a binding offer from Cisco."
Date: [DD-Mon-YYYY]                     Estimate ID:    [CCW Estimate ID]
                                        Deal ID:        [NA or deal number]
                                        Price List:     [e.g., Global Price List Emerging (USD)]
                                        All prices are shown in USD
```

### Line item columns
| Column | Description |
|---|---|
| Part Number | Cisco SKU |
| Smart Account Mandatory | "Yes" or "-" |
| Description | Full Cisco description |
| Service Duration (Months) | "---" for hardware, "36" or similar for services/subscriptions |
| Estimated Lead Time (Days) | Days to ship (e.g., 20, 28, 77) |
| Unit List Price | Cisco list price in USD |
| Pricing Term | Usually blank for standard pricing |
| Qty | Quantity |
| Unit Net Price | List price minus discount |
| Disc(%) | Discount percentage |
| Extended Net Price | Qty × Unit Net Price |

### Footer section
```
Product Total:        [sum of hardware + software + accessory lines]
Service Total:        [sum of SmartNet / support lines]
Subscription Total:   [sum of subscription / license term lines]
Total Price:          [Product + Service + Subscription]

Cisco legal disclaimer (standard text about non-binding estimate)
```

---

## 3. Real estimate: Routing & Switching (C9300L)

**Context:** 2× Catalyst 9300L switches for NTT Data / Dimension Data Saudi Arabia. Date: 14-Oct-2025. Price List: Global Price List Emerging (USD). Estimate ID: OG164161387AE.

### Configuration details

**Hardware:** C9300L-24UXG-4X-A × 2 (24-port, 8 mGig, Network Advantage, 4×10G uplink)

**Licensing:**
- C9300L-DNA-A-24 (DNA Advantage 24-port term license parent) × 2
- C9300L-DNA-A-24-3Y (DNA Advantage 3-year term) × 2 — $2,371.45 list each
- C9300L-NW-A-24 (Network Advantage 24-port license) × 2

**Support:** CON-SNT-C93024GA (SmartNet 8x5xNBD) × 2, 36 months — $2,584.05 list each

**Add-ons (notable):**
- ThousandEyes embedded agent (TE-EMBEDDED-T + TE-EMBEDDED-T-3Y) × 2 — most tools would miss this
- DNA Spaces Extend (D-DNAS-EXT-S-T + D-DNAS-EXT-S-3Y) × 2
- ThousandEyes C9K agent (TE-C9K-SW) × 2

**Hardware accessories:**
- FAN-T2 (fan module) × 6 — 3 per switch
- PWR-C1-1100WAC-P (primary 1100W platinum PSU) × 2
- PWR-C1-1100WAC-P/2 (secondary/redundant PSU) × 2 — $2,317.88 list each
- CAB-TA-UK (UK power cables) × 4 — UK cables for Saudi Arabia (NTT standard)
- C9300L-SSD-NONE (no SSD) × 2
- C9K-ACC-RBFT (rubber feet) × 2
- C9K-ACC-SCR-4 (rack screws) × 2
- CAB-GUIDE-1RU (cable management) × 2

**Stacking:**
- C9300L-STACK-KIT (stacking kit) × 2 — $1,592.03 list each
- C9300L-STACK (stack module) × 4 — 2 per switch
- STACK-T3-50CM (50cm stacking cable) × 2

**Software:** S9300LUK9-179 (IOS XE 17.9 Universal) × 2

**Other:** NETWORK-PNP-LIC (Plug-n-Play) × 2

### What this tells us about the agent
- ThousandEyes and DNA Spaces are add-ons that require domain knowledge to include
- UK power cables are used in Saudi Arabia — this is an NTT/tenant standard, not a Cisco default
- Redundant PSU requires both primary and secondary SKUs (different part numbers)
- Stacking kit + modules + cables are three separate line items
- Fan modules are 3 per switch (chassis-specific knowledge)

---

## 4. Real estimate: Wireless (C9120AX)

**Context:** 8× Catalyst 9120AX access points. Date: 14-Oct-2025. Price List: Global Price List Emerging (USD). Estimate ID: PQ164161394TX.

### Configuration details

**Hardware:** C9120AXE-E (external antenna, 802.11ax, 4×4 MIMO, IoT, BT5, mGig, USB) × 8 — $2,354.48 list each

**Software:** SW9120AX-CAPWAP-K9 (CAPWAP software) × 8

**Accessories:**
- AIR-AP-BRACKET-1 (low profile mounting bracket) × 8
- AIR-AP-T-RAIL-R (ceiling grid clip, recessed) × 8
- AIR-ANT2524DW-RS (2.4GHz 2dBi / 5GHz 4dBi dipole antenna, RP-TNC) × 32 — **4 per AP** (critical: agent must know antenna count per AP model)

**Licensing:** C9120AX-DNA-OPTOUT (DNA subscription opted out) × 8 — **deliberate opt-out, not a missing license**

**Other:**
- NETWORK-PNP-LIC × 8
- C9120AXE-SINGLE (single pack option) × 8
- C9120-OVER (overpack option) × 8

### What this tells us about the agent
- **No SmartNet** on APs — deliberate choice, not an error. The support attachment validation rule needs to handle this.
- **No wireless controller** in this estimate — AP-only. Controller is a separate estimate.
- **4 antennas per external-antenna AP** — the agent must know this per-model ratio
- **DNA opt-out is a valid configuration** — the license attachment rule must accept explicit opt-outs
- **External antenna model (E suffix)** requires antenna SKU selection; internal antenna models don't

---

## 5. Real estimate: Data Center (UCS C220 M6)

**Context:** 1× UCS C220 M6 server. Date: 14-Oct-2025. Price List: Global Price List Emerging (USD). Estimate ID: VZ164162237UR.

**Note:** Data Center is NOT in Phase 1 scope. This estimate is included for reference and future Phase 4 work.

### Key observations
- Server estimates have significantly more line items per unit than switching (30+ lines for 1 server)
- Intersight SaaS management with prepaid 36-month term
- 24×7×4 SmartNet (higher tier than switching's 8×5×NBD)
- Component-level detail: CPU, RAM, RAID controller, drives, PSU, TPM, cables, blanking panels, heatsinks
- Subscription billing with auto-renewal terms

---

## 6. Benchmark scenarios derived from Shahid's data

### Scenario 1: Access Switching (from Routing_Switching.xlsx)
- **Input:** "2× Catalyst 9300L 24-port mGig switches with Network Advantage, DNA Advantage 3-year, redundant power, stacking, 8×5 SmartNet, Saudi Arabia"
- **Expected output:** Match the Routing_Switching.xlsx BoM including ThousandEyes, DNA Spaces, stacking kit/modules/cables, redundant PSU, UK power cables, fan modules
- **Validation checks:** PoE budget, PSU redundancy, stacking cable count, license attachment, support attachment

### Scenario 2: Wireless (from Wireless_2.xlsx)
- **Input:** "8× Cisco 9120AX external antenna APs, ceiling mount, no DNA subscription, Saudi Arabia"
- **Expected output:** Match the Wireless_2.xlsx BoM including 4 antennas per AP, CAPWAP software, mounting hardware, PnP license, DNA opt-out
- **Validation checks:** No false positive on missing license (DNA opt-out is valid), antenna count matches AP count × 4, no false positive on missing SmartNet (valid for APs)

### Additional scenarios to create
- Campus switching refresh: 48-port PoE+ switches (C9300-48P) × 10, stacking, DNA Essentials
- Small office wireless: C9120AXI (internal antenna) × 4 + C9800-L controller
- Mixed switching + wireless: switches + APs + controller in one estimate
- Multi-floor deployment: different switch models per floor based on port density
- Edge cases: all EoX SKUs, region-blocked SKU, PoE budget exceeded, missing stacking cables

---

## 7. Key rules derived from Shahid's real-world patterns

1. **Power cables follow tenant standard, not region default.** UK cables (CAB-TA-UK) used in Saudi Arabia because that's NTT/Dimension Data's standard. The agent's default should come from tenant standards configuration.
2. **SmartNet tiers vary by product type.** 8×5×NBD for switching, 24×7×4 for servers. The agent needs product-family-aware support term defaults.
3. **Redundant PSU = primary + secondary SKUs** (different part numbers, e.g., PWR-C1-1100WAC-P vs PWR-C1-1100WAC-P/2). Not 2× the same SKU.
4. **Stacking = kit + modules + cables** (three separate line items). Module count = 2 per switch. Cable count depends on topology.
5. **External antenna APs need antenna SKUs.** Count = 4 per AP for the C9120AXE model. Internal antenna models don't need antenna SKUs.
6. **DNA opt-out is a valid configuration.** Don't flag it as a missing license.
7. **AP-only estimates (no controller) are valid.** Controller may be in a separate estimate or already deployed.
8. **Fan module count is chassis-specific.** C9300L needs 3 fan modules per switch.
9. **ThousandEyes and DNA Spaces are add-ons** that experienced engineers include but most automation tools would miss. This is domain knowledge, not something derivable from Catalog API alone.
