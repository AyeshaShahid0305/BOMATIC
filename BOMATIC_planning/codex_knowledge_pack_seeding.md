# Codex Task: Knowledge Pack Seeding

## Context

BOMATIC's E2 BoM engine uses `backend/app/engines/e2/data/catalog.json` for SKU
matching. It currently has 20 items — far too few for real demos. E2 also has no
EoX (End-of-Life) checking, so engineers can approve BoMs containing discontinued
products. There are no FX rate or VAT rate data files for the future cost stack.

This task:
1. Expands `catalog.json` to 100 SKUs across Cisco, Fortinet, Aruba, Palo Alto,
   and Juniper.
2. Creates `backend/app/engines/e2/data/eox.json` — a list of EoL/EoS SKUs.
3. Adds a lightweight EoX check to the E2 pipeline — warns (does not block) when
   matched SKUs are discontinued.
4. Creates `backend/app/engines/e2/data/fx_rates.json` and `vat_rates.json` for
   future cost stack use.
5. Updates the E2 reviewer to flag EoX warnings if present.

No DB changes. All data is consumed as JSON files.

---

## Step 1 — Read these files first

1. `backend/app/engines/e2/data/catalog.json` — existing 20 items, understand schema
2. `backend/app/engines/e2/step3_catalog_matcher.py`
3. `backend/app/engines/e2/step4_gap_analyzer.py`
4. `backend/app/engines/e2/pipeline.py`
5. `backend/app/engines/e2/models.py`
6. `backend/app/api/reviewer.py` — run_e2_reviewer function

---

## Step 2 — Replace `backend/app/engines/e2/data/catalog.json`

Replace the entire file with this content (100 SKUs):

