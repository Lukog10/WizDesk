# WizDesk Security Policy and Threat Model

## Overview
WizDesk is a local-first, offline desktop productivity companion application designed for Windows with cross-platform architecture considerations. This document defines the threat model, attack surface boundaries, security guarantees, vulnerability reporting procedures, and red-team audit findings.

---

## Security Guarantees
1. **Zero External Network Egress**: WizDesk operates completely locally. No telemetry, user notes, application sessions, or credentials are ever transmitted across the network.
2. **Authenticated Encryption at Rest**: When enabled, the database is encrypted with AES-256-GCM. Decryption and key verification occur strictly in memory.
3. **Hardware and OS-Backed Key Storage**: Master encryption keys are protected on Windows using DPAPI (Data Protection API) bound to the active user login.
4. **Identity-Bound Privilege Gates**: Access to view or export private recovery keys requires native Windows credential authentication through CredUI and LogonUser, strictly validating the active logon identity.
5. **Fail-Closed Execution**: Authentication errors, missing security libraries, or decryption failures immediately fail closed. Corrupt or unreadable encrypted data is never overwritten with blank state.
6. **Privacy-Preserving Telemetry**: Active window tracking applies automatic redaction for password managers, financial institutions, private browsing modes, and confidential seed phrases.

---

## Attack Surface Analysis (8 Domains)

### Surface 01: Secrets and Credentials
- **Finding**: OS clipboard indefinitely retained the 256-bit master recovery key after user copied it from the settings modal.
- **Remediation**: Implemented an automated 45-second timer that purges the key from the OS clipboard if it has not been overwritten.
- **Status**: Mitigated and verified.

### Surface 02: Database and Storage Security
- **Design**: SQLite database is serialized and encrypted with AES-256-GCM authenticated encryption using atomic temporary file swaps and disk sync flushes.
- **Remediation**: In-memory database serialization prevents writing cleartext SQLite files to disk. Decryption failures preserve unreadable copies and abort disk writeback.
- **Status**: Verified.

### Surface 03: Authentication and Access Control
- **Finding**: CredUI authentication verified credentials via LogonUser but did not verify that the authenticated username matched the active Windows user, allowing another valid account on a shared PC to authorize. Plaintext password buffers on the ctypes heap were not cleared in the cleanup block.
- **Remediation**: Added explicit comparison between the CredUI user and the active session login (os.environ USERNAME). Added memory zeroization (ctypes.memset) in the finally block.
- **Status**: Mitigated and verified.

### Surface 04: AI, LLM, and Agentic Pipelines
- **Analysis**: WizDesk contains no external cloud LLM connections, API keys, prompt injection vectors, or autonomous external agent pipelines.
- **Status**: Verified inert (no external AI attack surface).

### Surface 05: Webhooks, Network Egress, and IPC
- **Analysis**: Single-instance enforcement uses a local Qt named pipe (QLocalServer). No network sockets or HTTP endpoints are opened.
- **Status**: Verified local-only.

### Surface 06: Dependencies, Build Scripts, and Supply Chain
- **Finding**: PyInstaller specification hiddenimports omitted win32crypt, win32security, and cryptography, creating a risk that packaged binaries would fail closed or fail back to non-DPAPI storage.
- **Remediation**: Added win32crypt, win32security, cryptography, and AEAD primitive packages to hiddenimports in wizdesk.spec.
- **Status**: Mitigated and verified.

### Surface 07: Logging, Telemetry, and PII Exposure
- **Finding**: Modern password managers (Proton Pass, RoboForm) and cryptocurrency security keywords (seed phrase, private key, recovery phrase) were missing from the window title redaction filter.
- **Remediation**: Expanded PASSWORD_MANAGER_APPS and SENSITIVE_TITLE_KEYWORDS in wiz/utils/sanitizer.py.
- **Status**: Mitigated and verified.

