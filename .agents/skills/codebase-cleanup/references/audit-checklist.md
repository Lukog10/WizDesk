# Codebase Cleanup Audit Checklist

A quick technical checklist for agents and engineers conducting a deep cleanup pass.

---

## 1. Imports & Symbols
- [ ] Run AST / linter checks (e.g. `flake8 --select=F401`, `ruff check --select F401`, `eslint --rule 'no-unused-vars: error'`).
- [ ] Check for wildcard imports (`from module import *`) hiding actual dependencies.
- [ ] Verify if imported classes are used as type annotations only (use `from typing import TYPE_CHECKING` if applicable).
- [ ] Check manifest files (`requirements.txt`, `package.json`, `Cargo.toml`) for unused packages.

## 2. Event Systems & Signals
- [ ] List all declared signals, event emitters, or custom event hooks.
- [ ] Search repository for `.emit(`, `.dispatch(`, or `.trigger(` calls.
- [ ] Search repository for `.connect(`, `.subscribe(`, or `.addListener(` calls.
- [ ] Flag signals that are never emitted or never listened to.

## 3. Storage, SQL & Caching
- [ ] Inspect background daemon threads, polling intervals (`setInterval`, `QTimer`, `time.sleep`).
- [ ] Check what queries run inside periodic loops. If query result changes infrequently, apply memoization or cache with invalidation.
- [ ] Check data-fetching loops: look for `SELECT ... WHERE parent_id = ?` executed inside a parent row iteration (N+1 query pattern). Replace with `IN (...)` or JOIN.
- [ ] Verify database schema tables vs repository operations. Look for tables created in schema migration scripts that have no corresponding repository read/write methods.

## 4. UI & Styling
- [ ] Identify duplicate custom widgets (e.g. two classes drawing custom checkboxes, buttons, or modals).
- [ ] Look for repeated hardcoded CSS/QSS strings. Extract design tokens (colors, font stacks, border radiuses) into a single theme palette.
- [ ] Check asset directories (`assets/`, `public/`, `static/`). Find duplicate image formats (e.g. `logo.png` vs `logo.svg`), old design iterations, or unused fonts.

## 5. Architectural Boundaries
- [ ] Check file sizes. Any single file exceeding 1,000 lines should be evaluated for multi-responsibility bloat.
- [ ] Check cross-imports: Does a secondary utility module import a massive main window module just to borrow a 20-line helper? Extract the helper.

## 6. Packaging & Production Readiness
- [ ] Path resolution: Ensure asset loading supports bundled runtime environments (e.g. `sys._MEIPASS` or `importlib.resources`).
- [ ] Standard I/O: Ensure application does not crash in windowed/no-console mode (where `sys.stdout` or `sys.stderr` may be `None`).
- [ ] Clean manifest: Separate developer/test dependencies from the runtime production bundle.