```json
[
  {"sku": "ASA5516-FPWR-K9", "product_name": "Cisco ASA 5516-X with FirePOWER Services", "vendor": "Cisco", "category": "security", "keywords": ["firewall", "asa", "firepower", "ngfw", "5516"], "unit_price": 4995.0},
  {"sku": "FPR1120-NGFW-K9", "product_name": "Cisco Firepower 1120 NGFW Appliance", "vendor": "Cisco", "category": "security", "keywords": ["firewall", "firepower", "ngfw", "1120"], "unit_price": 3500.0},
  {"sku": "FPR2110-NGFW-K9", "product_name": "Cisco Firepower 2110 NGFW Appliance", "vendor": "Cisco", "category": "security", "keywords": ["firewall", "firepower", "ngfw", "2110"], "unit_price": 7500.0},
  {"sku": "FPR2120-NGFW-K9", "product_name": "Cisco Firepower 2120 NGFW Appliance", "vendor": "Cisco", "category": "security", "keywords": ["firewall", "firepower", "ngfw", "2120"], "unit_price": 11000.0},
  {"sku": "FPR4110-NGFW-K9", "product_name": "Cisco Firepower 4110 NGFW Appliance", "vendor": "Cisco", "category": "security", "keywords": ["firewall", "firepower", "ngfw", "4110", "datacenter"], "unit_price": 38000.0},
  {"sku": "ASA5506-K9", "product_name": "Cisco ASA 5506-X with FirePOWER Services", "vendor": "Cisco", "category": "security", "keywords": ["firewall", "asa", "5506", "branch"], "unit_price": 995.0},
  {"sku": "C9300-48P-E", "product_name": "Cisco Catalyst 9300 48-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9300", "48", "poe"], "unit_price": 8500.0},
  {"sku": "C9300-24P-E", "product_name": "Cisco Catalyst 9300 24-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9300", "24", "poe"], "unit_price": 5500.0},
  {"sku": "C9300-48T-E", "product_name": "Cisco Catalyst 9300 48-Port Data Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9300", "48", "data"], "unit_price": 6500.0},
  {"sku": "C9300-48U-E", "product_name": "Cisco Catalyst 9300 48-Port UPoE Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9300", "48", "upoe"], "unit_price": 9500.0},
  {"sku": "C9300L-48P-4G-E", "product_name": "Cisco Catalyst 9300L 48-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9300l", "48", "poe", "lite"], "unit_price": 7200.0},
  {"sku": "C9300L-24P-4G-E", "product_name": "Cisco Catalyst 9300L 24-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9300l", "24", "poe", "lite"], "unit_price": 4800.0},
  {"sku": "C9200-48P-E", "product_name": "Cisco Catalyst 9200 48-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9200", "48", "poe"], "unit_price": 4200.0},
  {"sku": "C9200-24P-E", "product_name": "Cisco Catalyst 9200 24-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9200", "24", "poe"], "unit_price": 2800.0},
  {"sku": "C9200-48T-E", "product_name": "Cisco Catalyst 9200 48-Port Data Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9200", "48", "data"], "unit_price": 3200.0},
  {"sku": "C9200L-48P-4G-E", "product_name": "Cisco Catalyst 9200L 48-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9200l", "48", "poe"], "unit_price": 3600.0},
  {"sku": "C9200L-24P-4G-E", "product_name": "Cisco Catalyst 9200L 24-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "9200l", "24", "poe"], "unit_price": 2400.0},
  {"sku": "C9500-16X-E", "product_name": "Cisco Catalyst 9500 16-Port 10G Core Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "core", "catalyst", "9500", "10g", "aggregation"], "unit_price": 18000.0},
  {"sku": "C9500-48Y4C-E", "product_name": "Cisco Catalyst 9500 48-Port 25G Core Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "core", "catalyst", "9500", "25g", "aggregation"], "unit_price": 32000.0},
  {"sku": "C1000-48P-4G-L", "product_name": "Cisco Catalyst 1000 48-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "1000", "48", "poe", "smb"], "unit_price": 1800.0},
  {"sku": "C1000-24P-4G-L", "product_name": "Cisco Catalyst 1000 24-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "1000", "24", "poe", "smb"], "unit_price": 1200.0},
  {"sku": "WS-C3850-48P-E", "product_name": "Cisco Catalyst 3850 48-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "3850", "48", "poe"], "unit_price": 6500.0},
  {"sku": "WS-C3650-48PS-E", "product_name": "Cisco Catalyst 3650 48-Port PoE+ Switch", "vendor": "Cisco", "category": "network", "keywords": ["switch", "catalyst", "3650", "48", "poe"], "unit_price": 4200.0},
  {"sku": "ISR4321/K9", "product_name": "Cisco ISR 4321 Integrated Services Router", "vendor": "Cisco", "category": "network", "keywords": ["router", "isr", "4321", "branch", "wan"], "unit_price": 2200.0},
  {"sku": "ISR4331/K9", "product_name": "Cisco ISR 4331 Integrated Services Router", "vendor": "Cisco", "category": "network", "keywords": ["router", "isr", "4331", "branch", "wan"], "unit_price": 3500.0},
  {"sku": "ISR4351/K9", "product_name": "Cisco ISR 4351 Integrated Services Router", "vendor": "Cisco", "category": "network", "keywords": ["router", "isr", "4351", "branch", "wan"], "unit_price": 6000.0},
  {"sku": "ISR4431/K9", "product_name": "Cisco ISR 4431 Integrated Services Router", "vendor": "Cisco", "category": "network", "keywords": ["router", "isr", "4431", "branch", "wan"], "unit_price": 9500.0},
  {"sku": "C8300-1N1S-4T2X", "product_name": "Cisco Catalyst 8300 Edge Router 4-Port", "vendor": "Cisco", "category": "network", "keywords": ["router", "catalyst", "8300", "edge", "wan", "sd-wan"], "unit_price": 4800.0},
  {"sku": "C8200-1N-4T", "product_name": "Cisco Catalyst 8200 Edge Router", "vendor": "Cisco", "category": "network", "keywords": ["router", "catalyst", "8200", "edge", "wan", "sd-wan", "branch"], "unit_price": 2900.0},
  {"sku": "AIR-AP2802I-E-K9", "product_name": "Cisco Aironet 2800i Access Point", "vendor": "Cisco", "category": "wireless", "keywords": ["access point", "ap", "wifi", "wireless", "2800", "aironet", "indoor"], "unit_price": 850.0},
  {"sku": "AIR-AP3802I-E-K9", "product_name": "Cisco Aironet 3800i Access Point", "vendor": "Cisco", "category": "wireless", "keywords": ["access point", "ap", "wifi", "wireless", "3800", "aironet", "indoor"], "unit_price": 1100.0},
  {"sku": "CW9162I-EWC-E", "product_name": "Cisco Catalyst 9162 Wi-Fi 6 Access Point", "vendor": "Cisco", "category": "wireless", "keywords": ["access point", "ap", "wifi", "wifi6", "wireless", "9162", "catalyst", "indoor"], "unit_price": 650.0},
  {"sku": "CW9164I-EWC-E", "product_name": "Cisco Catalyst 9164 Wi-Fi 6 Access Point", "vendor": "Cisco", "category": "wireless", "keywords": ["access point", "ap", "wifi", "wifi6", "wireless", "9164", "catalyst", "indoor"], "unit_price": 850.0},
  {"sku": "CW9166I-EWC-E", "product_name": "Cisco Catalyst 9166 Wi-Fi 6E Access Point", "vendor": "Cisco", "category": "wireless", "keywords": ["access point", "ap", "wifi", "wifi6e", "wireless", "9166", "catalyst", "indoor"], "unit_price": 1100.0},
  {"sku": "CW9163E-EWC-E", "product_name": "Cisco Catalyst 9163 Wi-Fi 6E Outdoor AP", "vendor": "Cisco", "category": "wireless", "keywords": ["access point", "ap", "wifi", "wifi6e", "wireless", "outdoor", "9163", "catalyst"], "unit_price": 1400.0},
  {"sku": "C9800-L-F-K9", "product_name": "Cisco Catalyst 9800-L Wireless Controller", "vendor": "Cisco", "category": "wireless", "keywords": ["wireless controller", "wlc", "9800", "catalyst", "controller"], "unit_price": 4500.0},
  {"sku": "C9800-40-K9", "product_name": "Cisco Catalyst 9800-40 Wireless Controller", "vendor": "Cisco", "category": "wireless", "keywords": ["wireless controller", "wlc", "9800", "catalyst", "controller"], "unit_price": 12000.0},
  {"sku": "UCSC-C220-M6S", "product_name": "Cisco UCS C220 M6 Rack Server", "vendor": "Cisco", "category": "hardware", "keywords": ["server", "rack", "ucs", "c220", "compute"], "unit_price": 8500.0},
  {"sku": "UCSC-C240-M6S", "product_name": "Cisco UCS C240 M6 Rack Server", "vendor": "Cisco", "category": "hardware", "keywords": ["server", "rack", "ucs", "c240", "storage", "compute"], "unit_price": 12000.0},
  {"sku": "C9300-DNA-A-48-3Y", "product_name": "Cisco DNA Advantage 48-Port 3-Year License", "vendor": "Cisco", "category": "license", "keywords": ["license", "dna", "advantage", "software", "subscription", "3 year", "catalyst"], "unit_price": 1440.0},
  {"sku": "C9300-DNA-A-24-3Y", "product_name": "Cisco DNA Advantage 24-Port 3-Year License", "vendor": "Cisco", "category": "license", "keywords": ["license", "dna", "advantage", "software", "subscription", "3 year", "catalyst"], "unit_price": 900.0},
  {"sku": "C9300-DNA-E-48-3Y", "product_name": "Cisco DNA Essentials 48-Port 3-Year License", "vendor": "Cisco", "category": "license", "keywords": ["license", "dna", "essentials", "software", "subscription", "3 year", "catalyst"], "unit_price": 720.0},
  {"sku": "C9200-DNA-A-48-3Y", "product_name": "Cisco DNA Advantage C9200 48-Port 3-Year", "vendor": "Cisco", "category": "license", "keywords": ["license", "dna", "advantage", "software", "subscription", "3 year", "9200"], "unit_price": 960.0},
  {"sku": "C9300-DNA-A-3Y", "product_name": "Cisco DNA Advantage 3-Year License", "vendor": "Cisco", "category": "license", "keywords": ["license", "dna", "advantage", "software", "subscription", "3 year"], "unit_price": 1200.0},
  {"sku": "FG-60F", "product_name": "Fortinet FortiGate 60F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "60f", "branch", "smb"], "unit_price": 1200.0},
  {"sku": "FG-80F", "product_name": "Fortinet FortiGate 80F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "80f", "branch"], "unit_price": 1800.0},
  {"sku": "FG-100F", "product_name": "Fortinet FortiGate 100F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "100f"], "unit_price": 2800.0},
  {"sku": "FG-200F", "product_name": "Fortinet FortiGate 200F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "200f", "campus"], "unit_price": 5500.0},
  {"sku": "FG-300E", "product_name": "Fortinet FortiGate 300E Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "300e", "campus"], "unit_price": 6500.0},
  {"sku": "FG-400F", "product_name": "Fortinet FortiGate 400F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "400f", "campus", "datacenter"], "unit_price": 9500.0},
  {"sku": "FG-600F", "product_name": "Fortinet FortiGate 600F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "600f", "datacenter"], "unit_price": 15000.0},
  {"sku": "FG-1000F", "product_name": "Fortinet FortiGate 1000F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "1000f", "datacenter", "enterprise"], "unit_price": 28000.0},
  {"sku": "FG-1800F", "product_name": "Fortinet FortiGate 1800F Next-Generation Firewall", "vendor": "Fortinet", "category": "security", "keywords": ["firewall", "fortigate", "ngfw", "1800f", "datacenter", "enterprise", "high performance"], "unit_price": 55000.0},
  {"sku": "FAP-43F", "product_name": "Fortinet FortiAP 43F Indoor Wi-Fi 6 Access Point", "vendor": "Fortinet", "category": "wireless", "keywords": ["access point", "ap", "fortiap", "wifi", "wifi6", "wireless", "indoor", "43f"], "unit_price": 380.0},
  {"sku": "FAP-231F", "product_name": "Fortinet FortiAP 231F Indoor Wi-Fi 6 Access Point", "vendor": "Fortinet", "category": "wireless", "keywords": ["access point", "ap", "fortiap", "wifi", "wifi6", "wireless", "indoor", "231f"], "unit_price": 450.0},
  {"sku": "FAP-234F", "product_name": "Fortinet FortiAP 234F Indoor Dual-Band Access Point", "vendor": "Fortinet", "category": "wireless", "keywords": ["access point", "ap", "fortiap", "wifi", "wireless", "indoor", "234f"], "unit_price": 520.0},
  {"sku": "FAP-431F", "product_name": "Fortinet FortiAP 431F High-Performance Indoor AP", "vendor": "Fortinet", "category": "wireless", "keywords": ["access point", "ap", "fortiap", "wifi", "wifi6", "wireless", "indoor", "431f", "enterprise"], "unit_price": 750.0},
  {"sku": "FAP-443K", "product_name": "Fortinet FortiAP 443K Indoor Wi-Fi 6E Access Point", "vendor": "Fortinet", "category": "wireless", "keywords": ["access point", "ap", "fortiap", "wifi", "wifi6e", "wireless", "indoor", "443k"], "unit_price": 950.0},
  {"sku": "FAP-832F", "product_name": "Fortinet FortiAP 832F Outdoor Access Point", "vendor": "Fortinet", "category": "wireless", "keywords": ["access point", "ap", "fortiap", "wifi", "wireless", "outdoor", "832f"], "unit_price": 1100.0},
  {"sku": "FSW-124E-FPOE", "product_name": "Fortinet FortiSwitch 124E-FPOE 24-Port PoE+", "vendor": "Fortinet", "category": "network", "keywords": ["switch", "fortiswitch", "24", "poe", "124e"], "unit_price": 950.0},
  {"sku": "FSW-148F-FPOE", "product_name": "Fortinet FortiSwitch 148F-FPOE 48-Port PoE+", "vendor": "Fortinet", "category": "network", "keywords": ["switch", "fortiswitch", "48", "poe", "148f"], "unit_price": 1400.0},
  {"sku": "FSW-248E-FPOE", "product_name": "Fortinet FortiSwitch 248E-FPOE 48-Port PoE+", "vendor": "Fortinet", "category": "network", "keywords": ["switch", "fortiswitch", "48", "poe", "248e"], "unit_price": 1800.0},
  {"sku": "FSW-448F-FPOE", "product_name": "Fortinet FortiSwitch 448F-FPOE 48-Port PoE+", "vendor": "Fortinet", "category": "network", "keywords": ["switch", "fortiswitch", "48", "poe", "448f", "enterprise"], "unit_price": 2800.0},
  {"sku": "FAZ-200G", "product_name": "Fortinet FortiAnalyzer 200G Log Management", "vendor": "Fortinet", "category": "security", "keywords": ["analyzer", "fortianalyzer", "log", "siem", "reporting", "200g"], "unit_price": 5500.0},
  {"sku": "FMG-200G", "product_name": "Fortinet FortiManager 200G Network Management", "vendor": "Fortinet", "category": "security", "keywords": ["manager", "fortimanager", "management", "nms", "200g"], "unit_price": 5500.0},
  {"sku": "FC-10-F100F-247-02-12", "product_name": "Fortinet FortiGate 100F 1-Year 24x7 Support", "vendor": "Fortinet", "category": "license", "keywords": ["license", "support", "fortigate", "100f", "subscription", "1 year", "24x7"], "unit_price": 420.0},
  {"sku": "FC-10-F200F-247-02-12", "product_name": "Fortinet FortiGate 200F 1-Year 24x7 Support", "vendor": "Fortinet", "category": "license", "keywords": ["license", "support", "fortigate", "200f", "subscription", "1 year", "24x7"], "unit_price": 825.0},
  {"sku": "FC-10-F100F-131-02-12", "product_name": "Fortinet FortiGate 100F 1-Year FortiGuard Bundle", "vendor": "Fortinet", "category": "license", "keywords": ["license", "fortigate", "100f", "subscription", "1 year", "fortiguard", "utm"], "unit_price": 780.0},
  {"sku": "FC-10-F200F-131-02-36", "product_name": "Fortinet FortiGate 200F 3-Year FortiGuard Bundle", "vendor": "Fortinet", "category": "license", "keywords": ["license", "fortigate", "200f", "subscription", "3 year", "fortiguard", "utm"], "unit_price": 2475.0},
  {"sku": "JL675A", "product_name": "Aruba 6300M 24-Port SFP+ Switch", "vendor": "Aruba", "category": "network", "keywords": ["switch", "aruba", "6300", "24", "sfp", "hpe"], "unit_price": 5800.0},
  {"sku": "JL676A", "product_name": "Aruba 6300M 48-Port PoE+ Switch", "vendor": "Aruba", "category": "network", "keywords": ["switch", "aruba", "6300", "48", "poe", "hpe"], "unit_price": 7200.0},
  {"sku": "JL253A", "product_name": "Aruba 2930F 24-Port PoE+ Switch", "vendor": "Aruba", "category": "network", "keywords": ["switch", "aruba", "2930f", "24", "poe", "hpe"], "unit_price": 2400.0},
  {"sku": "JL254A", "product_name": "Aruba 2930F 48-Port PoE+ Switch", "vendor": "Aruba", "category": "network", "keywords": ["switch", "aruba", "2930f", "48", "poe", "hpe"], "unit_price": 3600.0},
  {"sku": "JL322A", "product_name": "Aruba 2540 24-Port PoE+ Switch", "vendor": "Aruba", "category": "network", "keywords": ["switch", "aruba", "2540", "24", "poe", "hpe"], "unit_price": 1400.0},
  {"sku": "JL323A", "product_name": "Aruba 2540 48-Port PoE+ Switch", "vendor": "Aruba", "category": "network", "keywords": ["switch", "aruba", "2540", "48", "poe", "hpe"], "unit_price": 2000.0},
  {"sku": "R0X26A", "product_name": "Aruba AP-515 802.11ax Wi-Fi 6 Access Point", "vendor": "Aruba", "category": "wireless", "keywords": ["access point", "ap", "aruba", "wifi", "wifi6", "wireless", "indoor", "515"], "unit_price": 900.0},
  {"sku": "R2H22A", "product_name": "Aruba AP-635 802.11ax Wi-Fi 6E Access Point", "vendor": "Aruba", "category": "wireless", "keywords": ["access point", "ap", "aruba", "wifi", "wifi6e", "wireless", "indoor", "635"], "unit_price": 1200.0},
  {"sku": "R1Y27A", "product_name": "Aruba AP-575 Outdoor Wi-Fi 6 Access Point", "vendor": "Aruba", "category": "wireless", "keywords": ["access point", "ap", "aruba", "wifi", "wifi6", "wireless", "outdoor", "575"], "unit_price": 1500.0},
  {"sku": "JW688A", "product_name": "Aruba 7205 Mobility Controller", "vendor": "Aruba", "category": "wireless", "keywords": ["wireless controller", "wlc", "aruba", "7205", "mobility", "controller"], "unit_price": 8500.0},
  {"sku": "PA-440", "product_name": "Palo Alto Networks PA-440 NGFW", "vendor": "Palo Alto", "category": "security", "keywords": ["firewall", "palo alto", "ngfw", "pa-440", "branch", "zero trust"], "unit_price": 4000.0},
  {"sku": "PA-850", "product_name": "Palo Alto Networks PA-850 NGFW", "vendor": "Palo Alto", "category": "security", "keywords": ["firewall", "palo alto", "ngfw", "pa-850", "campus", "zero trust"], "unit_price": 10000.0},
  {"sku": "PA-1410", "product_name": "Palo Alto Networks PA-1410 NGFW", "vendor": "Palo Alto", "category": "security", "keywords": ["firewall", "palo alto", "ngfw", "pa-1410", "campus", "datacenter"], "unit_price": 18000.0},
  {"sku": "PA-3220", "product_name": "Palo Alto Networks PA-3220 NGFW", "vendor": "Palo Alto", "category": "security", "keywords": ["firewall", "palo alto", "ngfw", "pa-3220", "datacenter", "enterprise"], "unit_price": 35000.0},
  {"sku": "PA-5220", "product_name": "Palo Alto Networks PA-5220 NGFW", "vendor": "Palo Alto", "category": "security", "keywords": ["firewall", "palo alto", "ngfw", "pa-5220", "datacenter", "enterprise", "high performance"], "unit_price": 70000.0},
  {"sku": "EX2300-24P", "product_name": "Juniper EX2300 24-Port PoE+ Switch", "vendor": "Juniper", "category": "network", "keywords": ["switch", "juniper", "ex2300", "24", "poe", "access"], "unit_price": 2200.0},
  {"sku": "EX2300-48P", "product_name": "Juniper EX2300 48-Port PoE+ Switch", "vendor": "Juniper", "category": "network", "keywords": ["switch", "juniper", "ex2300", "48", "poe", "access"], "unit_price": 3400.0},
  {"sku": "EX3400-24P", "product_name": "Juniper EX3400 24-Port PoE+ Switch", "vendor": "Juniper", "category": "network", "keywords": ["switch", "juniper", "ex3400", "24", "poe", "access", "layer3"], "unit_price": 4500.0},
  {"sku": "EX3400-48P", "product_name": "Juniper EX3400 48-Port PoE+ Switch", "vendor": "Juniper", "category": "network", "keywords": ["switch", "juniper", "ex3400", "48", "poe", "access", "layer3"], "unit_price": 6200.0},
  {"sku": "EX4300-48P", "product_name": "Juniper EX4300 48-Port PoE+ Switch", "vendor": "Juniper", "category": "network", "keywords": ["switch", "juniper", "ex4300", "48", "poe", "distribution"], "unit_price": 8500.0},
  {"sku": "SRX300", "product_name": "Juniper SRX300 Services Gateway", "vendor": "Juniper", "category": "security", "keywords": ["firewall", "gateway", "juniper", "srx300", "branch", "security"], "unit_price": 1200.0},
  {"sku": "SRX345", "product_name": "Juniper SRX345 Services Gateway", "vendor": "Juniper", "category": "security", "keywords": ["firewall", "gateway", "juniper", "srx345", "branch", "security"], "unit_price": 2800.0},
  {"sku": "SRX1500", "product_name": "Juniper SRX1500 Services Gateway", "vendor": "Juniper", "category": "security", "keywords": ["firewall", "gateway", "juniper", "srx1500", "campus", "security"], "unit_price": 12000.0},
  {"sku": "GENERIC-UPS-10KVA", "product_name": "10 kVA UPS Power Unit", "vendor": "Generic", "category": "hardware", "keywords": ["ups", "power", "10kva", "uninterruptible", "battery"], "unit_price": 3500.0},
  {"sku": "GENERIC-RACK-42U", "product_name": "42U Server Rack Cabinet", "vendor": "Generic", "category": "hardware", "keywords": ["rack", "cabinet", "42u", "server rack", "enclosure"], "unit_price": 1200.0},
  {"sku": "GENERIC-SFP-1G-LX", "product_name": "1G SFP Single-Mode Fiber Module", "vendor": "Generic", "category": "hardware", "keywords": ["sfp", "transceiver", "fiber", "1g", "single mode", "optical"], "unit_price": 75.0},
  {"sku": "GENERIC-SFP-10G-SR", "product_name": "10G SFP+ Short-Range Fiber Module", "vendor": "Generic", "category": "hardware", "keywords": ["sfp", "sfp+", "transceiver", "fiber", "10g", "short range", "sr", "optical"], "unit_price": 95.0},
  {"sku": "GENERIC-CAT6A-CABLE", "product_name": "Cat6A Shielded Ethernet Cable (per meter)", "vendor": "Generic", "category": "hardware", "keywords": ["cable", "cat6a", "ethernet", "structured cabling", "patch"], "unit_price": 3.5},
  {"sku": "GENERIC-FIBER-OS2", "product_name": "OS2 Single-Mode Fiber Patch Cable (per meter)", "vendor": "Generic", "category": "hardware", "keywords": ["cable", "fiber", "os2", "single mode", "patch", "optical"], "unit_price": 8.0},
  {"sku": "GENERIC-INSTALL-DAY", "product_name": "Professional Installation Services (per day)", "vendor": "Generic", "category": "services", "keywords": ["installation", "services", "professional", "labor", "deployment", "engineer day"], "unit_price": 1200.0},
  {"sku": "GENERIC-SUPPORT-1Y", "product_name": "1-Year Maintenance & Support Contract", "vendor": "Generic", "category": "services", "keywords": ["support", "maintenance", "contract", "1 year", "subscription"], "unit_price": 2400.0}
]
```

