# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Cursor, Copilot, Antigravity, etc.) when working with code in this repository.

## Repository Overview

<!-- FILL IN: One-paragraph description of what this project is. -->

## Skill-Driven Execution Model

This project uses a **skill-driven execution model**. Skills are packaged instructions in `skills/<skill-name>/SKILL.md` that extend the agent's capabilities for specific domains.

### Core Rules

- If a task matches a skill, you MUST load and follow it
- Skills are located in `skills/<skill-name>/SKILL.md`
- Never implement directly if a skill applies
- Always follow the skill instructions exactly (do not partially apply them)

### Commit Routine

- After any agent makes code, configuration, documentation, or asset changes, the agent MUST commit the working tree before handing off, unless the user explicitly says not to commit.
- Use a short, appropriate commit message that summarizes the completed change.
- If verification fails, mention the failure in the final response but still commit when the user requested a commit.

### Intent → Skill Mapping

The agent should automatically map user intent to skills:

<!-- CUSTOMIZE these mappings for your project. Examples: -->

- Feature / new functionality → plan first, then build incrementally
- Bug / failure / unexpected behavior → debug and recover
- Code review → review for quality
- Refactoring / simplification → simplify with care
- API or interface design → design the contract first
- UI work → follow frontend engineering best practices

### Lifecycle Mapping

The agent must internally follow this lifecycle for non-trivial work:

1. **DEFINE** — Clarify what needs to be built (spec)
2. **PLAN** — Break down into tasks
3. **BUILD** — Implement incrementally
4. **VERIFY** — Test and debug
5. **REVIEW** — Self-review for quality
6. **SHIP** — Deliver and commit

### Execution Model

For every request:

1. Determine if any skill applies (even 1% chance)
2. Load the appropriate `SKILL.md` and follow it
3. Follow the skill workflow strictly
4. Only proceed to implementation after required steps (spec, plan, etc.) are complete

### Anti-Rationalization

The following thoughts are incorrect and must be ignored:

- "This is too small for a skill"
- "I can just quickly implement this"
- "I'll gather context first"

Correct behavior:

- Always check for and use skills first

## Creating a New Skill

### Directory Structure

```
skills/
  {skill-name}/           # kebab-case directory name
    SKILL.md              # Required: skill definition
    scripts/              # Optional: executable scripts
    examples/             # Optional: reference implementations
    references/           # Optional: detailed docs
```

### Naming Conventions

- **Skill directory**: `kebab-case` (e.g. `api-design`, `building-ui`)
- **SKILL.md**: Always uppercase, always this exact filename

### SKILL.md Format

```markdown
---
name: {skill-name}
description: >
  One sentence describing what the skill does.
  Use when [trigger condition 1]. Use when [trigger condition 2].
---

# {Skill Title}

{Brief overview of what the skill does and why it matters.}

## How It Works

1. Step one
2. Step two
3. ...

## Exit Criteria

- [ ] Criterion 1
- [ ] Criterion 2
```

### Best Practices

- **Keep SKILL.md under 500 lines** — put detailed reference material in separate files
- **Write specific descriptions** — helps the agent know exactly when to activate
- **Use progressive disclosure** — reference supporting files that get read only when needed

## Full Output Enforcement

When generating or modifying code, the agent MUST:

- Never truncate output
- Never use `// ... rest unchanged` or `/* existing code */`
- Never leave placeholder comments like `// TODO: implement`
- Always write complete, working code
- If a file is too large to output in full, split the work into smaller edits