### Surface 08: Platform-Specific Sandboxing and Storage
- **Finding**: The sync_note function in wiz/sync/obsidian.py wrote markdown note exports to disk without checking if database encryption was enabled, creating an unintended cleartext data leak.
- **Finding**: Development autostart launch command used raw string interpolation for project root.
- **Remediation**: Added encryption checks to sync_note requiring explicit user opt-in (allow_plaintext_obsidian_sync). Escaped project root in autostart using repr.
- **Status**: Mitigated and verified.

---

## Standardized Red-Team Audit Findings

| Severity | File:line | Vulnerability | Exploit scenario (1-2 sentences) | Fix (concrete code change) |
| :--- | :--- | :--- | :--- | :--- |
| High | [wiz/sync/obsidian.py:136](file:///H:/Projects/Wiz/wiz/sync/obsidian.py#L136) | Unchecked Cleartext Note Export in Encrypted Mode | When a user enables database encryption, calling sync_note wrote raw note markdown files to disk without verifying encryption_enabled or opt-in, bypassing encryption at rest. | Added guard blocking sync_note when encryption is active unless allow_plaintext_obsidian_sync is explicitly enabled. |
| Medium | [wiz/utils/auth.py:141](file:///H:/Projects/Wiz/wiz/utils/auth.py#L141) | Missing Caller Identity Validation in Credential Authorization | On a shared Windows workstation, LogonUser validated any valid local user entered into CredUI, allowing a secondary local account to authorize viewing the private key. | Added validation checking that the entered username matches the active session username. |
| Medium | [wiz/utils/auth.py:155](file:///H:/Projects/Wiz/wiz/utils/auth.py#L155) | Cleartext Password Retention in Process Memory Heap | Plaintext Windows credentials in the ctypes buffer remained in process heap memory after authentication. | Added ctypes.memset zeroization to wipe password_buf in the finally block. |
| Medium | [wiz/ui/settings_view.py:106](file:///H:/Projects/Wiz/wiz/ui/settings_view.py#L106) | Unbounded Master Key Persistence in OS Clipboard | Copying the master key placed the 256-bit recovery key in the clipboard indefinitely, allowing background clipboard monitors to harvest it. | Added an automatic 45-second timer that purges the master key from the clipboard. |
| Low | [wiz/core/autostart.py:32](file:///H:/Projects/Wiz/wiz/core/autostart.py#L32) | Raw String Interpolation in Windows Run Registry Launch Command | Development autostart registration interpolated project root into python command without quote escaping. | Escaped project root using repr(str(project_root)). |
| Low | [wizdesk.spec:16](file:///H:/Projects/Wiz/wizdesk.spec#L16) | Missing Security Modules in PyInstaller Spec hiddenimports | Frozen executables could omit win32crypt and win32security, causing key export or DPAPI failures in standalone builds. | Explicitly added win32crypt, win32security, and cryptography to hiddenimports. |
| Low | [wiz/utils/sanitizer.py:5](file:///H:/Projects/Wiz/wiz/utils/sanitizer.py#L5) | Missing Password Managers and Sensitive Crypto Keywords in Redaction Filter | Windows with titles containing seed phrase, recovery phrase, or Proton Pass were not masked before recording to the database. | Expanded PASSWORD_MANAGER_APPS and SENSITIVE_TITLE_KEYWORDS with modern managers and crypto terms. |

---

## Top 3 Things Fixed
1. **Protected Note Sync against Encryption Bypass**: Prevented sync_note from exporting cleartext markdown files to the Obsidian vault when database encryption is enabled.
2. **Hardened Windows Credential Authentication**: Enforced active-user identity verification in CredUI and zeroized plaintext password buffers in memory using ctypes.memset.
3. **Auto-Purged Sensitive Recovery Key from Clipboard**: Added automatic 45-second clipboard clearing in KeyDisplayDialog to prevent clipboard harvesting.

---

## Vulnerability Reporting
To report a security vulnerability in WizDesk, submit a private advisory through the GitHub repository or contact the project maintainers directly. Do not file public issues for unpatched security defects.
