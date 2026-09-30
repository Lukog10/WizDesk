# Mobile and Desktop Attack Surfaces

This reference defines attack vectors for Mobile platforms (Android, iOS, React Native, Flutter) and Desktop environments (Electron, PyQt/PySide, Tauri, native Windows/macOS/Linux).

## 1. Secrets and Binary Hardcoding
- Scan mobile asset directories, strings.xml, Info.plist, and compiled native binaries for hardcoded API secrets and signing keys.
- Decompilation readiness: assume APKs, IPAs, and desktop bundles will be unpacked and reverse-engineered with Ghidra, Jadx, or strings utilities.
- Prohibit hardcoded master encryption keys, private certificates, or fallback passwords in source.

## 2. Platform Key Storage and Keystores
- Windows: verify DPAPI (`CryptProtectData`) protects master encryption keys. Check fallback paths: never write raw symmetric keys to unencrypted local files.
- macOS: verify Keychain Services (`SecItemAdd`, `SecItemCopyMatching`) are used for credential persistence.
- Linux: audit secret storage: use Secret Service API / libsecret / KWallet; avoid cleartext dotfiles.
- Android: ensure keys are generated and stored in the Android Keystore system (`KeyGenParameterSpec`, hardware-backed StrongBox / TEE).
- iOS: ensure credentials use the iOS Keychain with strict accessibility attributes (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`).

## 3. Local Databases and Cryptography at Rest
- Audit local SQLite, Realm, or IndexedDB storage: ensure sensitive tables and files are encrypted with authenticated encryption (AES-256-GCM, ChaCha20-Poly1305, or SQLCipher).
- Inspect memory management: audit whether plaintext databases are held in unpinned process RAM where core dumps, pagefiles, or memory scanners can extract sensitive data.
- Atomic file writes: ensure encrypted databases write via atomic replacement to prevent partial write corruption.
- Destructive fail-open prevention: verify that decryption failures never overwrite existing databases with blank schemas.

## 4. Native Authentication and IPC
- Credential prompts: ensure biometric prompts (FaceID, TouchID, Windows Hello, CredUI) fail closed on cancel, error, or missing system libraries.
- Inter-Process Communication (IPC):
  - Electron: audit `nodeIntegration` (must be `false`), `contextIsolation` (must be `true`), and preload script exposure.
  - Android: verify exported activities, services, content providers, and broadcast receivers in `AndroidManifest.xml` (`android:exported="false"` unless explicitly required, and protected with custom permissions).
  - Deep links and intent schemes: validate all incoming deep link parameters to prevent arbitrary URI execution or state manipulation.

## 5. Background Activity and OS Telemetry
- Active window / foreground tracking: sanitize window titles before logging to avoid recording password manager titles, banking records, private emails, or PII.
- Export synchronization: ensure synchronization features (such as Markdown or plaintext notes) never bypass database encryption by writing cleartext copies of encrypted data to disk.
- Unencrypted temporary files: verify that backup verification and temp operations do not leave unencrypted SQLite files on physical disks.
