"""Model backends: one call shape for the tutor, two ways to reach Claude.

``LLM_BACKEND=api`` (default)
    The Anthropic Python SDK with ``ANTHROPIC_API_KEY``. Pay per token; any number
    of learners; prompt caching under our control.

``LLM_BACKEND=claude_cli``
    Runs the unmodified ``claude`` binary (Claude Code) once per call, signed in
    with the learner's own Claude subscription (``claude setup-token`` →
    ``CLAUDE_CODE_OAUTH_TOKEN``, or an existing ``claude /login`` on bare metal).
    Anthropic's terms allow a user to sign in to the unmodified binary with their
    own plan, and forbid routing other people's requests through it — so this
    backend is **single-learner only**, enforced in ``assert_single_learner`` and at
    signup. See README → "Choosing how the app talks to Claude".

Everything that shapes a CLI call (argument list, child environment, transcript
flattening, output parsing) is a pure function so it is tested without the
binary. The only I/O is ``ClaudeCliBackend.complete`` and the learner-count check.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from . import config

log = logging.getLogger(__name__)

BACKENDS = ("api", "claude_cli")
ERROR_SNIPPET = 300  # chars of CLI output kept in an error message


class LLMError(RuntimeError):
    """The model call failed; the message is safe to log (no credentials)."""


class SingleLearnerError(RuntimeError):
    """claude_cli mode found more than one account."""


@dataclass(frozen=True)
class SystemBlock:
    text: str
    cache: bool = False  # api backend: mark as a prompt-cache breakpoint


@dataclass(frozen=True)
class Completion:
    text: str
    tokens_in: int
    tokens_out: int
    cache_read: int = 0


class Backend(Protocol):
    name: str

    async def complete(self, *, model: str, system: list[SystemBlock],
                       messages: list[dict[str, str]], max_tokens: int) -> Completion: ...


# --- api ---------------------------------------------------------------------


class ApiBackend:
    """Anthropic Messages API via the Python SDK."""

    name = "api"

    def __init__(self, api_key: str) -> None:
        from anthropic import AsyncAnthropic  # imported lazily: CLI-only installs may lack it

        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(self, *, model: str, system: list[SystemBlock],
                       messages: list[dict[str, str]], max_tokens: int) -> Completion:
        blocks: list[dict[str, Any]] = []
        for b in system:
            block: dict[str, Any] = {"type": "text", "text": b.text}
            if b.cache:
                block["cache_control"] = {"type": "ephemeral"}
            blocks.append(block)
        from anthropic import APIError

        try:
            resp = await self._client.messages.create(
                model=model, max_tokens=max_tokens, system=blocks, messages=messages,
            )
        except APIError as e:
            detail = str(e)[:ERROR_SNIPPET]
            raise LLMError(f"Anthropic API error: {type(e).__name__}: {detail}") from e
        text = "".join(b.text for b in resp.content if b.type == "text")
        usage = resp.usage
        return Completion(
            text=text,
            tokens_in=usage.input_tokens + (getattr(usage, "cache_creation_input_tokens", 0) or 0),
            tokens_out=usage.output_tokens,
            cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )


# --- claude_cli: pure helpers ------------------------------------------------

# Only these variables reach the child. Everything else — in particular any
# CLAUDE_CODE_* / ANTHROPIC_* inherited from a Claude Code terminal you started
# uvicorn from — is dropped, because the CLI would otherwise join that session
# or prefer an API key over the subscription token (API key outranks
# CLAUDE_CODE_OAUTH_TOKEN in the CLI's auth precedence).
CLI_ENV_ALLOW = (
    "PATH", "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
    "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "PATHEXT", "WINDIR", "PROGRAMDATA",
    "LANG", "LC_ALL", "TZ",
    "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy",
    "SSL_CERT_FILE", "NODE_EXTRA_CA_CERTS",
    "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR",
)


def cli_env(parent: dict[str, str], workdir: str) -> dict[str, str]:
    """The child's environment: an allowlist of the parent's, plus fixed switches."""
    env = {k: v for k, v in parent.items() if k in CLI_ENV_ALLOW}
    env["DISABLE_AUTOUPDATER"] = "1"  # the image pins a version; don't drift mid-run
    env["CLAUDE_CODE_TMPDIR"] = workdir  # the CLI refuses temp dirs it doesn't own
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = workdir
    return env


def cli_args(binary: str, *, model: str, system_prompt_file: str) -> list[str]:
    """argv for one stateless, tool-less, customization-free print-mode call."""
    return [
        binary, "-p",
        "--output-format", "json",
        "--model", model,
        "--system-prompt-file", system_prompt_file,  # replace, not append to, Claude Code's prompt
        "--tools", "",                 # a tutor needs no tools
        "--strict-mcp-config",         # no MCP servers from any config
        "--safe-mode",                 # skip your CLAUDE.md, hooks, plugins, skills
        "--no-session-persistence",    # nothing written to ~/.claude/projects
        "--max-turns", "1",
    ]


ROLE_LABEL = {"user": "STUDENT", "assistant": "TUTOR"}


def flatten_transcript(messages: list[dict[str, str]]) -> str:
    """The CLI takes one prompt, not a message list: render the conversation as text.

    The last message is the one to answer. Earlier tutor turns are shown without
    their JSON blocks (the app strips them before storing), which is fine: the
    system prompt restates the contract every call.
    """
    if not messages:
        raise ValueError("no messages to send")
    if messages[-1]["role"] != "user":
        raise ValueError("the last message must be the student's")
    lines = ["Conversation so far, oldest first. Each turn is delimited by a [ROLE] tag.", ""]
    for m in messages:
        lines.append(f"[{ROLE_LABEL[m['role']]}]")
        lines.append(m["content"].strip())
        lines.append("")
    # Neutral wording: the same flattening serves tutor turns and the session evaluation.
    lines.append("Respond to the last message above. Follow your system instructions exactly, "
                 "including any required output format, and output only your response.")
    return "\n".join(lines)


def parse_cli_output(stdout: str, returncode: int) -> Completion:
    """Parse ``claude -p --output-format json``; raise LLMError on any failure shape."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise LLMError(
            f"claude CLI exited {returncode} without JSON: {stdout.strip()[:ERROR_SNIPPET]!r}"
        ) from None
    if not isinstance(data, dict):
        raise LLMError("claude CLI returned JSON that is not an object")
    result = data.get("result")
    if returncode != 0 or data.get("is_error") or data.get("subtype") != "success":
        detail = result if isinstance(result, str) else data.get("subtype")
        raise LLMError(f"claude CLI failed ({returncode}, {data.get('subtype')}): "
                       f"{str(detail)[:ERROR_SNIPPET]}")
    if not isinstance(result, str):
        raise LLMError("claude CLI result is missing")
    usage = data.get("usage") or {}
    return Completion(
        text=result,
        tokens_in=int(usage.get("input_tokens") or 0)
        + int(usage.get("cache_creation_input_tokens") or 0),
        tokens_out=int(usage.get("output_tokens") or 0),
        cache_read=int(usage.get("cache_read_input_tokens") or 0),
    )