---

## Step 3 — Create `backend/app/engines/e2/data/eox.json`

Create this file:

```json
[
  {
    "sku": "WS-C3750X-24P-E",
    "product_name": "Cisco Catalyst 3750X 24-Port PoE+ Switch",
    "end_of_sale": "2016-01-31",
    "end_of_support": "2023-01-31",
    "replacement_sku": "C9300-24P-E"
  },
  {
    "sku": "WS-C3750X-48P-E",
    "product_name": "Cisco Catalyst 3750X 48-Port PoE+ Switch",
    "end_of_sale": "2016-01-31",
    "end_of_support": "2023-01-31",
    "replacement_sku": "C9300-48P-E"
  },
  {
    "sku": "WS-C2960X-48FPS-L",
    "product_name": "Cisco Catalyst 2960X 48-Port PoE+ Switch",
    "end_of_sale": "2023-01-28",
    "end_of_support": "2028-01-31",
    "replacement_sku": "C9200-48P-E"
  },
  {
    "sku": "WS-C2960X-24PS-L",
    "product_name": "Cisco Catalyst 2960X 24-Port PoE+ Switch",
    "end_of_sale": "2023-01-28",
    "end_of_support": "2028-01-31",
    "replacement_sku": "C9200-24P-E"
  },
  {
    "sku": "ASA5506-K9",
    "product_name": "Cisco ASA 5506-X",
    "end_of_sale": "2022-08-31",
    "end_of_support": "2027-08-31",
    "replacement_sku": "FPR1120-NGFW-K9"
  },
  {
    "sku": "ASA5516-FPWR-K9",
    "product_name": "Cisco ASA 5516-X with FirePOWER",
    "end_of_sale": "2022-08-31",
    "end_of_support": "2027-08-31",
    "replacement_sku": "FPR2110-NGFW-K9"
  },
  {
    "sku": "AIR-AP2802I-E-K9",
    "product_name": "Cisco Aironet 2800 Series Access Point",
    "end_of_sale": "2022-04-30",
    "end_of_support": "2027-04-30",
    "replacement_sku": "CW9162I-EWC-E"
  },
  {
    "sku": "AIR-AP3802I-E-K9",
    "product_name": "Cisco Aironet 3800 Series Access Point",
    "end_of_sale": "2022-04-30",
    "end_of_support": "2027-04-30",
    "replacement_sku": "CW9164I-EWC-E"
  },
  {
    "sku": "WS-C3850-48P-E",
    "product_name": "Cisco Catalyst 3850 48-Port PoE+ Switch",
    "end_of_sale": "2022-10-31",
    "end_of_support": "2027-10-31",
    "replacement_sku": "C9300-48P-E"
  },
  {
    "sku": "ISR4331/K9",
    "product_name": "Cisco ISR 4331",
    "end_of_sale": "2023-10-31",
    "end_of_support": "2028-10-31",
    "replacement_sku": "C8300-1N1S-4T2X"
  }
]
```

