import re

# Ordered list of (keyword set, tp_section). First match wins.
_KEYWORD_SECTION_MAP: list[tuple[frozenset[str], str]] = [
    (frozenset({"governance", "policy", "policies", "compliance", "audit", "risk", "regulatory", "regulation", "framework", "strategy", "oversight", "accountability"}), "§5 Governance and Compliance"),
    (frozenset({"firewall", "network", "perimeter", "dmz", "vlan", "segmentation", "routing", "switching", "lan", "wan", "bandwidth", "latency", "tcp", "udp", "ipv6", "ipv4", "dns", "dhcp", "nat", "proxy", "gateway", "ingress", "egress"}), "§6 Network Security Architecture"),
    (frozenset({"identity", "authentication", "mfa", "iam", "access", "privileged", "pam", "rbac", "sso", "ldap", "active", "directory", "credential", "password", "biometric", "token", "authorisation", "authorization", "least", "privilege", "entitlement"}), "§7 Identity and Access Management"),
    (frozenset({"encryption", "cryptography", "cryptographic", "data", "protection", "key", "management", "aes", "tls", "pki", "certificate", "hashing", "sha", "rsa", "masking", "tokenisation", "tokenization", "dlp", "classification", "labelling", "labeling", "confidential", "privacy", "pii", "gdpr", "pdpl"}), "§8 Data Protection"),
    (frozenset({"siem", "monitoring", "logging", "log", "soc", "detection", "correlation", "alert", "alerting", "threat", "intelligence", "ueba", "soar", "ndr", "xdr", "telemetry", "visibility", "anomaly", "event"}), "§9 Security Operations"),
    (frozenset({"incident", "response", "recovery", "bcdr", "continuity", "disaster", "rto", "rpo", "backup", "restore", "resilience", "failover", "redundancy", "availability", "outage", "disruption", "restoration"}), "§10 Incident Management"),
    (frozenset({"endpoint", "antivirus", "edr", "workstation", "laptop", "desktop", "mobile", "device", "mdm", "malware", "ransomware", "antimalware", "uem", "byod", "removable", "usb", "media"}), "§11 Endpoint Security"),
    (frozenset({"cloud", "saas", "paas", "iaas", "azure", "aws", "gcp", "hosted", "hosting", "tenant", "multitenancy", "shared", "responsibility", "cspm", "casb", "serverless", "container", "kubernetes", "docker"}), "§12 Cloud Security"),
    (frozenset({"physical", "cctv", "surveillance", "datacenter", "data", "centre", "badge", "biometric", "environmental", "fire", "suppression", "ups", "power", "cooling", "hvac", "rack", "cage", "colocation"}), "§13 Physical Security"),
    (frozenset({"vulnerability", "patch", "patching", "scanning", "penetration", "pentest", "assessment", "cvss", "cve", "remediation", "hardening", "baseline", "configuration", "misconfiguration", "exploit"}), "§14 Vulnerability Management"),
    (frozenset({"supply", "chain", "third", "party", "vendor", "supplier", "outsource", "outsourcing", "contractor", "subcontractor", "procurement", "due", "diligence", "mssp", "managed", "service"}), "§15 Third-Party Risk"),
    (frozenset({"awareness", "training", "phishing", "simulation", "education", "culture", "behavior", "behaviour", "social", "engineering", "staff", "employee", "personnel"}), "§16 Security Awareness"),
]

_DEFAULT_SECTION = "§6 Network Security Architecture"


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def link_tp_sections(matrix_rows: list[dict]) -> list[dict]:
    """
    Set tp_section on each matrix row based on keyword matching against
    req_text + control_name. Mutates rows in place and returns the list.
    Asserts that every mandatory row has a non-empty tp_section before returning.
    """
    for row in matrix_rows:
        if row.get("gap_type") == "orphan" and not row.get("req_text"):
            row["tp_section"] = _DEFAULT_SECTION
            continue

        tokens = _tokenize(
            (row.get("req_text") or "") + " " + (row.get("control_name") or "")
        )

        assigned = _DEFAULT_SECTION
        for keywords, section in _KEYWORD_SECTION_MAP:
            if tokens & keywords:
                assigned = section
                break

        row["tp_section"] = assigned

    # Invariant: every mandatory row must have a non-empty tp_section
    for row in matrix_rows:
        if row.get("classification") == "mandatory":
            if not row.get("tp_section"):
                raise ValueError(
                    f"Mandatory requirement {row.get('req_id')} has no tp_section assigned"
                )

    return matrix_rows
