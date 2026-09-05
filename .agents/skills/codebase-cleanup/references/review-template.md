# Code Quality & Maintainability Review Template

Use this template when producing reports for the `codebase-cleanup` skill.

---

# Code Quality & Maintainability Review: [Project Name]

**Reviewer:** Senior Software Engineer  
**Milestone / Objective:** [e.g., Version 1.0 Release / Windows .exe Packaging / Technical Debt Sprint]  
**Baseline Test Status:** [e.g., 28/28 tests passing (`pytest tests/ -v`)]

---

## Executive Summary

[2-3 paragraph overview of the current codebase health, major categories of waste identified (LOC reduction, I/O elimination, packaging blockers), and the overall impact of completing the cleanup.]

---

## 1. Dead Code

### Issue 1.1: [Short Title]
* **Location:** `[path/to/file.ext:line_number]`
* **Why Unnecessary:** [Explain why this code exists and why it is no longer used.]
* **Estimated Impact:** [e.g., Removes 30 lines of dead code, cleans namespace, prevents accidental invocation.]
* **Pre-Deletion Risks:** [e.g., Low. Verified no dynamic lookups or external package exports.]
* **Recommended Cleanup Plan:** [Actionable steps to safely delete the code.]

---

## 2. Duplicate Logic that Should Be Consolidated

### Issue 2.1: [Short Title]
* **Location:** `[file_a.ext:lines]` and `[file_b.ext:lines]`
* **Why Unnecessary:** [Explain the duplication and divergence risk.]
* **Estimated Impact:** [e.g., Eliminates 80 lines of duplicate drawing code, establishes single source of truth.]
* **Pre-Deletion Risks:** [e.g., Any slight differences in parameters or behavior between implementations.]
* **Recommended Cleanup Plan:** [How to extract a shared component/function and update callers.]

---

## 3. Unused UI Components & Assets

### Issue 3.1: [Short Title]
* **Location:** `[assets/image.png]` or `[path/to/component.ext]`
* **Why Unnecessary:** [Explain why this UI element or asset is orphaned.]
* **Estimated Impact:** [e.g., Reduces binary bundle size by 50KB, removes fallback conditionals.]
* **Pre-Deletion Risks:** [e.g., None, verified no string-based asset loading.]
* **Recommended Cleanup Plan:** [Deletion command and cleanup of reference logic.]

---

## 4. Overly Complex Implementations that Can Be Simplified

### Issue 4.1: [Short Title]
* **Location:** `[path/to/monolith.ext]`
* **Why Unnecessary:** [Describe why the complexity or file size is counter-productive.]
* **Estimated Impact:** [e.g., Decouples 11 classes into focused modules, enables faster imports and isolated unit testing.]
* **Pre-Deletion Risks:** [e.g., Circular imports or broken re-exports.]
* **Recommended Cleanup Plan:** [Step-by-step modularization or simplification plan.]

---

## 5. Legacy Code No Longer Needed

### Issue 5.1: [Short Title]
* **Location:** `[path/to/file.ext:lines]`
* **Why Unnecessary:** [Explain what past transition or temporary workaround produced this code.]
* **Estimated Impact:** [e.g., Removes obsolete fallback conditionals.]
* **Pre-Deletion Risks:** [e.g., Ensure all environments use the updated contract.]
* **Recommended Cleanup Plan:** [Removal and verification steps.]

---

## 6. Redundant Database Queries or I/O Calls

### Issue 6.1: [Short Title]
* **Location:** `[path/to/query_caller.ext:lines]`
* **Why Unnecessary:** [Detail the frequency and redundancy of the I/O operations.]
* **Estimated Impact:** [e.g., Eliminates 17,280 redundant SQLite queries per day, prevents UI stutter.]
* **Pre-Deletion Risks:** [e.g., Cache staleness; requires explicit cache invalidation upon mutations.]
* **Recommended Cleanup Plan:** [In-memory caching, batch query refactoring, or debounce setup.]

---

## 7. Abandoned or Disconnected Files

### Issue 7.1: [Short Title]
* **Location:** `[path/to/orphaned_file.ext]`
* **Why Unnecessary:** [Why the file is disconnected from the build or application flow.]
* **Estimated Impact:** [e.g., Eliminates repository clutter, prevents misleading documentation.]
* **Pre-Deletion Risks:** [e.g., Ensure no CI/CD or documentation scripts reference the file.]
* **Recommended Cleanup Plan:** [Safe file deletion.]

---

## 8. Technical Debt & Release / Packaging Readiness

### Issue 8.1: [Short Title]
* **Location:** `[path/to/config.ext]`
* **Why Unnecessary / Deficit:** [Explain what will fail upon compilation or deployment.]
* **Estimated Impact:** [e.g., Guarantees portable asset loading in bundled standalone executable.]
* **Pre-Deletion Risks:** [e.g., Testing in both dev mode and packaged executable mode.]
* **Recommended Cleanup Plan:** [Environment-aware path resolution and build spec setup.]

---

## Summary of Cleanup Leverage

| Area | Issues Identified | Estimated Code/Asset Reduction | Performance / Reliability Gain |
|---|---|---|---|
| **Dead Code** | N issues | ... | ... |
| **Duplicate Logic** | N issues | ... | ... |
| **Unused UI / Assets** | N issues | ... | ... |
| **Complexity & Monoliths** | N issues | ... | ... |
| **Legacy Code** | N issues | ... | ... |
| **Database & I/O** | N issues | ... | ... |
| **Abandoned Files** | N issues | ... | ... |
| **Technical Debt & Packaging**| N issues | ... | ... |

---

## Phased Action Plan

1. **Step 1 (Safe Surgical Cleanups)**
2. **Step 2 (Deduplication & Component Extraction)**
3. **Step 3 (I/O Caching & Batching)**
4. **Step 4 (Packaging & Environment Fixes)**
5. **Step 5 (Verification Gate — Test Suite & Manual Smoke Tests)**