---

## Step 4 — Create `backend/app/engines/e2/data/fx_rates.json`

```json
{
  "base_currency": "USD",
  "rates": {
    "USD": 1.0,
    "SAR": 3.75,
    "AED": 3.673,
    "EGP": 30.9,
    "KWD": 0.307,
    "QAR": 3.64,
    "BHD": 0.376,
    "OMR": 0.385,
    "GBP": 0.79,
    "EUR": 0.92
  },
  "updated": "2025-01-01"
}
```

---

## Step 5 — Create `backend/app/engines/e2/data/vat_rates.json`

```json
{
  "rates": {
    "SA": {"rate": 0.15, "name": "Saudi Arabia VAT"},
    "AE": {"rate": 0.05, "name": "UAE VAT"},
    "EG": {"rate": 0.14, "name": "Egypt VAT"},
    "KW": {"rate": 0.0,  "name": "Kuwait (no VAT)"},
    "QA": {"rate": 0.0,  "name": "Qatar (no VAT)"},
    "BH": {"rate": 0.10, "name": "Bahrain VAT"},
    "OM": {"rate": 0.05, "name": "Oman VAT"},
    "GB": {"rate": 0.20, "name": "UK VAT"},
    "DE": {"rate": 0.19, "name": "Germany VAT"},
    "US": {"rate": 0.0,  "name": "USA (no federal VAT)"}
  }
}
```

