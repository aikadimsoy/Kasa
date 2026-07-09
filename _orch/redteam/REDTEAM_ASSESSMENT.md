# KASA Red-Team Assessment Consolidated Report

## Executive Summary
This report summarizes the findings from a red-team assessment conducted on the KASA project. The assessment focused on testing the security of the MCP vault server and the anti-fingerprinting capabilities of the WebView2 browser. Key risks identified include critical identity leaks in the browser, authorization flaws in the MCP server, and potential for real-world adversaries to fingerprint users' systems. Remediation is required to mitigate these risks.

## Severity Table

| Finding | Track | Severity | One-line evidence | Fix |
|---------|-------|----------|------------------|-----|
| B1 First-load race | B | CRITICAL | Real locale, resolution, cores/mem, GPU leak on first page load. | Implement pre-injection on the very first paint event. |
| C5 System impersonation | C | CRITICAL | Any bearer-token holder sets agent_id="system" and bypasses all permission checks. | Bind agent_id to authenticated identity. |
| C7 Privilege escalation via grant_permission | C | CRITICAL | Random agent called grant_permission(scope="profile:write") then wrote successfully (pwn.esc). The grant PERSISTS. | Put grant_permission behind an admin-only scope. |

## Browser Identity Leaks

The two-pass experiment was conducted to test the effectiveness of the WebView2 browser's anti-fingerprinting capabilities. In PASS 1, before pre-injection applied, real identity details such as locale (tr), resolution (3440x1440), cores/memory (16/32), and GPU ("NVIDIA RTX 5070") were leaked. In PASS 2, after pre-injection was active, some values like canvas hash and WebRTC changed, but the GPU and timezone remained unchanged, indicating persistent identity leaks.

## MCP Server Authorization Flaws

The shared root cause of C5 (System impersonation), C7 (Privilege escalation via grant_permission), and C8 (Private-method exposure) is that the authorization model trusts client-supplied agent_id and exposes every attribute via hasattr. This allows any bearer-token holder to set agent_id="system" and bypass all permission checks.

## What is already SOLID

- TRACK A: The MCP vault server core passed all Layer 1 smoke tests, proving up the schema, event write/read, health endpoint, end-to-end authorized ingest, no-token rejection, audit log written, and run.py wiring.
- TRACK D: Literature research independently flagged the same gaps we proved live.

## Prioritized Remediation

1. Implement pre-injection on the very first paint event to prevent real identity leaks in PASS 1 (B1).
2. Bind agent_id to authenticated identity to fix C5 System impersonation.
3. Put grant_permission behind an admin-only scope to fix C7 Privilege escalation via grant_permission.

## Turkish Summary (Turkce Ozet)

KASA projesi için bir kırmızı takım değerlendirme raporunu sunuyoruz. Değerlendirmenin odak noktası, MCP kasası sunucusunun ve WebView2 tarayıcısının anti-fingerprinting yeteneklerinin güvenliğini test etmeyi içeriyordu. Belirtilen önemli riskler arasında tarayıcıdaki kimlik açıkları ve MCP sunucundaki izlenim yetkisizliği yer alıyor. Bu risklerin giderilmesi için düzelme gerektiği belirildi.

Raporda ayrıca tarayıcının kimlik bilgilerini koruyan önlemler ve MCP sunucusunun güvenliğini sağlamak için altyapı düzeltmeleri de önerildi. Önerilen önceliklendirilmiş düzeltmeler, sistemdeki güvenlik açıklarını en aza indirirmeye yardımcı olacaktır.
