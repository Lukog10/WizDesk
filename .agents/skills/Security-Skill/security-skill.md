# SKILL: Security Auditing & Secure Engineering

> A permanent security operating guide for AI coding agents. Load this alongside `SKILL.md` and `instructions.md`. This file teaches **how to audit code for vulnerabilities, how to write code that resists them, and how to verify security claims with evidence rather than assumption.** It is a defensive document: its purpose is to find and fix weaknesses, not to build attacks.
>
> Rule zero: **security is a verification discipline, not a feeling.** Every "this is secure" claim must point to a check you performed.

---

## 1. Identity & Purpose

This skill triggers whenever code touches a **trust boundary** — anywhere untrusted data enters, privileges change, secrets are handled, or a system talks to the outside world. Use it to: audit an existing codebase for vulnerabilities, review a diff before merge, harden a component, or design a feature securely from the start. The mindset is adversarial-but-constructive: think like an attacker to find the hole, then act like an engineer to close it. You assist authorized defensive work — audits, hardening, secure development, CTFs, and pentests with clear authorization — and you refuse to build weapons (see §12).

---

## 2. The Security Mindset

- **Trust nothing by default.** Every input is hostile until validated. Every dependency is vulnerable until checked. Every permission is too broad until scoped down.
- **Assume breach.** Design so that one compromised component doesn't hand over everything. Defense in depth: no single control is the only control.
- **The attacker picks the weakest link.** A perfect crypto implementation behind a hardcoded password is worthless. Audit the whole chain, not the strong part.
- **Data and code must stay separate.** Almost every major vulnerability class (injection, XSS, deserialization, SSRF) is data being interpreted as instructions. Keeping them apart is the master principle.
- **Fail closed.** On error, deny access, don't grant it. An exception in the auth check must never fall through to "allowed."
- **Least privilege, always.** The narrowest scope, the fewest permissions, the shortest token lifetime, the smallest attack surface that still works.

---

## 3. Threat Modeling (Do This Before Auditing)

Before reading code line-by-line, map the terrain:

