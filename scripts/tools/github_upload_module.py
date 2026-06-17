#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0
"""Push this repo to GitHub over SSH and bump scripts/_version.py when needed."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ===== config =====

DEFAULT_REMOTE_SSH = "git@github.com:wxhwwla/wanna-understanding.git"
AUTH_MODE = "ssh"
REMOTE_HTTPS = "https://github.com/wxhwwla/wanna-understanding.git"

KEY_FILE = "git_key.txt"

WORK_BRANCH = "develop"
RELEASE_BRANCH = "main"
DEFAULT_BRANCH = WORK_BRANCH

SKIP_PULL = False
FORCE_PUSH = False

# =================


_TOKEN_IN_REMOTE = re.compile(
    r"https://[^@\s]+@github\.com/",
    re.IGNORECASE,
)


def _import_upload_meta():
    """Import upload_meta module dynamically."""
    from scripts._path_setup import ensure_root

    ensure_root()
    from scripts._version import ensure_summary_marker_assignments, please_read_me_path

    if ensure_summary_marker_assignments(please_read_me_path()):
        print("[info] fixed _version.py SUMMARY_BEGIN/SUMMARY_END constants")
    from scripts import upload_meta

    return upload_meta


def _decode_output(output: Any) -> str:
    """Decode command output to string."""
    if output is None:
        return ""

    if isinstance(output, str):
        return output

    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")

    if isinstance(output, memoryview):
        return bytes(output).decode("utf-8", errors="replace")

    return str(output)


def _run_git_core(
    args: list[str], *, check: bool, capture_output: bool, timeout: int | None
) -> subprocess.CompletedProcess:
    """Low-level git command wrapper."""
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=capture_output,
            encoding="utf-8",
            errors="replace",
            check=check,
            timeout=timeout,
        )
    except FileNotFoundError:
        print("[error] git not found, please install Git and add to PATH")
        sys.exit(1)


def run_git(
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    timeout: int | None = 30,
) -> tuple[int, str, str]:
    """Run git command and return (returncode, stdout, stderr)."""
    try:
        if capture_output:
            proc = _run_git_core(
                args, check=check, capture_output=True, timeout=timeout
            )
            return (
                proc.returncode,
                _decode_output(proc.stdout),
                _decode_output(proc.stderr),
            )

        proc = _run_git_core(args, check=check, capture_output=False, timeout=timeout)
        return proc.returncode, "", ""

    except subprocess.CalledProcessError as e:
        print(f"[error] Git command failed: git {' '.join(args)}")
        print(f"[error] Exit code: {e.returncode}")
        raise
    except subprocess.TimeoutExpired:
        print(f"[error] Git command timed out ({timeout}s): git {' '.join(args)}")
        raise


def _repo_root() -> str:
    """Return repo root directory as string path."""
    return str(Path(__file__).resolve().parent.parent.parent)


def _git_dir() -> Path:
    return Path(_repo_root()) / ".git"


def _is_rebase_in_progress() -> bool:
    git_dir = _git_dir()
    return (git_dir / "rebase-merge").is_dir() or (git_dir / "rebase-apply").is_dir()


def _is_merge_in_progress() -> bool:
    return (_git_dir() / "MERGE_HEAD").is_file()


def preflight_upload(*, check_only: bool = False) -> bool:
    """Preflight checks before upload."""
    root = _repo_root()
    if not os.path.isdir(os.path.join(root, ".git")):
        print("[error] no .git directory found")
        return False
    if _is_rebase_in_progress():
        print("[error] rebase in progress, please git rebase --continue or --abort")
        return False
    if _is_merge_in_progress():
        print("[error] merge in progress, please finish or abort")
        return False

    ref = _remote_branch_ref()
    code, _, _ = run_git(
        ["rev-parse", "--verify", ref], check=False, capture_output=True
    )
    if code != 0:
        if check_only:
            print(f"[info] remote origin/{WORK_BRANCH} does not exist, first push OK")
        return True

    code, merge_base, _ = run_git(
        ["merge-base", "HEAD", ref],
        check=False,
        capture_output=True,
    )
    if code != 0 or not merge_base.strip():
        print(
            f"[error] local and origin/{WORK_BRANCH} have no common ancestor, "
            "manual reconcile needed"
        )
        return False

    if check_only:
        print("[info] preflight passed")
    return True


def _origin_remote_url() -> str | None:
    """Read origin remote URL from git config."""
    if not os.path.isdir(os.path.join(_repo_root(), ".git")):
        return None

    code, url, _ = run_git(
        ["remote", "get-url", "origin"],
        check=False,
        capture_output=True,
    )
    if code != 0:
        return None

    return url.strip() or None


def _remote_url() -> str:
    """Determine remote URL based on AUTH_MODE."""
    if AUTH_MODE == "ssh":
        origin = _origin_remote_url()
        if origin and not _TOKEN_IN_REMOTE.search(origin):
            return origin
        return DEFAULT_REMOTE_SSH

    if AUTH_MODE == "https_token":
        if not os.path.isfile(KEY_FILE):
            print(f"[error] HTTPS mode needs {KEY_FILE}, use AUTH_MODE='ssh' instead")
            sys.exit(1)
        with open(KEY_FILE, encoding="utf-8") as f:
            token = f.read().strip()
        if not token:
            print(f"[error] {KEY_FILE} is empty")
            sys.exit(1)
        path = REMOTE_HTTPS.removeprefix("https://")
        return f"https://wxhwwla:{token}@{path}"

    print(f"[error] unknown AUTH_MODE: {AUTH_MODE}")
    sys.exit(1)


def _warn_if_remote_has_embedded_token(stdout: str) -> None:
    """Check if remote URL has embedded token."""
    if _TOKEN_IN_REMOTE.search(stdout):
        print("[warn] origin has embedded HTTPS token, changing to SSH/new URL")


def _ensure_gitignore(repo_dir: str) -> None:
    """Ensure .gitignore has required entries."""
    path = os.path.join(repo_dir, ".gitignore")
    wanted = [
        KEY_FILE,
        "git_key.txt",
        ".git-upload-msg.txt",
        "__pycache__/",
        "*.py[cod]",
        ".venv/",
        "venv/",
        "build/",
        "dist/",
        "*.spec",
        "*.exe",
        "*.log",
        "debug.log",
        ".pytest_cache/",
        ".ruff_cache/",
        ".coverage",
        "cov_report.txt",
        "htmlcov/",
        ".benchmarks/",
    ]

    existing = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()

    to_add = [line for line in wanted if line not in existing]
    if not to_add:
        return

    with open(path, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write("\n".join(to_add) + "\n")

    print(f"[info] updated .gitignore (added {len(to_add)} entries)")


def setup_git_repo() -> str:
    """Setup/check git repo, configure remote and branch."""
    script_dir = _repo_root()
    os.chdir(script_dir)
    remote = _remote_url()

    if AUTH_MODE == "ssh":
        print("[info] using SSH push")
        probe_code, _, probe_err = run_git(
            ["ls-remote", remote, "HEAD"],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if probe_code != 0:
            hint = (probe_err or "").strip() or f"exit {probe_code}"
            print(f"[warn] SSH connectivity not confirmed ({hint})")

    _ensure_gitignore(script_dir)

    if not os.path.isdir(".git"):
        print("[info] initializing Git repo")
        run_git(["init"])
        run_git(["config", "user.name", "wxhwwla"])
        run_git(["config", "user.email", "wxhwwla@gmail.com"])

    _, current_branch, _ = run_git(["branch", "--show-current"], capture_output=True)
    current_branch = current_branch.strip()

    if current_branch != WORK_BRANCH:
        print(
            f"[info] current branch is '{current_branch}', switching to {WORK_BRANCH}"
        )
        code, _, _ = run_git(
            ["checkout", WORK_BRANCH], check=False, capture_output=True
        )
        if code != 0:
            _, branches, _ = run_git(["branch"], capture_output=True)
            if WORK_BRANCH in branches:
                print("[error] can't switch due to uncommitted changes")
                print(
                    "[hint] manually: "
                    f"git stash && git checkout {WORK_BRANCH} && git stash pop"
                )
                print(f"[hint] or run the script from {WORK_BRANCH} branch")
                sys.exit(1)
            code, _, _ = run_git(
                ["checkout", "-b", WORK_BRANCH, f"origin/{RELEASE_BRANCH}"],
                check=False,
                capture_output=True,
            )
            if code != 0:
                run_git(["checkout", "-b", WORK_BRANCH])
            print(f"[info] created local branch {WORK_BRANCH}")

    _, stdout, _ = run_git(["remote", "-v"], capture_output=True)
    _warn_if_remote_has_embedded_token(stdout)

    if "origin" not in stdout:
        print("[info] adding origin")
        run_git(["remote", "add", "origin", remote])
    else:
        print("[info] updating origin URL")
        run_git(["remote", "set-url", "origin", remote])

    _, verify, _ = run_git(["remote", "get-url", "origin"], capture_output=True)
    if _TOKEN_IN_REMOTE.search(verify):
        print("[error] origin still has embedded token, manually run:")
        print(f"  git remote set-url origin {DEFAULT_REMOTE_SSH}")
        sys.exit(1)

    print(f"[info] origin = {verify.strip()}")
    return remote


def _remote_branch_ref() -> str:
    return f"origin/{WORK_BRANCH}"


def _remote_release_ref() -> str:
    return f"origin/{RELEASE_BRANCH}"


def _fetch_origin_main(*, timeout: int = 300) -> None:
    run_git(["fetch", "origin", WORK_BRANCH], check=False, timeout=timeout)


def _fetch_all_origin_branches(*, timeout: int = 300) -> None:
    run_git(
        ["fetch", "origin", WORK_BRANCH, RELEASE_BRANCH],
        check=False,
        timeout=timeout,
    )


def _count_ahead_behind() -> tuple[int, int]:
    """Return (ahead count, behind count) vs origin/develop."""
    ref = _remote_branch_ref()
    code, _, _ = run_git(
        ["rev-parse", "--verify", ref], check=False, capture_output=True
    )
    if code != 0:
        return 0, 0
    _, ahead, _ = run_git(
        ["rev-list", "--count", f"{ref}..HEAD"],
        check=False,
        capture_output=True,
    )
    _, behind, _ = run_git(
        ["rev-list", "--count", f"HEAD..{ref}"],
        check=False,
        capture_output=True,
    )
    ahead_n = int(ahead.strip()) if ahead.strip().isdigit() else 0
    behind_n = int(behind.strip()) if behind.strip().isdigit() else 0
    return ahead_n, behind_n


def _stash_error_lines(stderr: str) -> list[str]:
    lines: list[str] = []
    for raw in stderr.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("warning:") and "LF will be replaced by CRLF" in line:
            continue
        lines.append(line)
    return lines


def _stash_dirty_worktree() -> bool:
    """Stash uncommitted changes."""
    _, status_out, _ = run_git(
        ["status", "--porcelain"], check=False, capture_output=True
    )
    if not status_out.strip():
        return True

    print("[info] stashing local changes")
    stash_code, _, stash_err = run_git(
        ["stash", "push", "--include-untracked", "-m", "upload-script"],
        check=False,
        capture_output=True,
    )
    if stash_code == 0:
        return True

    issues = _stash_error_lines(stash_err)
    detail = (
        "\n  ".join(issues) if issues else stash_err.strip() or f"exit {stash_code}"
    )
    print(f"[error] stash failed:\n  {detail}")
    return False


def _pop_stash_if_needed(stashed: bool, *, pull_ok: bool) -> None:
    if not stashed or not pull_ok:
        return
    code, _, stderr = run_git(
        ["stash", "pop", "--index"],
        check=False,
        capture_output=True,
    )
    if code != 0:
        print("[warn] stash pop failed, manually run: git stash pop")
        if stderr.strip():
            print(f"[warn] {stderr.strip()}")


def sync_with_remote(*, skip_pull: bool = False) -> bool:
    """Fetch remote updates and sync local."""
    if skip_pull or SKIP_PULL:
        print("[info] skipped pull")
        return True

    print("[info] pulling remote updates...")
    _fetch_origin_main()

    ahead, behind = _count_ahead_behind()
    if behind == 0:
        print(
            f"[info] in sync with origin/{WORK_BRANCH} (ahead {ahead}), skipping pull"
        )
        return True

    print(f"[info] behind origin/{WORK_BRANCH} by {behind} commits, pulling...")

    code, stdout, _ = run_git(
        ["rev-list", "--count", "--all"], check=False, capture_output=True
    )
    has_commits = int(stdout.strip()) > 0 if code == 0 and stdout.strip() else False
    if not has_commits:
        print("[info] no local commits, skipping pull")
        return True

    stashed = _stash_dirty_worktree()
    if not stashed:
        return False

    code, _, stderr = run_git(
        ["pull", "--rebase", "origin", WORK_BRANCH],
        check=False,
        capture_output=False,
        timeout=300,
    )
    pull_ok = code == 0
    if not pull_ok:
        _code2, heads, _ = run_git(
            ["ls-remote", "--heads", "origin", WORK_BRANCH],
            check=False,
            capture_output=True,
        )
        if not heads.strip():
            print(f"[info] remote has no {WORK_BRANCH} yet, first push")
            pull_ok = True
        else:
            print(f"[warn] pull failed: {stderr.strip()}")

    _pop_stash_if_needed(stashed, pull_ok=pull_ok)
    return pull_ok


def _unquote_git_path(raw: str) -> str:
    """Unquote git path with C-style escapes."""
    text = raw.strip()
    if not (text.startswith('"') and text.endswith('"')):
        return text
    inner = text[1:-1]
    out = bytearray()
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch != "\\":
            out.extend(ch.encode("utf-8"))
            i += 1
            continue
        i += 1
        if i >= len(inner):
            break
        esc = inner[i]
        if esc in ('"', "\\"):
            out.extend(esc.encode("utf-8"))
            i += 1
        elif esc == "n":
            out.extend(b"\n")
            i += 1
        elif esc == "t":
            out.extend(b"\t")
            i += 1
        elif esc.isdigit():
            j = i
            while j < len(inner) and j < i + 3 and inner[j].isdigit():
                j += 1
            out.append(int(inner[i:j], 8))
            i = j
        else:
            out.extend(esc.encode("utf-8"))
            i += 1
    return out.decode("utf-8")


def _normalize_change_path(raw: str) -> str:
    """Normalize git path to repo-relative POSIX path."""
    path = _unquote_git_path(raw.strip())
    if not path:
        return ""
    path = path.replace("\\", "/")
    root = _repo_root().replace("\\", "/")
    if os.path.isabs(path) or (len(path) > 1 and path[1] == ":"):
        try:
            return os.path.relpath(path, root).replace("\\", "/")
        except ValueError:
            return path
    return path


def _porcelain_paths(porcelain: str) -> list[str]:
    """Extract file paths from git status --porcelain output.

    Uses core.quotepath=false to handle Chinese filenames correctly.
    Skips deleted (D) entries.
    """
    paths: list[str] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue

        if line[0] == "D" or line[0:2] in (" D", "DD"):
            continue

        rest = line[3:].strip()

        if " -> " in rest:
            rest = rest.split(" -> ")[-1].strip()

        normalized = _normalize_change_path(rest)
        if normalized:
            paths.append(normalized)

    return paths


def _collect_change_paths() -> list[str]:
    """Collect all changed file paths (excluding deleted entries).

    Uses core.quotepath=false for Chinese filename support.
    """
    path_git = ["-c", "core.quotepath=false"]
    _, porcelain, _ = run_git([*path_git, "status", "--porcelain"], capture_output=True)
    paths = _porcelain_paths(porcelain)
    for diff_cmd in (
        ["diff", "--diff-filter=d", "--name-only"],
        ["diff", "--cached", "--diff-filter=d", "--name-only"],
    ):
        _, out, _ = run_git([*path_git, *diff_cmd], check=False, capture_output=True)
        for line in out.splitlines():
            normalized = _normalize_change_path(line)
            if normalized:
                paths.append(normalized)

    return paths


@dataclass(frozen=True)
class SigningConfig:
    """Local git commit signing config snapshot."""

    gpgsign: str | None
    signingkey: str | None
    gpg_format: str | None


def _is_truthy_git_config(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"true", "1", "yes", "on"}


def _git_config_get(key: str) -> str | None:
    """Read git config (local first, then global)."""
    for scope in ([], ["--global"]):
        args = ["config", *scope, "--get", key] if scope else ["config", "--get", key]
        code, stdout, _ = run_git(args, check=False, capture_output=True)
        if code == 0 and stdout.strip():
            return stdout.strip()
    return None


def resolve_signing_config(
    getter: Callable[[str], str | None] | None = None,
) -> SigningConfig:
    read = getter or _git_config_get
    return SigningConfig(
        gpgsign=read("commit.gpgsign"),
        signingkey=read("user.signingkey"),
        gpg_format=read("gpg.format"),
    )


def commit_extra_args(cfg: SigningConfig) -> list[str]:
    """Return extra args for git commit based on signing config."""
    if _is_truthy_git_config(cfg.gpgsign):
        return []
    if cfg.signingkey and cfg.signingkey.strip():
        return ["-S"]
    return []


def tag_extra_args(cfg: SigningConfig) -> list[str]:
    if is_signing_configured(cfg):
        return ["-s"]
    return []


def is_signing_configured(cfg: SigningConfig) -> bool:
    return bool(commit_extra_args(cfg)) or _is_truthy_git_config(cfg.gpgsign)


def signing_status_message(cfg: SigningConfig) -> str:
    if is_signing_configured(cfg):
        fmt = (cfg.gpg_format or "openpgp").strip().lower()
        return (
            f"[info] commit signing configured ({fmt}), "
            "commits and tags will be signed, "
            "GitHub can show Verified\n"
            "(key must be added to GitHub SSH and GPG keys Settings)"
        )
    return (
        "[hint] no commit signing detected; commits/tags may lack Verified badge.\n"
        "  Setup example (SSH signing):\n"
        "    git config --global gpg.format ssh\n"
        "    git config --global user.signingkey /path/to/ssh/public/key\n"
        "    git config --global commit.gpgsign true\n"
        "  Then add your SSH public key to GitHub SSH and GPG keys Signing keys"
    )


def _ask_bump_kind(*, minor_flag: bool, no_bump: bool) -> str | None:
    if no_bump:
        return None
    if minor_flag:
        return "minor"
    if sys.stdin.isatty():
        print("version bump: [P]atch (enter default) / [M]inor")
        choice = input("> ").strip().lower()
        if choice in ("m", "minor"):
            return "minor"
        return "patch"
    return "patch"


def _rel_repo_path(path: Path | str) -> str:
    if isinstance(path, Path):
        p = path
        if p.is_absolute():
            return os.path.relpath(p, _repo_root()).replace("\\", "/")
        return p.as_posix()
    return _normalize_change_path(str(path))


def _stage_upload_changes(change_paths: list[str], version_path: Path) -> None:
    """Stage only upload-related paths, avoiding git add ."""
    paths: list[str] = []
    seen: set[str] = set()
    for raw in change_paths:
        rel = _rel_repo_path(raw)
        if rel and rel not in seen:
            seen.add(rel)
            paths.append(rel)
    version_rel = _rel_repo_path(version_path)
    if version_rel not in seen:
        paths.append(version_rel)
    if not paths:
        print("[error] no valid paths to stage")
        sys.exit(1)
    print(f"[info] git add ({len(paths)} paths, staged in batches)")
    paths = [p for p in paths if os.path.exists(os.path.join(_repo_root(), p))]
    if not paths:
        print("[error] all paths no longer exist")
        sys.exit(1)
    batch_size = 50
    for i in range(0, len(paths), batch_size):
        batch = paths[i : i + batch_size]
        run_git(["add", "--", *batch])
    print(f"[info] git add done ({len(paths)} paths)")


def _pre_commit_installed() -> bool:
    return os.path.isfile(os.path.join(_repo_root(), ".git", "hooks", "pre-commit"))


def _staged_file_list() -> list[str]:
    _, out, _ = run_git(
        ["-c", "core.quotepath=false", "diff", "--cached", "--name-only"],
        check=False,
        capture_output=True,
    )
    paths: list[str] = []
    for line in out.splitlines():
        normalized = _normalize_change_path(line)
        if normalized:
            paths.append(normalized)
    return paths


def _unstaged_modified_paths() -> list[str]:
    """Return paths modified in worktree but not in index."""
    _, porcelain, _ = run_git(
        ["-c", "core.quotepath=false", "status", "--porcelain"],
        check=False,
        capture_output=True,
    )
    paths: list[str] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        if line[0] == " " and line[1] not in (" ", "?"):
            normalized = _normalize_change_path(line[3:])
            if normalized:
                paths.append(normalized)
    return paths


def _refresh_staging_for_commit(change_paths: list[str], version_path: Path) -> None:
    """Re-stage before commit to avoid index/worktree inconsistency."""
    merged: list[str] = []
    seen: set[str] = set()
    for raw in (*change_paths, *_collect_change_paths()):
        rel = _rel_repo_path(raw)
        if rel and rel not in seen:
            seen.add(rel)
            merged.append(rel)
    version_rel = _rel_repo_path(version_path)
    if version_rel not in seen:
        merged.append(version_rel)
    unstaged = _unstaged_modified_paths()
    added = 0
    for path in unstaged:
        if path not in seen:
            seen.add(path)
            merged.append(path)
            added += 1
    if added:
        print(f"[info] added {added} worktree changes")
    print(f"[info] git add ({len(merged)} paths, pre-commit sync)")
    merged = [p for p in merged if os.path.exists(os.path.join(_repo_root(), p))]
    if not merged:
        print("[info] no valid files to stage")
        return
    batch_size = 50
    for i in range(0, len(merged), batch_size):
        batch = merged[i : i + batch_size]
        run_git(["add", "--", *batch])
    print(f"[info] pre-commit sync done ({len(merged)} paths)")


def _pre_commit_has_lint_errors(output: str) -> bool:
    lint_failed = False
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("ruff-lint") and "Failed" in stripped:
            lint_failed = True
            break
    if not lint_failed:
        return False
    if re.search(r"\(\d+ fixed, 0 remaining\)", output):
        return False
    return not re.search(r"Found \d+ errors? .*0 remaining", output)


def _run_pre_commit_on_staged(*, rounds: int = 2) -> bool:
    """Run pre-commit, retrying if hooks auto-fix files."""
    if not _pre_commit_installed():
        return True
    print(f"[info] pre-commit up to {rounds} rounds")
    for attempt in range(1, rounds + 1):
        files = _staged_file_list()
        if not files:
            return True
        print(f"[info] pre-commit round {attempt}/{rounds} ({len(files)} files)")
        proc = subprocess.run(
            ["pre-commit", "run", "--files", *files],
            cwd=_repo_root(),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        if proc.returncode == 0:
            if attempt > 1:
                print(f"[info] pre-commit round {attempt} passed")
            return True
        if _pre_commit_has_lint_errors(output):
            print("[error] ruff-lint issues found, please fix before retrying")
            return False
        if attempt < rounds:
            print(f"[info] pre-commit round {attempt}: hooks auto-fixed, re-adding...")
        if files:
            run_git(["add", "--", *files], check=False)
    print("[error] pre-commit failed, commit cancelled")
    return False


def _version_file_relpath(readme_path: Path) -> str:
    return readme_path.relative_to(_repo_root()).as_posix()


def _read_version_from_git_head(readme_path: Path) -> str | None:
    """Read _VERSION from HEAD; None if no commit."""
    from scripts._version import _VERSION_PATTERN

    code, out, _ = run_git(
        ["show", f"HEAD:{_version_file_relpath(readme_path)}"],
        check=False,
        capture_output=True,
    )
    if code != 0 or not out.strip():
        return None
    match = _VERSION_PATTERN.search(out)
    return match.group(2) if match else None


def _sync_saved_version_with_head(readme_path: Path, meta) -> str:
    """Sync _VERSION with HEAD (revert leftover bumps from failed uploads)."""
    saved_version = meta.read_version(readme_path)
    head_version = _read_version_from_git_head(readme_path)
    if head_version and saved_version != head_version:
        print(
            f"[info] correcting _VERSION: worktree {saved_version} "
            f"-> HEAD {head_version}"
            " (leftover from failed upload)"
        )
        meta.write_version(readme_path, head_version)
        return head_version
    return saved_version


def _should_merge_to_release(*, was_minor: bool) -> bool:
    """Auto-merge develop -> main on minor version bumps."""
    if not was_minor:
        print(f"[info] not a minor upload, pushing only {WORK_BRANCH}")
        return False
    release_ref = _remote_release_ref()
    code, _, _ = run_git(
        ["rev-parse", "--verify", release_ref], check=False, capture_output=True
    )
    if code != 0:
        print(f"[info] remote {RELEASE_BRANCH} does not exist, skipping merge")
        return False
    print(f"[info] minor upload -> merging {WORK_BRANCH} -> {RELEASE_BRANCH}")
    return True


def _merge_work_into_release(*, meta, readme_path: Path, push_tag: bool) -> None:
    """Merge develop into main and push."""
    _, saved_out, _ = run_git(["branch", "--show-current"], capture_output=True)
    saved_branch = saved_out.strip()

    stashed = False
    _, status_out, _ = run_git(["status", "--porcelain"], capture_output=True)
    if status_out.strip():
        run_git(
            ["stash", "--include-untracked", "-m", "upload: auto-stash before merge"]
        )
        stashed = True

    try:
        _fetch_all_origin_branches()
        code, _, _ = run_git(
            ["checkout", RELEASE_BRANCH], check=False, capture_output=True
        )
        if code != 0:
            _, branches, _ = run_git(["branch"], capture_output=True)
            if RELEASE_BRANCH in branches:
                print(f"[error] cannot switch to {RELEASE_BRANCH}, merge cancelled")
                return
            run_git(["checkout", "-b", RELEASE_BRANCH, _remote_release_ref()])
        run_git(["pull", "--rebase", "origin", RELEASE_BRANCH], timeout=300)
        run_git(
            [
                "merge",
                "--no-ff",
                WORK_BRANCH,
                "-m",
                f"release: merge {WORK_BRANCH} into {RELEASE_BRANCH}",
            ],
            timeout=120,
        )
        run_git(["push", "origin", RELEASE_BRANCH], timeout=300)
        print(f"[ok] merged {WORK_BRANCH} -> {RELEASE_BRANCH} and pushed")
        if push_tag:
            _push_tag(meta.read_exe_version(readme_path))
    finally:
        if saved_branch:
            run_git(["checkout", saved_branch], check=False)
        if stashed:
            run_git(["stash", "pop"], check=False)


def _rollback_upload_draft(
    readme_path,
    meta,
    *,
    saved_version: str,
    restore_version: bool,
) -> None:
    """Rollback summary block and optionally version number on failure."""
    meta.remove_summary_block(readme_path)
    if restore_version:
        meta.write_version(readme_path, saved_version)
        print(f"[info] rolled back _VERSION -> {saved_version}")
    print("[info] removed UPLOAD_SUMMARY block from _version.py")


def _commit_with_message(message: str) -> None:
    """Commit with message file."""
    cfg = resolve_signing_config()
    extra = commit_extra_args(cfg)
    msg_path = os.path.join(_repo_root(), ".git-upload-msg.txt")

    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(message)
        f.write("\n")

    try:
        run_git(["commit", *extra, "-F", msg_path])
    except subprocess.CalledProcessError as exc:
        print("[error] git commit failed (pre-commit / ruff likely)")
        if _pre_commit_installed():
            print("[hint] check for stash conflicts, then retry")
        raise exc
    finally:
        if os.path.isfile(msg_path):
            os.remove(msg_path)


def _push_to_remote() -> bool:
    """Push develop to origin; use -u for first push."""
    remote_ref = _remote_branch_ref()
    code, _, _ = run_git(
        ["rev-parse", "--verify", remote_ref], check=False, capture_output=True
    )
    push_args = ["push", "origin", WORK_BRANCH]
    if code != 0:
        push_args = ["push", "-u", "origin", WORK_BRANCH]
        print(f"[info] first push of {WORK_BRANCH} branch")
    if FORCE_PUSH:
        push_args.append("--force-with-lease")
        print("[warn] using --force-with-lease")

    print("[info] git push ...")
    try:
        run_git(push_args, timeout=300)
        print("[ok] push complete")
        return True
    except subprocess.CalledProcessError:
        if SKIP_PULL:
            print("[error] push failed; retry later or use --no-bump")
            raise

        print("[info] push failed, trying fetch + pull --rebase + retry")
        _fetch_origin_main()
        _, behind = _count_ahead_behind()
        if behind == 0:
            raise
        if not _stash_dirty_worktree():
            raise
        run_git(["pull", "--rebase", "origin", WORK_BRANCH], timeout=300)
        _pop_stash_if_needed(True, pull_ok=True)
        run_git(push_args, timeout=300)
        print("[ok] push complete")
        return True


def _push_tag(version: str) -> bool:
    """Create and push git tag."""
    tag = f"v{version}"
    _, existing_tags, _ = run_git(["tag", "-l", tag], capture_output=True)

    if tag in existing_tags.strip().split("\n"):
        print(f"[info] tag {tag} already exists, skipping")
    else:
        print(f"[info] creating tag {tag}")
        cfg = resolve_signing_config()
        tag_args = ["tag", "-a", tag, "-m", f"Release {tag}"]
        tag_args.extend(tag_extra_args(cfg))
        run_git(tag_args)

    print(f"[info] pushing tag {tag} ...")
    run_git(["push", "origin", tag], timeout=120)
    print(f"[info] tag {tag} pushed")
    return True


def _maybe_backup_git_for_minor(*, current_version: str, skip: bool) -> None:
    """Backup .git before minor version bump."""
    if skip:
        print("[info] skipped .git backup")
        return
    try:
        from scripts.tools import git_backup

        dest = git_backup.backup_git_dir(
            Path(_repo_root()),
            current_version=current_version,
            bump_kind="minor",
        )
        rel = dest.relative_to(_repo_root())
        print(f"[info] backed up .git -> {rel}")
    except ImportError:
        print("[info] git_backup module not found, skipping .git backup")
    except Exception as exc:
        print(f"[error] .git backup failed: {exc}")
        print(
            "[abort] minor upload needs successful backup; use --no-git-backup to skip"
        )
        sys.exit(1)


def commit_and_push(
    *,
    minor: bool = False,
    no_bump: bool = False,
    push_tag: bool = False,
    skip_git_backup: bool = False,
    dry_run: bool = False,
) -> None:
    """Execute git commit and push flow with version management.

    Args:
        minor: 次版本递增（第二位 +1，第三位置零）。
        no_bump: 本次上传不递增版本号。
        push_tag: 推送与版本对应的 git tag。
        skip_git_backup: 跳过上传前的 .git 目录备份。
        dry_run: 预览模式，展示计划但不修改或推送。
    """
    os.chdir(_repo_root())

    meta = _import_upload_meta()
    readme_path = meta.please_read_me_path()

    _, remote_heads, _ = run_git(
        ["ls-remote", "--heads", "origin", WORK_BRANCH],
        check=False,
        capture_output=True,
    )
    remote_exists = bool(remote_heads.strip())

    has_unpushed = False
    if remote_exists:
        code, ahead, _ = run_git(
            ["rev-list", "--count", f"origin/{WORK_BRANCH}..{WORK_BRANCH}"],
            check=False,
            capture_output=True,
        )
        if code == 0 and ahead.strip().isdigit():
            has_unpushed = int(ahead.strip()) > 0
            if has_unpushed:
                print(f"[info] {ahead.strip()} unpushed commits (no version bump)")

    created_commit = False
    was_minor = False
    push_succeeded = False
    version_for_msg = ""
    saved_version = ""
    version_planned_bump = False

    if not has_unpushed:
        change_paths = _collect_change_paths()
        _, porcelain, _ = run_git(["status", "--porcelain"], capture_output=True)

        if not porcelain.strip():
            print("[info] no changes to commit")
            if remote_exists:
                print("[done] in sync with remote")
            return

        saved_version = _sync_saved_version_with_head(readme_path, meta)
        version_for_msg = saved_version
        version_planned_bump = False

        if not no_bump and change_paths:
            kind = _ask_bump_kind(minor_flag=minor, no_bump=False)
            if kind == "minor":
                was_minor = True
                _maybe_backup_git_for_minor(
                    current_version=saved_version,
                    skip=skip_git_backup,
                )
                version_for_msg = meta.bump_minor(saved_version)
                print(f"[info] version minor: {saved_version} -> {version_for_msg}")
            elif kind == "patch":
                version_for_msg = meta.bump_patch(saved_version)
                print(f"[info] version patch: {saved_version} -> {version_for_msg}")
            version_planned_bump = True

        # DryRun mode
        if dry_run:
            print("")
            print("=" * 60)
            print("  [DryRun] preview mode - no files modified, no push")
            print("=" * 60)
            print(f"  current version:   {saved_version}")
            if version_planned_bump:
                print(f"  target version:    {version_for_msg}")
                print(f"  bump type:         {'Minor' if was_minor else 'Patch'}")
            else:
                print("  version bump:      skipped")
            print(f"  branch:            {WORK_BRANCH}")
            print(f"  changed files:     {len(change_paths)}")
            for p in sorted(change_paths):
                print(f"    - {p}")
            if was_minor:
                print(f"  minor action:      merge {WORK_BRANCH} -> {RELEASE_BRANCH}")
            if push_tag:
                tag = f"v{version_for_msg if version_planned_bump else saved_version}"
                print(f"  tag:               {tag}")
            print("=" * 60)
            print("  [DryRun] done - run without --dry-run to execute")
            print("=" * 60)
            return

        title, bullets = meta.summarize_changes(change_paths)
        meta.write_summary_block(readme_path, title, bullets)
        print(f"[info] wrote summary to {readme_path.name} footer")

        from scripts._version import ensure_summary_marker_assignments

        if ensure_summary_marker_assignments(readme_path):
            print("[info] fixed SUMMARY_BEGIN/SUMMARY_END constants")

        _stage_upload_changes(change_paths, readme_path)

        if not _run_pre_commit_on_staged():
            _rollback_upload_draft(
                readme_path,
                meta,
                saved_version=saved_version,
                restore_version=False,
            )
            sys.exit(1)

        if version_planned_bump:
            meta.write_version(readme_path, version_for_msg)

        _refresh_staging_for_commit(change_paths, readme_path)

        print("[info] pre-commit after version write...")
        if not _run_pre_commit_on_staged():
            _rollback_upload_draft(
                readme_path,
                meta,
                saved_version=saved_version,
                restore_version=version_planned_bump,
            )
            sys.exit(1)

        title_read, bullets_read = meta.read_summary_for_commit(readme_path)
        commit_msg = meta.build_commit_message(
            version_for_msg, title_read, bullets_read
        )

        meta.remove_summary_block(readme_path)
        print(f"[info] removed UPLOAD_SUMMARY block from {readme_path.name}")
        run_git(["add", _version_file_relpath(readme_path)])

        print("[info] pre-commit after removing summary block...")
        if not _run_pre_commit_on_staged(rounds=2):
            _rollback_upload_draft(
                readme_path,
                meta,
                saved_version=saved_version,
                restore_version=version_planned_bump,
            )
            sys.exit(1)

        print(signing_status_message(resolve_signing_config()))
        print(f"[info] git commit:\n{commit_msg.splitlines()[0]} ...")

        try:
            _commit_with_message(commit_msg)
        except subprocess.CalledProcessError:
            _rollback_upload_draft(
                readme_path,
                meta,
                saved_version=saved_version,
                restore_version=version_planned_bump,
            )
            sys.exit(1)

        created_commit = True
    else:
        head_version = _read_version_from_git_head(readme_path)
        if head_version and re.match(r"^\d+\.\d+\.0$", head_version):
            was_minor = True
            print(
                f"[info] HEAD version {head_version} is minor, "
                f"will auto-merge {RELEASE_BRANCH} after push"
            )
        print("[info] skipping new commit, pushing existing commits only")

    try:
        push_succeeded = _push_to_remote()
    except subprocess.CalledProcessError:
        push_succeeded = False
        if version_planned_bump and created_commit:
            print("[info] push failed, rolling back _VERSION...")
            meta.write_version(readme_path, saved_version)
            print(f"[info] rolled back _VERSION -> {saved_version}")
            print("[info] version restored; fix and rerun upload script")
        print(
            "[warn] push failed; local commit preserved, "
            "rerun with --no-bump to retry push"
        )
        raise

    if push_succeeded:
        try:
            if _should_merge_to_release(was_minor=was_minor):
                _merge_work_into_release(
                    meta=meta,
                    readme_path=readme_path,
                    push_tag=push_tag,
                )
            elif push_tag:
                print(
                    "[info] --tag skipped: only minor uploads get tags, "
                    "use --minor or input M"
                )
        except subprocess.CalledProcessError:
            print(
                f"[warn] {WORK_BRANCH} pushed but merge to "
                f"{RELEASE_BRANCH} failed, manual merge needed"
            )
            raise

    if push_succeeded and created_commit:
        print(f"[info] current _VERSION = {meta.read_version(readme_path)}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Push this repo to GitHub over SSH and update _VERSION.",
    )

    parser.add_argument(
        "--minor",
        action="store_true",
        help="bump minor version (second segment +1)",
    )

    parser.add_argument(
        "--no-bump",
        action="store_true",
        help="do not bump _VERSION this time",
    )

    parser.add_argument(
        "--tag",
        action="store_true",
        help="push git tag (v{version}) to trigger GitHub Actions build",
    )

    parser.add_argument(
        "--skip-pull",
        action="store_true",
        help="skip remote pull",
    )

    parser.add_argument(
        "--force-push",
        action="store_true",
        help="use --force-with-lease to overwrite remote history",
    )

    parser.add_argument(
        "--no-git-backup",
        action="store_true",
        help="skip .git backup on minor upload",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="only check repo state, no pull/commit/push",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview mode: show plan without modifying or pushing",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entry point. Execute full git commit and push flow."""
    global FORCE_PUSH

    args = parse_args()

    if args.minor and args.no_bump:
        print("[error] --minor and --no-bump cannot be used together")
        sys.exit(1)

    if args.force_push:
        FORCE_PUSH = True

    print("=" * 60)
    print("GitHub upload script (SSH)")
    print("=" * 60)

    try:
        setup_git_repo()
        if not preflight_upload(check_only=args.check):
            sys.exit(1)
        if args.check:
            sys.exit(0)

        if not args.dry_run and not sync_with_remote(skip_pull=args.skip_pull):
            print("[abort] remote sync failed")
            sys.exit(1)

        commit_and_push(
            minor=args.minor,
            no_bump=args.no_bump,
            push_tag=args.tag,
            skip_git_backup=args.no_git_backup,
            dry_run=args.dry_run,
        )

        print("=" * 60)
        print("[done]")
        print("=" * 60)

    except Exception as exc:
        print(f"\n[error] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