---

## Step 6 — Create `backend/app/engines/e2/step_eox_checker.py`

```python
"""
EoX (End-of-Life/End-of-Sale) checker for matched SKUs.

check_eox(matched_skus, eox_data) -> list[dict]

Returns a list of EoX warning dicts for any matched SKU found in the EoX list.
"""

import json
from datetime import date
from pathlib import Path

_EOX_PATH = Path(__file__).parent / "data" / "eox.json"


def _load_eox() -> dict[str, dict]:
    """Load EoX data as a dict keyed by SKU (uppercase)."""
    try:
        with open(_EOX_PATH, encoding="utf-8") as f:
            records = json.load(f)
        return {r["sku"].upper(): r for r in records}
    except Exception:
        return {}


def check_eox(matched_skus: list[str]) -> list[dict]:
    """
    Check a list of SKUs against the EoX database.

    Args:
        matched_skus: list of SKU strings from the catalog match results.

    Returns:
        list of dicts, one per EoX hit:
        {
            "sku": str,
            "product_name": str,
            "end_of_sale": str,       # ISO date or ""
            "end_of_support": str,    # ISO date or ""
            "replacement_sku": str,
            "is_end_of_sale": bool,   # EoS date is in the past
            "is_end_of_support": bool # EoL date is in the past
        }
    """
    eox_db = _load_eox()
    today = date.today().isoformat()
    warnings = []

    for sku in matched_skus:
        record = eox_db.get(sku.upper())
        if not record:
            continue

        eos = record.get("end_of_sale", "")
        eol = record.get("end_of_support", "")

        warnings.append({
            "sku": sku,
            "product_name": record.get("product_name", ""),
            "end_of_sale": eos,
            "end_of_support": eol,
            "replacement_sku": record.get("replacement_sku", ""),
            "is_end_of_sale": bool(eos and eos <= today),
            "is_end_of_support": bool(eol and eol <= today),
        })

    return warnings
```

