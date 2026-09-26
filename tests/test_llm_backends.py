"""app/llm.py: both backends behind one call shape, and the claude_cli safety rails.

Nothing here calls Claude. The CLI path is exercised end to end against a fake
``claude`` script that records its argv, stdin, working directory and
environment, so the real subprocess plumbing runs without the real binary.
"""
import json
import sys
import textwrap

import pytest

from app import claude_client, config, llm

# A real `claude -p --output-format json` success payload (CLI 2.1.283), trimmed to
# the keys we read plus a few we ignore. If a CLI upgrade changes this shape,
# parse_cli_output must change with it.
CLI_SUCCESS = {
    "type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
    "result": "Γεια σου! Πώς σε λένε;",
    "session_id": "0627383f-5d7e-44b4-b98e-e497b52fa868",
    "total_cost_usd": 0.0015,
    "usage": {"input_tokens": 248, "cache_creation_input_tokens": 10,
              "cache_read_input_tokens": 5, "output_tokens": 256},
    "api_error_status": None, "stop_reason": "end_turn",
}


# --- pure helpers --------------------------------------------------------------


def test_cli_env_keeps_the_subscription_token_and_drops_everything_that_would_override_it():
    parent = {
        "PATH": "/usr/bin", "HOME": "/home/tutor",
        "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat-secret",
        "ANTHROPIC_API_KEY": "sk-ant-api-key",     # outranks the OAuth token in the CLI
        "ANTHROPIC_AUTH_TOKEN": "bearer",          # outranks it too
        "CLAUDE_CODE_SESSION_ID": "abc",           # would join a parent Claude Code session
        "CLAUDE_CODE_CHILD_SESSION": "1",
        "DATABASE_URL": "postgresql://tutor:pw@db/greektutor",  # none of its business
    }
    env = llm.cli_env(parent, "/tmp/work")
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat-secret"
    assert env["PATH"] == "/usr/bin" and env["HOME"] == "/home/tutor"
    for dropped in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_SESSION_ID",
                    "CLAUDE_CODE_CHILD_SESSION", "DATABASE_URL"):
        assert dropped not in env
    assert env["DISABLE_AUTOUPDATER"] == "1"
    assert env["CLAUDE_CODE_TMPDIR"] == env["TMPDIR"] == "/tmp/work"


def test_cli_args_make_a_stateless_toolless_call_with_our_system_prompt():
    argv = llm.cli_args("/usr/bin/claude", model="claude-haiku-4-5", system_prompt_file="/w/s.txt")
    assert argv[:2] == ["/usr/bin/claude", "-p"]

    def value(flag):
        return argv[argv.index(flag) + 1]

    assert value("--output-format") == "json"
    assert value("--model") == "claude-haiku-4-5"
    assert value("--system-prompt-file") == "/w/s.txt"   # replaces Claude Code's prompt
    assert value("--tools") == ""                         # no tools at all
    assert value("--max-turns") == "1"
    for flag in ("--strict-mcp-config", "--safe-mode", "--no-session-persistence"):
        assert flag in argv
    assert "--bare" not in argv  # bare mode ignores CLAUDE_CODE_OAUTH_TOKEN


def test_flatten_labels_roles_in_order_and_ends_on_the_student():
    text = llm.flatten_transcript([
        {"role": "user", "content": "Γεια!"},
        {"role": "assistant", "content": "Γεια σου! Πώς σε λένε;\n"},
        {"role": "user", "content": " Με λένε Γιάννη. "},
    ])
    first, second, third = (text.index(s) for s in ("Γεια!", "Πώς σε λένε;", "Με λένε Γιάννη."))
    assert first < second < third
    assert text.count("[STUDENT]") == 2 and text.count("[TUTOR]") == 1
    assert text.rstrip().endswith("output only your response.")


def test_flatten_refuses_an_empty_transcript_or_one_ending_on_the_tutor():
    with pytest.raises(ValueError):
        llm.flatten_transcript([])
    with pytest.raises(ValueError):
        llm.flatten_transcript([{"role": "user", "content": "a"},
                                {"role": "assistant", "content": "b"}])


def test_parse_success_counts_uncached_plus_cache_writes_as_input():
    out = llm.parse_cli_output(json.dumps(CLI_SUCCESS), 0)
    assert out.text == "Γεια σου! Πώς σε λένε;"
    assert (out.tokens_in, out.tokens_out, out.cache_read) == (258, 256, 5)


def test_parse_failures_raise_llm_error_with_the_reason():
    err = dict(CLI_SUCCESS, is_error=True, subtype="success",
               result="Invalid API key · Please run /login")
    with pytest.raises(llm.LLMError, match="Please run /login"):
        llm.parse_cli_output(json.dumps(err), 1)
    with pytest.raises(llm.LLMError, match="error_max_turns"):
        llm.parse_cli_output(json.dumps(dict(CLI_SUCCESS, subtype="error_max_turns")), 0)
    with pytest.raises(llm.LLMError, match="without JSON"):
        llm.parse_cli_output("Error: unknown option '--safe-mode'", 1)
    with pytest.raises(llm.LLMError, match="missing"):
        llm.parse_cli_output(json.dumps({k: v for k, v in CLI_SUCCESS.items() if k != "result"}), 0)
    with pytest.raises(llm.LLMError, match="not an object"):
        llm.parse_cli_output("[]", 0)


# --- selection and the single-learner rule --------------------------------------


def test_make_backend_validates_its_configuration(monkeypatch):
    with pytest.raises(llm.LLMError, match="must be one of"):
        llm.make_backend("openai")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    with pytest.raises(llm.LLMError, match="ANTHROPIC_API_KEY"):
        llm.make_backend("api")
    monkeypatch.setattr(config, "CLAUDE_CLI_PATH", "definitely-not-a-real-claude-binary")
    with pytest.raises(llm.LLMError, match="not on PATH"):
        llm.make_backend("claude_cli")


