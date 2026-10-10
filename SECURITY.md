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
- **Architecture**: Obsidian vault synchronization is intentionally designed as an unencrypted Markdown file bridge to external vaults. Because third-party markdown viewers (e.g. Obsidian) cannot parse encrypted blobs, WizDesk exports plaintext markdown files directly into the user-configured vault, while internal SQLite database storage remains encrypted with AES-256-GCM.
- **Finding**: Development autostart launch command used raw string interpolation for project root.
- **Remediation**: Escaped project root in autostart using repr(str(project_root)).
- **Status**: Mitigated and verified.

---

## Standardized Red-Team Audit Findings

| Severity | File:line | Vulnerability | Exploit scenario (1-2 sentences) | Fix (concrete code change) |
| :--- | :--- | :--- | :--- | :--- |
| High | [wiz/ui/settings_view.py:1020](file:///H:/Projects/Wiz/wiz/ui/settings_view.py#L1020) | Missing Privilege Gate on Database Decryption | An unauthorized user at an unattended terminal could click Disable Encryption and decrypt the entire database to cleartext on disk without entering credentials. | Enforced OS credential authentication (authenticate_user) before executing disable_encryption. |
| Medium | [wiz/__main__.py:29](file:///H:/Projects/Wiz/wiz/__main__.py#L29) | Cross-User Named Pipe Collision in Single-Instance IPC | On multi-user Windows hosts, multiple users shared the same named pipe, causing secondary logins to trigger the primary user instance and exit. | Scoped the single-instance named pipe to the active session username. |
| Medium | [wiz/utils/auth.py:144](file:///H:/Projects/Wiz/wiz/utils/auth.py#L144) | Inflexible Identity Check on Domain and UPN Logins | Entering DOMAIN\user or user@domain into CredUI failed authentication against USERNAME even with valid credentials. | Added normalization to extract base username before comparing to active login. |
| Medium | [wiz/utils/auth.py:155](file:///H:/Projects/Wiz/wiz/utils/auth.py#L155) | Cleartext Password Retention in Process Memory Heap | Plaintext Windows credentials in the ctypes buffer remained in process heap memory after authentication. | Added ctypes.memset zeroization to wipe password_buf in the finally block. |
| Medium | [wiz/ui/settings_view.py:106](file:///H:/Projects/Wiz/wiz/ui/settings_view.py#L106) | Unbounded Master Key Persistence in OS Clipboard | Copying the master key placed the 256-bit recovery key in the clipboard indefinitely, allowing background clipboard monitors to harvest it. | Added an automatic 45-second timer that purges the master key from the clipboard. |
| Low | [wiz/sync/obsidian.py:145](file:///H:/Projects/Wiz/wiz/sync/obsidian.py#L145) | Unescaped Quotes and Newlines in YAML Frontmatter | Note titles or project tags containing quotes or newlines could corrupt YAML frontmatter in synced Obsidian notes. | Added escaping for quotes, backslashes, and line breaks in YAML frontmatter generation. |
| Low | [wiz/core/config.py:124](file:///H:/Projects/Wiz/wiz/core/config.py#L124) | Non-Atomic Configuration File Persistence | Process termination or power failure during config.json write could corrupt the file into a zero-byte invalid JSON state. | Implemented atomic temporary file writes with os.replace and os.fsync. |
| Low | [wiz/storage/backup.py:84](file:///H:/Projects/Wiz/wiz/storage/backup.py#L84) | Permissive Backup File Permissions on Shared Filesystems | Backup snapshot files created on disk used default umask without restrictive user-only access permissions. | Added explicit 0o600 file permission setting on created backups for POSIX environments. |
| Low | [wiz/core/autostart.py:32](file:///H:/Projects/Wiz/wiz/core/autostart.py#L32) | Raw String Interpolation in Windows Run Registry Launch Command | Development autostart registration interpolated project root into python command without quote escaping. | Escaped project root using repr(str(project_root)). |
| Low | [wizdesk.spec:16](file:///H:/Projects/Wiz/wizdesk.spec#L16) | Missing Security Modules in PyInstaller Spec hiddenimports | Frozen executables could omit win32crypt and win32security, causing key export or DPAPI failures in standalone builds. | Explicitly added win32crypt, win32security, and cryptography to hiddenimports. |
| Low | [wiz/utils/sanitizer.py:5](file:///H:/Projects/Wiz/wiz/utils/sanitizer.py#L5) | Missing Password Managers and Sensitive Crypto Keywords in Redaction Filter | Windows with titles containing seed phrase, recovery phrase, or Proton Pass were not masked before recording to the database. | Expanded PASSWORD_MANAGER_APPS and SENSITIVE_TITLE_KEYWORDS with modern managers and crypto terms. |

---

## Top 3 Things Fixed
1. **Privilege Gating on Database Decryption and Key Export**: Enforced OS credential authentication through CredUI before allowing master key viewing or database decryption in [wiz/ui/settings_view.py](file:///H:/Projects/Wiz/wiz/ui/settings_view.py#L1020).
2. **Hardened Windows Credential Authentication and Memory Zeroization**: Enforced active-user identity verification in CredUI with domain/UPN normalization and zeroized plaintext password buffers in memory using ctypes.memset in [wiz/utils/auth.py](file:///H:/Projects/Wiz/wiz/utils/auth.py#L155).
3. **Multi-User IPC Isolation and Atomic Storage Resilience**: Scoped local single-instance named pipes per-user in [wiz/__main__.py](file:///H:/Projects/Wiz/wiz/__main__.py#L29) and implemented crash-proof atomic persistence in [wiz/core/config.py](file:///H:/Projects/Wiz/wiz/core/config.py#L124).

---

## Vulnerability Reporting
To report a security vulnerability in WizDesk, submit a private advisory through the GitHub repository or contact the project maintainers directly. Do not file public issues for unpatched security defects.
