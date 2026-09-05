---
name: codebase-cleanup
description: >
  Conducts a code quality, maintainability, and dead-code audit to optimize codebases,
  consolidate duplicate logic, eliminate redundant queries, and safely remove dead code.
  Use when preparing for a release or packaging (e.g. into an .exe or binary), when auditing
  for technical debt, or when asked to clean up, optimize, or review a codebase for dead code.
---

# Codebase Cleanup & Maintainability Audit

A systematic, aggressive yet safe framework for senior software engineers and coding agents to audit, optimize, and strip dead weight from any software project. It identifies unused code, duplicate abstractions, redundant I/O, orphaned UI elements, and packaging blockers without breaking existing functionality.

## Core Principles

1. **Safety First**: Never delete code without verifying who was supposed to call it, why it was introduced, and whether tests or dynamic lookups rely on it.
2. **Establish Baseline First**: Run the existing test suite and verify working behavior before proposing or applying deletions.
3. **Structured Evidence**: Every finding must cite exact file paths, line numbers, why it is unnecessary, impact estimation, pre-deletion risk, and an actionable cleanup plan.
4. **Aggressive but Safe**: Eliminate bloat, but preserve intentional extension points that are documented or tested.
5. **Zero Regressions**: The cleanup is only successful if 100% of baseline tests continue to pass and application behavior is preserved.

---

## The 8 Review Dimensions

Every audit MUST analyze the codebase across these 8 dimensions:

### 1. Dead Code
- Unused functions, classes, methods, and variables.
- Dead imports and unreferenced third-party dependencies in manifest files.
- Unconnected or never-emitted event signals, hooks, or callbacks.
- Unreferenced database schemas, tables, or columns.

### 2. Duplicate Logic
- Copy-pasted widgets, components, or UI styling strings.
- Redundant helper functions that duplicate existing utilities or standard library features.
- Repeated interaction patterns (e.g. frameless dragging, drop shadows, modal setup).

### 3. Unused UI Components & Assets
- Orphaned UI widgets, dialogs, or subcomponents.
- Unused asset files (images, duplicate SVGs, deprecated icons).
- Unreferenced CSS/QSS styles and dead style constants.

### 4. Overly Complex Implementations
- Monolithic files (>1,000 LOC containing multiple distinct classes or concerns).
- Convoluted control flow or nested callback hell that can be flattened.
- Over-engineered abstractions with only one consumer (YAGNI).

### 5. Legacy & Transitory Code
- Deprecated backward-compatibility shims that are no longer needed.
- Stub placeholders, leftover migration scripts, and forgotten debug routines.

### 6. Redundant Database Queries & I/O Calls
- High-frequency polling loops running un-cached database queries.
- N+1 query patterns in data-fetching methods.
- Synchronous disk or network I/O executed on UI/main threads.

### 7. Abandoned or Disconnected Files
- Generic template files, prompt scaffoldings, and leftover boilerplate.
- Abandoned prototypes, scratch scripts, and unreferenced assets.

### 8. Technical Debt & Release / Packaging Readiness
- Path resolution issues under compiled or bundled environments (e.g. `sys._MEIPASS` in PyInstaller).
- Separation of runtime dependencies vs dev/test tooling.
- Hardcoded constants that belong in configuration.

---

## Audit & Execution Workflow

```
[Phase 1: Recon & Test Baseline]
              ↓
[Phase 2: 8-Dimension Static & Architectural Scan]
              ↓
[Phase 3: Structured Findings Report & Risk Assessment]
              ↓
[Phase 4: Phased Safe Execution & Refactoring]
              ↓
[Phase 5: Zero-Regression Verification Gate]
```

### Phase 1 — Recon & Verification Baseline
1. Identify project type, language, package manager, and entry point.
2. Execute existing automated tests (`pytest`, `npm test`, `cargo test`, `go test`, etc.).
3. Record the pass/fail baseline. If tests fail initially, document the pre-existing failures before modifying any files.

### Phase 2 — Static & Architectural Scan
1. Sweep codebase across all 8 dimensions using search tools (`grep_search`), AST inspection, or linters.
2. Cross-reference symbols: For every suspected dead function or variable, search the entire repository for dynamic or string-based references (e.g., config files, reflection, signal connections).
3. Check I/O hot loops: Inspect background workers, timers, and event loops for repeated database or disk access.

### Phase 3 — Deliver Structured Findings Report
For each identified issue, provide the mandatory 4-part assessment:
- **Why it is unnecessary**: Explain why the code exists and why it provides no value.
- **Estimated impact**: Quantify LOC reduction, memory savings, CPU/disk I/O reduction, or bundle size improvement.
- **Pre-deletion risks**: Identify potential regressions, hidden callers, or edge cases.
- **Recommended cleanup plan**: Step-by-step instructions for safe removal or refactoring.

Consult [references/review-template.md](references/review-template.md) for the exact markdown layout.

### Phase 4 — Phased Safe Execution
When approved to execute:
1. **Tier 1 (Safe Surgical Deletions)**:
   - Remove dead imports, unreferenced constants, and unused private stubs.
   - Delete abandoned template files and duplicate assets.
2. **Tier 2 (Deduplication & Consolidation)**:
   - Consolidate duplicate widgets and styling into shared modules.
   - Replace redundant helpers with standard library or centralized utilities.
3. **Tier 3 (I/O & Architecture Optimization)**:
   - Add in-memory caching to hot polling loops.
   - Batch database queries to eliminate N+1 patterns.
   - Debounce or delegate synchronous I/O off the UI thread.
4. **Tier 4 (Packaging & Environment Fixes)**:
   - Ensure asset paths resolve correctly in bundled/executable environments (e.g., PyInstaller `sys._MEIPASS`).
   - Clean manifest dependencies (e.g., separate `requirements.txt` from `requirements-dev.txt`).

### Phase 5 — Zero-Regression Verification Gate
1. Re-run the full test suite.
2. Verify that 100% of baseline tests pass.
3. Validate that interactive flows (CLI, UI, or API endpoints) operate identically with reduced latency and cleaner logs.

---

## Exit Criteria

- [ ] Baseline test suite executed and documented before changes.
- [ ] All 8 review dimensions systematically analyzed with exact file and line references.
- [ ] Every finding formatted with: Why Unnecessary, Impact, Pre-Deletion Risks, and Cleanup Plan.
- [ ] All deletions and refactorings executed in safe, incremental tiers.
- [ ] 100% of automated tests pass post-cleanup with zero regressions.
- [ ] Application verified for release, packaging, or compilation.