class _Conn:
    def __init__(self, users):
        self.users = users

    async def fetchval(self, sql):
        assert "count(*) FROM users" in sql
        return self.users


async def test_single_learner_rule_only_applies_to_the_subscription_backend(monkeypatch):
    monkeypatch.setattr(config, "LLM_BACKEND", "api")
    await llm.assert_single_learner(_Conn(5))           # API key: any number of learners

    monkeypatch.setattr(config, "LLM_BACKEND", "claude_cli")
    await llm.assert_single_learner(_Conn(0))
    await llm.assert_single_learner(_Conn(1))
    with pytest.raises(llm.SingleLearnerError, match="LLM_BACKEND=api"):
        await llm.assert_single_learner(_Conn(2))


# --- the CLI subprocess path, end to end against a fake binary --------------------

FAKE_CLAUDE = textwrap.dedent("""\
    #!{python}
    import json, os, sys
    argv = sys.argv[1:]
    record = {{
        "argv": argv,
        "stdin": sys.stdin.read(),
        "cwd": os.getcwd(),
        "env": {{k: v for k, v in os.environ.items()
                 if k.startswith(("CLAUDE", "ANTHROPIC", "DISABLE"))}},
        "system": open(argv[argv.index("--system-prompt-file") + 1], encoding="utf-8").read(),
    }}
    with open({record_path!r}, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
    print({reply})
""")


@pytest.mark.skipif(sys.platform == "win32", reason="fake binary is a shebang script")
async def test_cli_backend_runs_the_binary_with_prompt_on_stdin_and_a_scrubbed_env(
        tmp_path, monkeypatch):
    record_path = tmp_path / "record.json"
    fake = tmp_path / "claude"
    fake.write_text(FAKE_CLAUDE.format(python=sys.executable, record_path=str(record_path),
                                       reply=repr(json.dumps(CLI_SUCCESS))), encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-must-not-leak")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat-token")

    backend = llm.ClaudeCliBackend(str(fake), timeout_s=30)
    out = await backend.complete(
        model="claude-haiku-4-5",
        system=[llm.SystemBlock("STATIC RULES", cache=True), llm.SystemBlock("STUDENT CONTEXT")],
        messages=[{"role": "user", "content": "Καλημέρα!"}],
        max_tokens=100,
    )

    assert out.text == CLI_SUCCESS["result"]
    rec = json.loads(record_path.read_text(encoding="utf-8"))
    assert rec["system"] == "STATIC RULES\n\nSTUDENT CONTEXT"
    assert "Καλημέρα!" in rec["stdin"] and "[STUDENT]" in rec["stdin"]
    assert rec["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat-token"
    assert "ANTHROPIC_API_KEY" not in rec["env"]
    assert "CLAUDE_CODE_SESSION_ID" not in rec["env"]
    assert rec["env"]["DISABLE_AUTOUPDATER"] == "1"
    assert "gt-claude-" in rec["cwd"]  # a throwaway dir: no CLAUDE.md or .mcp.json to pick up


@pytest.mark.skipif(sys.platform == "win32", reason="fake binary is a shebang script")
async def test_cli_backend_turns_a_hung_binary_into_an_llm_error(tmp_path):
    fake = tmp_path / "claude"
    fake.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n", encoding="utf-8")
    fake.chmod(0o755)
    with pytest.raises(llm.LLMError, match="timed out"):
        await llm.ClaudeCliBackend(str(fake), timeout_s=0.5).complete(
            model="m", system=[llm.SystemBlock("s")],
            messages=[{"role": "user", "content": "x"}], max_tokens=10)


# --- claude_client is backend-agnostic ---------------------------------------------


class _FakeBackend:
    name = "fake"

    def __init__(self, text):
        self.text = text
        self.calls = []

    async def complete(self, *, model, system, messages, max_tokens):
        self.calls.append({"model": model, "system": system, "messages": messages})
        return llm.Completion(text=self.text, tokens_in=11, tokens_out=7)


async def test_tutor_turn_goes_through_whichever_backend_is_configured(monkeypatch):
    reply = 'Πολύ καλά!\n\n```json\n{"vocab_events": [], "objective_progress": 0.4}\n```'
    fake = _FakeBackend(reply)
    monkeypatch.setattr(llm, "_backend", fake)
    text, meta, tok_in, tok_out = await claude_client.tutor_turn(
        "CONTEXT", [{"role": "user", "content": "Είμαι καλά"}])
    assert text == "Πολύ καλά!"
    assert meta["objective_progress"] == 0.4
    assert (tok_in, tok_out) == (11, 7)
    call = fake.calls[0]
    assert call["model"] == config.TUTOR_MODEL
    assert call["system"][0].cache and not call["system"][1].cache  # static prompt cached
    assert call["system"][1].text == "CONTEXT"


async def test_evaluate_session_parses_json_from_either_backend(monkeypatch):
    fake = _FakeBackend('```json\n{"summary": "ok", "error_patterns": ["gender_agreement"], '
                        '"lesson_score": 0.8, "level_recommendation": "keep"}\n```')
    monkeypatch.setattr(llm, "_backend", fake)
    data, _, _ = await claude_client.evaluate_session([{"role": "user", "content": "a"},
                                                       {"role": "assistant", "content": "b"}])
    assert data["lesson_score"] == 0.8
    assert fake.calls[0]["model"] == config.EVAL_MODEL
    assert fake.calls[0]["messages"][-1]["role"] == "user"  # CLI flattening needs this
