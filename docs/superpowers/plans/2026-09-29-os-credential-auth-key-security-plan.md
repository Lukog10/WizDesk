# Implementation Plan: OS Credential Authentication for Private Key Access

**Date**: 2026-09-29  
**Design Spec Reference**: [docs/superpowers/specs/2026-09-29-os-credential-auth-key-security-design.md](file:///h:/Projects/Wiz/docs/superpowers/specs/2026-09-29-os-credential-auth-key-security-design.md)  
**Status**: Ready for Execution  

---

## 1. Context Lock-in

- **TASK**: Implement operating system credential authentication (Windows PIN or account password prompt) before allowing users to view or export their AES-256 database private recovery key in WizDesk Settings.
- **INPUTS**:
  - Design Spec: `docs/superpowers/specs/2026-09-29-os-credential-auth-key-security-design.md`
  - Existing settings view: `wiz/ui/settings_view.py`
  - Windows API dependencies: `ctypes.windll.credui`, `ctypes.windll.ole32`, `win32security`
- **OUTPUTS**:
  - `wiz/utils/auth.py`: Central OS authentication utility supporting Windows CredUI and LogonUser verification with cross-platform fallback.
  - `wiz/ui/settings_view.py`: Gated `_on_view_private_key` that prompts for OS credentials before opening `KeyDisplayDialog`.
  - `tests/test_auth.py`: Comprehensive test suite for credential prompt states (success, cancellation, invalid password, resource cleanup).
  - Standalone PyInstaller rebuild in `dist/WizDesk/`.
- **CONSTRAINTS**:
  - Zero double dashes and zero em-dashes across all code, comments, and documentation.
  - Zero emojis across UI, code, and tests.
  - Complete memory safety with CoTaskMemFree for native credential buffers.
  - 100% test pass rate with zero regressions.
  - Clean commit of working tree before handoff.
- **SUCCESS CRITERIA**:
  - Clicking "View Private Key" triggers native Windows Security authentication modal.
  - Entering correct Windows credentials decrypts and displays the recovery key.
  - Cancelling the prompt or entering an incorrect password denies access without displaying the key.
  - Automated unit tests pass with mocked and functional API validations.

---

## 2. File Impact Analysis

| File | Nature of Change | Target Functionality | Verification Method |
| :--- | :--- | :--- | :--- |
| `wiz/utils/auth.py` | New file | OS credential prompt via `CredUIPromptForWindowsCredentialsW` and `win32security.LogonUser` | Unit test suite |
| `wiz/ui/settings_view.py` | Modify file | Connect `_on_view_private_key` to `authenticate_user()` before showing `KeyDisplayDialog` | Integration test and manual check |
| `tests/test_auth.py` | New file | Tests for success, cancellation, bad password, and memory cleanup | Pytest |
| `tests/test_sidebar_and_shell.py` | Modify file | Verify settings view key gate behavior | Pytest |
| `wizdesk.spec` | Verify build | Ensure `win32security` and `auth.py` bundle properly into standalone distribution | PyInstaller build |

---

## 3. Phased Implementation Tasks

### Phase 1: Create `wiz/utils/auth.py`
- [ ] Define `CREDUI_INFOW` structure and Win32 CredUI prototypes.
- [ ] Implement `_prompt_windows_credentials(parent_hwnd, title, message)`:
  - Invokes `CredUIPromptForWindowsCredentialsW` with generic and current user flags.
  - Unpacks credentials via `CredUnPackAuthenticationBufferW`.
  - Verifies logon session with `win32security.LogonUser()`.
  - Safely calls `ole32.CoTaskMemFree()` in a finally block.
- [ ] Implement public entrypoint `authenticate_user(parent_hwnd, title, message) -> bool`.
- [ ] Add non-Windows fallback stub for future Linux compatibility.

### Phase 2: Integrate OS Authentication into Settings View
- [ ] In `wiz/ui/settings_view.py`, import `authenticate_user` from `wiz.utils.auth`.
- [ ] In `_on_view_private_key()`:
  - Extract native window handle `int(self.window().winId())`.
  - Invoke `authenticate_user(parent_hwnd=parent_hwnd, ...)`.
  - If False, update status pill or show notification and return early.
  - If True, load DPAPI key and execute `KeyDisplayDialog`.

### Phase 3: Create Unit and Integration Tests
- [ ] Create `tests/test_auth.py` with mock tests:
  - Mock `CredUIPromptForWindowsCredentialsW` returning `ERROR_SUCCESS` and `LogonUser` returning valid token.
  - Mock cancellation returning `ERROR_CANCELLED` (1223).
  - Mock invalid credentials raising `win32security.error` 1326.
  - Verify buffer memory deallocation is always called.
- [ ] Update `tests/test_sidebar_and_shell.py` to test that `_on_view_private_key()` respects `authenticate_user` results.

### Phase 4: Validation, PyInstaller Packaging, and Commit
- [ ] Run full test suite (`pytest -v`).
- [ ] Rebuild standalone executable with PyInstaller.
- [ ] Commit changes with message: `feat: add os credential authentication for private recovery key`.
