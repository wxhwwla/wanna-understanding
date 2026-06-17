---
name: "design-then-build"
description: "Full development workflow: grill-me to stress-test the design, then TDD red-green-refactor to implement. Non-risky operations auto-consented, high-risk operations require manual approval. DEFAULT skill for this project."
---

# Design-Then-Build Workflow

## When to Invoke

This is the **default workflow skill** for this project. Invoke it:
- When the user asks to implement a feature, fix a bug, or refactor code
- When the user starts a new development task
- Unless the user explicitly calls for a different skill

Do NOT invoke it:
- When the user asks a pure informational question (no code changes)
- When the user explicitly invokes a different skill by name

## Workflow

### Phase 1: Design (grill-me)

Before writing any code, interview the user relentlessly about the plan:
1. Ask questions **one at a time**, walking down each branch of the design tree
2. For each question, provide your **recommended answer**
3. Resolve dependencies between decisions
4. Explore the codebase before asking questions that can be answered by reading it
5. Continue until a shared understanding is reached

### Phase 2: Implement (tdd)

Use test-driven development with red-green-refactor:
1. **Plan**: Write a concrete implementation plan with vertical slices
2. **Tracer Bullet**: Write ONE test → make it fail → make it pass
3. **Incremental Loop**: One test → one implementation → repeat
4. **Refactor**: After all tests pass, clean up
5. Write tests that verify behavior through public interfaces

### Phase 3: Verify

After all slices:
1. Run the **full test suite** (`python -m pytest tests/ -v`)
2. Run **lint** (if available: `ruff check .` or equivalent)
3. Report results

## Auto-Consent Rules

- **Auto-consent**: Running tests, creating files, modifying code, installing dependencies, running safe scripts
- **Manual approval (ask user first)**: 
  - Running upload scripts (`github_upload_module.py`)
  - Pushing to git
  - Deleting files outside the project
  - Running destructive system commands
  - Installing packages that modify the system Python environment