---

## Step 7 — Update `backend/app/engines/e2/pipeline.py`

**Add import:**
```python
from .step_eox_checker import check_eox
```

**Add EoX check** after `match_catalog` and before `analyze_gaps`. Find:

```python
    matches = match_catalog(rfp_items, vendor_list=e1_output.vendor_list if e1_output else None)
    summary = analyze_gaps(matches)
```

Replace with:
```python
    matches = match_catalog(rfp_items, vendor_list=e1_output.vendor_list if e1_output else None)

    # EoX check on matched SKUs
    matched_skus = [m.sku for m in matches if m.sku]
    eox_warnings = check_eox(matched_skus)

    summary = analyze_gaps(matches)
```

**Add `eox_warnings` to the return dict:**
```python
    return {
        "output_file": output_path,
        "distributor_file": distributor_path.name,
        "vendor_list": e1_output.vendor_list if e1_output else [],
        "requirements_baseline_count": len(e1_output.requirements_baseline) if e1_output else 0,
        "matched_count": len(summary.matched_items),
        "unmatched_count": len(summary.unmatched_items),
        "low_confidence_count": len(summary.low_confidence_items),
        "subtotal": summary.subtotal,
        "discount_amount": summary.discount_amount,
        "total": summary.total,
        "currency": summary.currency,
        "boq_items": boq_items,
        "eox_warnings": eox_warnings,
    }
```