def resolve_cli(path: str) -> str:
    """Full path to the claude binary (PATH lookup; handles claude.exe on Windows)."""
    found = shutil.which(path)
    if not found:
        raise LLMError(
            f"LLM_BACKEND=claude_cli but {path!r} is not on PATH. Install Claude Code "
            "(Docker: build with WITH_CLAUDE_CLI=true) or set CLAUDE_CLI_PATH."
        )
    return found


# --- claude_cli: I/O ---------------------------------------------------------


class ClaudeCliBackend:
    """One ``claude -p`` process per call, in a throwaway working directory."""

    name = "claude_cli"

    def __init__(self, binary: str, timeout_s: float) -> None:
        self._binary = binary
        self._timeout = timeout_s

    async def complete(self, *, model: str, system: list[SystemBlock],
                       messages: list[dict[str, str]], max_tokens: int) -> Completion:
        # max_tokens has no CLI flag; the tutor's replies are short by instruction.
        prompt = flatten_transcript(messages)
        with tempfile.TemporaryDirectory(prefix="gt-claude-") as work:
            sys_file = Path(work) / "system.txt"
            sys_file.write_text("\n\n".join(b.text for b in system), encoding="utf-8")
            argv = cli_args(self._binary, model=model, system_prompt_file=str(sys_file))
            # A blocking run in a worker thread, not asyncio subprocesses: on Windows,
            # uvicorn may run a SelectorEventLoop, which cannot spawn subprocesses.
            try:
                proc = await asyncio.to_thread(
                    subprocess.run, argv, cwd=work, env=cli_env(dict(os.environ), work),
                    input=prompt.encode("utf-8"), capture_output=True, timeout=self._timeout,
                )
            except subprocess.TimeoutExpired:
                raise LLMError(f"claude CLI timed out after {self._timeout:.0f}s") from None
        if proc.stderr:
            log.debug("claude CLI stderr: %s",
                      proc.stderr.decode("utf-8", "replace")[:ERROR_SNIPPET])
        return parse_cli_output(proc.stdout.decode("utf-8", "replace"), proc.returncode)


# --- selection + the single-learner rule --------------------------------------

_backend: Backend | None = None


def backend() -> Backend:
    """The configured backend, created on first use (so tests can import freely)."""
    global _backend
    if _backend is None:
        _backend = make_backend(config.LLM_BACKEND)
    return _backend


def make_backend(name: str) -> Backend:
    if name == "api":
        if not config.ANTHROPIC_API_KEY:
            raise LLMError("LLM_BACKEND=api needs ANTHROPIC_API_KEY.")
        return ApiBackend(config.ANTHROPIC_API_KEY)
    if name == "claude_cli":
        return ClaudeCliBackend(resolve_cli(config.CLAUDE_CLI_PATH), config.CLAUDE_CLI_TIMEOUT)
    raise LLMError(f"LLM_BACKEND must be one of {BACKENDS}, got {name!r}")


def is_single_learner_mode() -> bool:
    return config.LLM_BACKEND == "claude_cli"


async def assert_single_learner(conn: Any) -> None:
    """In claude_cli mode, refuse to serve if more than one account exists.

    A personal Claude subscription may only carry its owner's requests. Called at
    startup and before every session start; signup is gated separately.
    """
    if not is_single_learner_mode():
        return
    n = await conn.fetchval("SELECT count(*) FROM users")
    if n > 1:
        raise SingleLearnerError(
            f"LLM_BACKEND=claude_cli runs on one person's Claude subscription, but {n} "
            "accounts exist. Switch to LLM_BACKEND=api (API key) for more than one learner."
        )