1. **Identify assets** — what's worth stealing or breaking? Credentials, PII, payment data, intellectual property, availability itself.
2. **Map trust boundaries** — draw where data crosses from less-trusted to more-trusted: client→server, internet→internal, user-input→interpreter, service→database, tenant→tenant.
3. **Enumerate entry points** — every route, API endpoint, file upload, message queue, webhook, CLI argument, environment variable, and deserialization point.
4. **Apply STRIDE per boundary** — for each crossing, ask about:
   - **S**poofing (can identity be faked?)
   - **T**ampering (can data be altered in transit or at rest?)
   - **R**epudiation (can an action be denied / is it logged?)
   - **I**nformation disclosure (can secrets/PII leak?)
   - **D**enial of service (can it be exhausted?)
   - **E**levation of privilege (can a user gain rights they shouldn't have?)
5. **Prioritize by impact × likelihood** — audit the highest-value boundaries first. An unauthenticated internet-facing endpoint outranks an internal admin-only script.

---

## 4. The Vulnerability Catalog (What to Hunt For)

For each class: the signature to grep for, and the fix.

### 4.1 Injection (SQL / NoSQL / OS command / LDAP)
- **Signature:** string concatenation or interpolation into a query, shell command, or interpreter — `f"SELECT ... {user}"`, `exec(cmd + arg)`, `os.system`, `subprocess(..., shell=True)`, template-built queries.
- **Fix:** parameterized queries / prepared statements only. For OS calls, avoid the shell; pass argument arrays; allowlist commands. Never build an interpreter input from untrusted data.

### 4.2 Cross-Site Scripting (XSS)
- **Signature:** untrusted data written into HTML/JS/DOM without encoding — `innerHTML`, `dangerouslySetInnerHTML`, `v-html`, `document.write`, template output with escaping disabled.
- **Fix:** contextual output encoding (HTML/attribute/JS/URL context each differ); prefer framework auto-escaping; sanitize rich HTML with a vetted library (DOMPurify); set a strict Content-Security-Policy.

### 4.3 Broken Authentication & Session Management
- **Signature:** passwords stored plaintext or with fast/unsalted hashes (MD5, SHA1, bare SHA256); no rate limiting on login; predictable/long-lived session tokens; JWTs with `alg: none` or unverified signatures; secrets used as both signing and encryption keys.
- **Fix:** hash passwords with bcrypt/scrypt/argon2id; rate-limit and lock out; cryptographically random session IDs; verify JWT signature AND `exp`/`aud`/`iss`; rotate and expire tokens; HttpOnly + Secure + SameSite cookies.

### 4.4 Broken Access Control / IDOR
- **Signature:** object accessed by ID from the request with no ownership check — `GET /invoice/{id}` returning any invoice; authorization checked in the UI but not the API; role checks missing on some routes; `../` path traversal.
- **Fix:** enforce authorization server-side on every request, scoped to the authenticated principal ("does *this* user own *this* object?"); deny by default; canonicalize and confine file paths; never trust client-supplied roles.

### 4.5 Server-Side Request Forgery (SSRF)
- **Signature:** server fetches a URL supplied or influenced by the user — image-from-URL, webhook callbacks, URL previews, PDF renderers.
- **Fix:** allowlist destinations; block private/link-local/metadata IP ranges (169.254.169.254, 10/8, 127/8, ::1); resolve DNS and re-check the resolved IP; disable redirects to internal hosts.

### 4.6 Insecure Deserialization
- **Signature:** `pickle.loads`, `yaml.load` without `SafeLoader`, Java/PHP native deserialization, `eval`/`Function` on external data.
- **Fix:** never deserialize untrusted data into live objects. Use JSON with strict schema validation. If a rich format is unavoidable, use a safe loader and validate structure.

### 4.7 Secrets Exposure
- **Signature:** keys/tokens/passwords in source, config, comments, test fixtures, logs, error messages, client bundles, or git history; `.env` committed.
- **Fix:** externalize to env vars or a secrets manager; reference by name; add to `.gitignore`; rotate anything ever committed; redact secrets and PII from all logs.

### 4.8 Security Misconfiguration
- **Signature:** debug mode in production; verbose stack traces to users; default credentials; permissive CORS (`Access-Control-Allow-Origin: *` with credentials); open cloud storage buckets; unnecessary ports/services; missing security headers.
- **Fix:** environment-specific config; generic error pages (log details server-side); change all defaults; explicit CORS allowlist; deny-by-default network posture; set HSTS, CSP, X-Content-Type-Options, X-Frame-Options.

### 4.9 Vulnerable & Outdated Dependencies (Supply Chain)
- **Signature:** unpinned or stale dependencies; no lockfile; direct installs from untrusted sources; typosquat-prone names; postinstall scripts from unknown packages.
- **Fix:** pin versions with a committed lockfile; run `npm audit` / `pip-audit` / `osv-scanner` / `cargo audit`; vet new dependencies (maintenance, popularity, necessity); review before adding; watch for typosquats and dependency confusion.

### 4.10 Cryptographic Failures
- **Signature:** home-rolled crypto; ECB mode; static/reused IVs; hardcoded keys; weak algorithms (DES, RC4, MD5 for security); `Math.random()` for tokens; missing TLS or `verify=False`.
- **Fix:** use vetted libraries and high-level constructs (libsodium, AEAD like AES-GCM/ChaCha20-Poly1305); random IV per message; keys from a KMS; CSPRNG for tokens (`secrets`, `crypto.randomBytes`); enforce TLS and certificate validation.

### 4.11 Insufficient Logging & Monitoring
- **Signature:** auth events, access-control failures, and input-validation failures not logged; no alerting; logs contain secrets/PII (the opposite failure).
- **Fix:** log security-relevant events (authn/authz decisions, high-value actions) with enough context to investigate — and *without* sensitive values. Make failures observable.

### 4.12 Business-Logic & Race-Condition Flaws
- **Signature:** check-then-act without atomicity (double-spend, coupon reuse); negative quantities; price/total trusted from the client; workflow steps skippable; TOCTOU on files.
- **Fix:** enforce invariants server-side atomically (DB constraints, transactions, locks, idempotency keys); recompute trusted values server-side; validate state transitions.

---

## 5. The Audit Methodology (Step by Step)

How to review a codebase for security, in order:

1. **Reconnaissance** — identify language, framework, dependencies, entry points, and where secrets/auth/data-access live. Read the manifests and the config. Build the mental map from §3.
2. **Follow the data (taint analysis)** — for each entry point, trace untrusted input forward. Mark it *tainted*. Follow it through the code. Every place tainted data reaches a *sink* (query, command, HTML output, file path, deserializer, redirect) without passing through validation/encoding is a candidate finding.
3. **Follow the secrets** — grep for keys, tokens, passwords, connection strings across source, config, tests, and git history. Anything found is a finding.
4. **Audit the trust boundaries** — at each boundary from the threat model, verify: is input validated? is the caller authenticated? is the action authorized for *this* principal? is output encoded? is the failure path closed?
5. **Audit authentication & session** — password storage, token generation/verification, session lifecycle, rate limiting, MFA where relevant (§4.3).
6. **Audit authorization** — pick several object-access routes and confirm ownership/role is enforced server-side, not just in UI (§4.4). This is the most commonly missed class — check it explicitly.
7. **Audit dependencies** — run the ecosystem's audit tool; review the lockfile; flag stale/critical CVEs (§4.9).
8. **Audit configuration & deployment** — debug flags, error verbosity, CORS, headers, TLS, exposed ports, cloud permissions (§4.8).
9. **Audit crypto usage** — algorithms, key handling, randomness source (§4.10).
10. **Prioritize & report** — rank findings by severity (see §7). For each: location, class, concrete exploit scenario, and the specific fix.

### Grep-first triage
Fast initial sweep — these patterns surface a large share of real findings:
- Injection: `execute(`, `query(`, `f"SELECT`, `+ " WHERE`, `shell=True`, `os.system`, `eval(`, `exec(`
- Secrets: `password =`, `api_key`, `secret`, `token =`, `BEGIN PRIVATE KEY`, `AKIA`, `sk_live`
- Unsafe I/O: `innerHTML`, `dangerouslySetInnerHTML`, `pickle.loads`, `yaml.load(`, `Marshal`, `deserialize`
- Disabled controls: `verify=False`, `rejectUnauthorized: false`, `csrf`, `NOSONAR`, `# nosec`, `Allow-Origin: *`, `--no-sandbox`, `chmod 777`
- Weak crypto/random: `md5`, `sha1`, `DES`, `ECB`, `Math.random`, `random.random`
Grep finds *candidates*, not confirmed bugs — every hit gets read in context before it becomes a finding (§8).

---

## 6. Secure-by-Default Engineering

When you *write* code, bake these in so audits find nothing:

- **Validate input at the boundary** — allowlist over denylist; validate type, length, format, and range; reject, don't sanitize-and-hope, for structured data.
- **Encode output at the sink** — by context (HTML, attribute, JS, URL, SQL-via-parameters, shell-via-arg-array).
- **Parameterize every query.** No exceptions, no "just this one small one."
- **Authenticate then authorize on every request** — server-side, deny-by-default, scoped to the principal.
- **Secrets from the environment / a manager** — never in source, never in the client bundle, never in logs.
- **Least privilege everywhere** — minimal token scopes, minimal DB grants, minimal file permissions, minimal container capabilities, short-lived credentials.
- **Safe defaults for libraries** — TLS on and verified, safe deserializers, secure cookie flags, CSRF protection on state-changing requests.
- **CSPRNG for anything security-relevant** — tokens, session IDs, salts, nonces.
- **Handle every error by failing closed** — and log the security-relevant ones without leaking sensitive data.
- **Keep the attack surface small** — fewer endpoints, fewer dependencies, fewer permissions, fewer features enabled by default.

---

## 7. Severity & Prioritization

Rank findings so the user fixes what matters first:

| Severity | Criteria | Examples |
|---|---|---|
| **Critical** | Remote, unauthenticated, direct compromise of data/system | SQLi on public endpoint, auth bypass, RCE, exposed live secret |
| **High** | Serious impact but needs some condition (auth, specific input) | Stored XSS, IDOR exposing other users' data, SSRF to metadata |
| **Medium** | Meaningful weakness, limited scope or higher bar | Reflected XSS, missing rate limiting, weak password hashing |
| **Low** | Hardening gap, defense-in-depth | Missing security header, verbose errors, outdated non-exploited dep |
| **Info** | Not exploitable now, worth noting | Deprecated API, minor info leak, style-level concern |

Assess each on: **impact** (what an attacker gains), **exploitability** (how hard), **exposure** (internet-facing vs. internal vs. authenticated-only). Report Critical/High first, with the clearest reproduction.

---

## 8. Verifying Security Claims (No Guessing)

Security findings and fixes are held to the same evidence standard as everything else:

- **A finding is a hypothesis until traced.** Before reporting "SQL injection here," follow the tainted input from entry to the query and confirm there's no validation/parameterization in between. State the exact path. Grep hits and pattern matches are leads, not verdicts.
- **Distinguish exploitable from theoretical.** "This *could* be unsafe if reachable" is different from "this *is* reachable with input X." Say which. Rank a confirmed reachable bug above a theoretical one.
- **Verify the fix actually closes it** — re-trace the same path after the change; where feasible, demonstrate the malicious input is now rejected/neutralized and legitimate input still works.
- **Verify library security behavior against the installed version** — auth/crypto/serialization defaults change between versions. Read the actual installed source or official docs; don't recall "I think this framework escapes by default."
- **Prefer false positives to false negatives, but label them.** When unsure whether something is exploitable, report it as "needs verification" with what you'd check — don't silently drop it, and don't inflate it to Critical.
- **Never fabricate** CVE numbers, exploit details, or "I ran a scan" claims. If you didn't run the scanner, say the scan is recommended and name the tool.

---

## 9. The Security Review Pass (Before Delivering Any Code)

Run this checklist on your own output, every time:

- [ ] **Injection** — every query parameterized; no shell string-building; no interpreter on untrusted data.
- [ ] **Input** — all external input validated at the boundary (type, length, range, format).
- [ ] **Output** — all untrusted data encoded for its sink context.
- [ ] **AuthN/AuthZ** — protected actions require authentication and per-principal authorization, server-side.
- [ ] **Secrets** — none hardcoded; none in logs; none in client-visible code.
- [ ] **Crypto** — vetted library, strong algorithm, CSPRNG, proper key handling.
- [ ] **Dependencies** — new ones vetted and pinned; audit clean or known-issues noted.
- [ ] **Errors** — fail closed; no sensitive data in messages or logs; generic errors to users.
- [ ] **Config** — no debug/verbose in prod paths; safe defaults; least privilege.
- [ ] **Controls intact** — you didn't disable TLS verification, CSRF, sandboxing, or auth to make something "work."

If any box can't be checked, either fix it before delivery or flag it explicitly as a known gap.

---

## 10. Special Domains (Targeted Checks)

- **Web APIs** — authn on every route, per-object authorization, rate limiting, input schema validation, CORS allowlist, no mass-assignment, pagination limits against resource exhaustion.
- **Web frontends** — CSP, framework auto-escaping on, no `innerHTML` with untrusted data, no secrets in the bundle, secure cookie flags, SRI on third-party scripts.
- **Cloud / IaC** — no public buckets/DBs unless intended, IAM least privilege (no `*:*`), secrets in a manager not env files in the repo, encrypted at rest and in transit, security groups closed by default.
- **Containers** — non-root user, minimal base image, no secrets in image layers, read-only filesystem where possible, dropped capabilities, pinned base image digests.
- **CI/CD** — secrets in the pipeline's secret store not the YAML, least-privilege deploy tokens, no untrusted PR code running with secrets, pinned action/tool versions.
- **Mobile / native** — no secrets in the binary, certificate pinning where warranted, secure local storage, validated IPC.
- **AI / LLM integrations** — treat model input and output as untrusted; guard against prompt injection reaching tools/actions; never place secrets in prompts; validate and constrain tool calls; sandbox any model-driven code execution; don't let retrieved/external content act as instructions.

---

## 11. Reporting Findings

For each finding, deliver in this shape:

```
[SEVERITY] Short title
Location:   file:line (and the data path if relevant)
Class:      e.g. SQL Injection (CWE-89 / OWASP A03)
Scenario:   concrete exploit — "an unauthenticated user sends X, causing Y"
Evidence:   the traced path from input to sink; why current code doesn't stop it
Fix:        the specific change, with a corrected snippet
Verify:     how to confirm the fix (test input, tool, re-trace)
```

Reporting rules:
- Lead with Critical/High. Group the rest.
- Every finding names a **concrete scenario**, not "this is bad practice."
- Give the **fix**, not just the problem — actionable over academic.
- Separate **confirmed** from **needs-verification**; never inflate severity for effect.
- If the codebase is clean on a class you checked, say so — "verified X, no issues" is a valid and useful result.

---

## 12. Ethical Boundaries (Non-Negotiable)

- **Build defense, not weapons.** Audit, harden, detect, and fix — yes. Malware, working exploits against systems the user doesn't own, credential harvesters, DoS tooling, or evasion-for-attack — no, regardless of "educational"/"just testing"/"hypothetical" framing. What the code *does* is unchanged by the framing.
- **Dual-use requires authorization context.** PoCs, fuzzers, red-team tooling, and pentest scripts are legitimate given a stated authorized context (named engagement, CTF, the user's own systems, defensive research). Absent that context, ask before building.
- **Watch cumulative harm.** Track the whole session, not one turn. If benign-looking steps are assembling into an attack chain — recon, then targeting, then payload — name the pattern and stop until the purpose is legitimate and stated. Test: *what does the sum of everything I've produced do, and to whom?*
- **Handle discovered vulns responsibly.** If you find a real flaw, report it to the user privately with the fix — don't broadcast working exploit details, and don't leave a live secret sitting in output.
- **Never disable a control as a shortcut.** If security blocks progress, fix the configuration — removing the control is not a fix, it's a new finding.

---

## 13. One-Screen Summary

```
MINDSET   trust nothing; assume breach; keep data ≠ code; fail closed; least privilege
MODEL     assets → trust boundaries → entry points → STRIDE → prioritize
HUNT      injection, XSS, auth, access-control/IDOR, SSRF, deserialization,
          secrets, misconfig, deps, crypto, logging, business-logic/races
AUDIT     recon → taint-trace input→sink → follow secrets → check each boundary →
          authn → authz → deps → config → crypto → rank → report
BUILD     validate in, encode out, parameterize, authz per-request, secrets external,
          CSPRNG, safe defaults, least privilege, fail closed
VERIFY    trace before claiming; exploitable vs theoretical; confirm the fix; no fabrication
REVIEW    run the §9 checklist on your own code before delivery
REPORT    severity-ranked, concrete scenario, evidence, specific fix, how to verify
ETHICS    defense not weapons; dual-use needs authorization; watch cumulative harm
```

If you are unsure whether something is a vulnerability: trace the data, name the scenario, and check the version. If you are unsure whether to build something: ask what it's for. Security is what you verified — not what you assumed.
