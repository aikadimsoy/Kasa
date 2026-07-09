### KASA Security-Test Catalog

#### MCP-API
[MEVCUT] | Bearer token required | Test by sending requests without the correct bearer token and ensure they are denied access.

#### Tool-Poisoning
[MEVCUT] | Tools deny-by-default | Attempt to use tools with different agent IDs, including 'system', and verify if access is granted.

#### Vault-Integrity
[MEVCUT] | Audit hash-chain verification | Generate modified audits and attempt to verify the chain using the provided functions. Check for tampering detection.
[EKSIK] | Tool-definition poisoning detector | Try injecting malicious tool definitions or payloads and check for detection by the proposed system.

#### Fingerprint
[EKSIK] | Inconsistent navigator spoofing | Test browser behavior with different language settings, timezones, etc., while comparing against hardcoded de-DE/Berlin values in Layer#1.
[EKSIK] | AudioContext/font noise inconsistency | Generate audiovisual content using different fonts, noises, etc., and verify if Layer#3 consistency engine flags inconsistencies.

#### Network-Leak
[EKSIK] | WebRTC dual-path filter evasion | Attempt to leak IP addresses using WebRTC and verify if the dual-path filter successfully blocks the attempt.

### JSON Block for [EKSIK] Items

```json
[
    {
        "id": "1",
        "category": "Fingerprint",
        "name": "Inconsistent navigator spoofing",
        "tag": "EKSIK",
        "how_to_test": "Test browser behavior with different language settings, timezones, etc., while comparing against hardcoded de-DE/Berlin values in Layer#1.",
        "target": "browser"
    },
    {
        "id": "2",
        "category": "Network-Leak",
        "name": "WebRTC dual-path filter evasion",
        "tag": "EKSIK",
        "how_to_test": "Attempt to leak IP addresses using WebRTC and verify if the dual-path filter successfully blocks the attempt.",
        "target": "browser"
    },
    {
        "id": "3",
        "category": "Vault-Integrity",
        "name": "Tool-definition poisoning detector",
        "tag": "EKSIK",
        "how_to_test": "Try injecting malicious tool definitions or payloads and check for detection by the proposed system.",
        "target": "mcp"
    },
    {
        "id": "4",
        "category": "Fingerprint",
        "name": "AudioContext/font noise inconsistency",
        "tag": "EKSIK",
        "how_to_test": "Generate audiovisual content using different fonts, noises, etc., and verify if Layer#3 consistency engine flags inconsistencies.",
        "target": "browser"
    }
]
```
