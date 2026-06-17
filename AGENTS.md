# Agent Skills Configuration

## Session continuity (new conversations)

**At the start of every new conversation** on this repo (unless the user only asks a one-off question unrelated to the codebase), read these two documents first:

1. [`docs/会话接续手册.md`](docs/会话接续手册.md) — project state, architecture seams, recent work, todo
2. [`docs/技术方案.md`](docs/技术方案.md) — detailed module design, data flow, interfaces

If the user @-mentions either file, treat it as mandatory context before any code change.

**Layout constraints:** Before structural refactors or adding modules, read [`docs/代码结构规范.md`](docs/代码结构规范.md) (≤20 items per directory, target ≤15; ~400 lines per file).

## Project operations

Before changing code or pushing to GitHub, read the operations guide: [`docs/操作指令集.md`](docs/操作指令集.md).

Domain terms: [`CONTEXT.md`](CONTEXT.md).

### Pushing to GitHub (agents)

**All git upload operations must go through `python github_upload_module.py`.** Agents must NOT execute `git add`, `git commit`, or `git push` directly.

- **Default: the human runs upload.** Publishing is done by the repo maintainer locally. Agents **must not** run the upload script unless the user **explicitly asks in that conversation**.
- When work is ready but the user has not asked to publish, **stop** and tell them which command to run.
- Version bumps for `_VERSION` must go through the upload script.

### Pulling from GitHub (agents)

- **Do not** run `python github_download_module.py` unless the user explicitly asks to discard local work.
- That script requires typing **`覆盖本地`** to confirm; it runs `reset --hard` and `git clean -fd`.

## Default development workflow

**When the user requests feature implementation, bug fixes, or code changes**, default to the `design-then-build` workflow:
1. First interview the user to clarify the design
2. Then implement with TDD (test-first, red-green-refactor)
3. For non-risky operations (tests, code edits, dependency installs), auto-consent
4. For high-risk operations (git push, destructive commands), ask user first
