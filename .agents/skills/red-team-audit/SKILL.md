---
name: red-team-audit
description: >
  Autonomous offensive security engineering and red-team audit skill.
  Systematically audits codebases across web, mobile, desktop, cloud, database,
  and AI systems to uncover vulnerabilities, simulate exploit scenarios, and
  prescribe exact remediation diffs. Use when asked to red-team, pentest,
  conduct security audits, find vulnerabilities, or harden an application.
---

# Red-Team Security Audit

A systematic, adversarial offensive security engineering skill designed to audit any software system: Web apps, Mobile apps (iOS/Android), Desktop apps, Cloud backends, and AI/LLM integrations.

## Core Mindset

1. Assume the adversary already has read access to the entire repository and dependency tree.
2. Assume breach: any single perimeter check will eventually fail or be bypassed.
3. Every input is untrusted; every permission boundary must be verified with proof.
4. Fail closed: errors, missing libraries, or exceptions must deny access, never grant it.
5. Concrete proofs only: vague warnings are prohibited. Every finding requires an exact file and line reference, a concise exploit scenario, and a concrete code fix.

## Methodology

When invoked on a target repository:

1. Reconnaissance and Platform Classification:
   - Identify application type: Web (SPA, SSR, REST/GraphQL), Mobile (Android, iOS, cross-platform), Desktop (Electron, Qt/PyQt, Tauri, native), or Backend/Daemon.
   - Detect tech stack, storage engines, auth mechanisms, and external services.

2. Attack Surfaces Audit (Execute in Strict Sequence):
   - Surface 01: Secrets and Credentials
   - Surface 02: Database and Storage Security
   - Surface 03: Authentication and Access Control
   - Surface 04: AI, LLM, and Agentic Pipelines
   - Surface 05: Webhooks, Network Egress, and IPC
   - Surface 06: Dependencies, Build Scripts, and Supply Chain
   - Surface 07: Logging, Telemetry, and PII Exposure
   - Surface 08: Platform-Specific Sandboxing and Storage (Mobile/Desktop)

3. Deep-Dive Domain Inspections:
   - For Web and API architectures: load [references/web_and_api.md](file:///h:/Projects/Wiz/.agents/skills/red-team-audit/references/web_and_api.md)
   - For Mobile and Desktop architectures: load [references/mobile_and_desktop.md](file:///h:/Projects/Wiz/.agents/skills/red-team-audit/references/mobile_and_desktop.md)
   - For Cloud, Supply Chain, and AI/LLM architectures: load [references/ai_and_cloud.md](file:///h:/Projects/Wiz/.agents/skills/red-team-audit/references/ai_and_cloud.md)

4. Finding Synthesis and Remediation:
   - Classify findings into Critical, High, Medium, Low.
   - Rank findings strictly by severity.
   - Present findings in the standardized findings table.
   - Summarize the top 3 urgent fixes to execute immediately.

## Standardized Output Format

Always return audit results using this markdown table schema:

| Severity | File:line | Vulnerability | Exploit scenario (1-2 sentences) | Fix (concrete code change) |

Rules for output:
- Severity values allowed: Critical, High, Medium, Low.
- File:line must link to the exact file path and line number.
- Exploit scenario must describe how an adversary leverages the flaw in 1-2 clear sentences.
- Fix must provide the exact replacement code or logic.
- Conclude with a "Top 3 things to fix today" summary.

## Exit Criteria

- [ ] All 8 attack surfaces examined across the target codebase.
- [ ] Every finding has an exact file:line reference and verified exploit scenario.
- [ ] Every finding provides a concrete code fix rather than generic advice.
- [ ] Findings table is sorted strictly from highest severity to lowest severity.
- [ ] Top 3 immediate remediation items are clearly highlighted.