---

## Step 8 — Update `backend/app/api/e2_routes.py`

**Store `eox_warnings` in step_outputs["e2"].**

Find the `outputs['e2']` block and add:
```python
                'eox_warnings': result.get('eox_warnings', []),
```

---

## Step 9 — Update `run_e2_reviewer` in `backend/app/api/reviewer.py`

Add an EoX check after the existing deterministic checks in `run_e2_reviewer`.
Find the block that checks `vendor_list`:
```python
    # Warning: no vendors identified from E1
    if not vendor_list:
        warnings.append(
            "No vendor list was passed from E1. ..."
        )
```

Add immediately after it:
```python
    # Warning: EoX hits
    eox_warnings = e2_data.get("eox_warnings", [])
    eos_hits = [w for w in eox_warnings if w.get("is_end_of_sale")]
    eol_hits = [w for w in eox_warnings if w.get("is_end_of_support")]

    if eol_hits:
        skus = ", ".join(w["sku"] for w in eol_hits[:3])
        more = f" (+{len(eol_hits) - 3} more)" if len(eol_hits) > 3 else ""
        errors.append(
            f"End-of-Life SKUs in BoM: {skus}{more}. These products are no longer "
            "supported — replace with recommended alternatives before submitting."
        )
    elif eos_hits:
        skus = ", ".join(w["sku"] for w in eos_hits[:3])
        more = f" (+{len(eos_hits) - 3} more)" if len(eos_hits) > 3 else ""
        warnings.append(
            f"End-of-Sale SKUs in BoM: {skus}{more}. These products can no longer "
            "be ordered — verify availability or use replacements."
        )
```

Note: EoL (end of support) is an error — the product is unsupported. EoS (end of
sale only, still supported) is a warning — the product works but can't be reordered.

---

## Step 10 — Validation steps

### 10A. JSON validity check
```
backend\.venv\Scripts\python.exe -c "
import json
for f in [
    'backend/app/engines/e2/data/catalog.json',
    'backend/app/engines/e2/data/eox.json',
    'backend/app/engines/e2/data/fx_rates.json',
    'backend/app/engines/e2/data/vat_rates.json',
]:
    d = json.load(open(f))
    count = len(d) if isinstance(d, list) else len(d.get('rates', d))
    print(f'{f}: valid JSON, {count} items')
"
```
Expected: 4 lines, catalog showing 100, eox showing 10, fx_rates showing 10, vat_rates showing 10.

