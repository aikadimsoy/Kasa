[MEVCUT] | MCP-API | Bearer token required | Test by sending requests without the correct bearer token and ensure they are denied access.
[MEVCUT] | Tool-Poisoning | Tools deny-by-default | Attempt to use tools with different agent IDs, including 'system', and verify if access is granted.
[MEVCUT] | Vault-Integrity | Audit hash-chain verification | Generate modified audits and attempt to verify the chain using the provided functions. Check for tampering detection.
[EKSIK] | Fingerprint | Inconsistent navigator spoofing | Test browser behavior with different language settings, timezones, etc., while comparing against hardcoded de-DE/Berlin values in Layer#1.
[EKSIK] | Network-Leak | WebRTC dual-path filter evasion | Attempt to leak IP addresses using WebRTC and verify if the dual-path filter successfully blocks the attempt.
[EKSIK] | Vault-Integrity | Tool-definition poisoning detector | Try injecting malicious tool definitions or payloads and check for detection by the proposed system.
[EKSIK] | Fingerprint | AudioContext/font noise inconsistency | Generate audiovisual content using different fonts, noises, etc., and verify if Layer#3 consistency engine flags inconsistencies.