### 10B. Syntax check
```
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/step_eox_checker.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/engines/e2/pipeline.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/e2_routes.py
backend\.venv\Scripts\python.exe -m py_compile backend/app/api/reviewer.py
```
Expected: no output.

### 10C. EoX checker unit test
```
backend\.venv\Scripts\python.exe -c "
from app.engines.e2.step_eox_checker import check_eox

# Known EoL SKU
results = check_eox(['WS-C3750X-48P-E', 'C9300-48P-E'])
assert len(results) == 1, f'Expected 1 EoX hit, got {len(results)}'
assert results[0]['sku'] == 'WS-C3750X-48P-E'
assert results[0]['is_end_of_sale'] == True
assert results[0]['replacement_sku'] == 'C9300-48P-E'
print('EoX checker: PASS')

# Empty input
results = check_eox([])
assert results == []
print('EoX empty: PASS')

# Unknown SKU
results = check_eox(['NONEXISTENT-SKU'])
assert results == []
print('EoX unknown: PASS')
"
```
Expected: 3 PASS lines.

### 10D. Catalog size check
```
backend\.venv\Scripts\python.exe -c "
import json
catalog = json.load(open('backend/app/engines/e2/data/catalog.json'))
assert len(catalog) >= 100, f'Catalog has only {len(catalog)} items'
vendors = set(c['vendor'] for c in catalog)
print(f'Catalog: {len(catalog)} items, vendors: {vendors}')
assert 'Cisco' in vendors
assert 'Fortinet' in vendors
assert 'Aruba' in vendors
print('Catalog check: PASS')
"
```
Expected: vendor set includes Cisco, Fortinet, Aruba, and PASS.

### 10E. Reviewer EoX integration test
```
backend\.venv\Scripts\python.exe -c "
from app.api.reviewer import run_e2_reviewer

# EoL SKU in BoM should become an error
e2_data = {
    'matched_count': 5,
    'unmatched_count': 0,
    'low_confidence_count': 0,
    'total': 50000,
    'currency': 'USD',
    'vendor_list': ['Cisco'],
    'requirements_baseline_count': 5,
    'eox_warnings': [
        {'sku': 'WS-C3750X-48P-E', 'is_end_of_sale': True,
         'is_end_of_support': True, 'replacement_sku': 'C9300-48P-E'}
    ],
}
result = run_e2_reviewer(e2_data, api_key='')
assert not result['passed'], 'EoL SKU should fail review'
assert any('End-of-Life' in e for e in result['errors'])
print('EoX reviewer error: PASS')

# EoS only should be a warning not error
e2_data['eox_warnings'][0]['is_end_of_support'] = False
result = run_e2_reviewer(e2_data, api_key='')
assert result['passed'], 'EoS-only should pass'
assert any('End-of-Sale' in w for w in result['warnings'])
print('EoX reviewer warning: PASS')
"
```
Expected: 2 PASS lines.

---

## Step 11 — Summary of files changed

| Action   | File path                                          |
|----------|----------------------------------------------------|
| Modified | `backend/app/engines/e2/data/catalog.json`         |
| Created  | `backend/app/engines/e2/data/eox.json`             |
| Created  | `backend/app/engines/e2/data/fx_rates.json`        |
| Created  | `backend/app/engines/e2/data/vat_rates.json`       |
| Created  | `backend/app/engines/e2/step_eox_checker.py`       |
| Modified | `backend/app/engines/e2/pipeline.py`               |
| Modified | `backend/app/api/e2_routes.py`                     |
| Modified | `backend/app/api/reviewer.py`                      |

No DB migration. No frontend changes. No new pip dependencies.

---

## Step 12 — Git commit message

```
feat: expand knowledge packs — 100-SKU catalog, EoX checking, FX/VAT rates

- catalog.json: expanded from 20 to 100 SKUs covering Cisco (switches,
  routers, wireless, security, UCS, licenses), Fortinet (firewalls,
  FortiSwitch, FortiAP, FortiAnalyzer, FortiManager, licenses), Aruba
  (switches, APs, controller), Palo Alto (PA-440 through PA-5220),
  Juniper (EX2300/3400/4300 switches, SRX gateways), Generic
  (cabling, racks, services)

- eox.json: 10 known EoL/EoS Cisco SKUs with end-of-sale date,
  end-of-support date, and recommended replacement SKU

- fx_rates.json: USD-based rates for SAR, AED, EGP, KWD, QAR,
  BHD, OMR, GBP, EUR (for future cost stack CS-001)

- vat_rates.json: VAT rates for SA (15%), AE (5%), EG (14%),
  BH (10%), OM (5%), KW/QA/US (0%), GB (20%), DE (19%)

- step_eox_checker.py: check_eox(matched_skus) -> list[dict]
  Loads eox.json, returns hits with is_end_of_sale/is_end_of_support flags

- pipeline.py: run EoX check after catalog matching; add eox_warnings
  to result dict

- e2_routes.py: store eox_warnings in step_outputs["e2"]

- reviewer.py: run_e2_reviewer checks eox_warnings — EoL SKUs become
  errors (unsupported), EoS-only SKUs become warnings (unavailable)
```
