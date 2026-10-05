"""macOS deny-default child confinement, also used for shell replay.

The broker port is the only network grant. Descendants inherit the sandbox;
setsid, Bash, curl, hooks and a second CLI cannot acquire a different grant.
The real credential and ledger remain in the unsandboxed trusted controller.
"""

import contextlib
import json
import os
import selectors
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from tests.evaluation_budget import BudgetStop


def profile(scratch: Path, reads: list[Path], port: int | None = None) -> str:
    def literal(path):
        return json.dumps(str(path))

    # '/' itself is needed by dyld. No user-home subtree or broad /tmp grant.
    rules = [
        "(version 1)",
        '(deny default (with message "CI_JOINT_OFFLINE"))',
        "(allow process-exec process-fork)",
        "(allow signal (target same-sandbox))",
        "(allow file-read-metadata)",
        '(allow file-read* (literal "/") (subpath "/usr") (subpath "/bin") '
        '(subpath "/System") (subpath "/Library/Apple") '
        '(subpath "/private/var/db/dyld") (subpath "/private/var/db/timezone") '
        '(literal "/private/etc/ssl/openssl.cnf") (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
        '(allow sysctl-read (require-not (sysctl-name-regex #"^kern\\.proc")))',
        "(allow process-info* (target self))",
        "(allow mach-priv-task-port (target self))",
        '(allow sysctl-write (sysctl-name "kern.tcsm_enable"))',
        "(allow system-socket (require-all (socket-domain AF_SYSTEM) (socket-protocol 2)))",
        '(allow mach-lookup (global-name "com.apple.system.opendirectoryd.libinfo") '
        '(global-name "com.apple.system.opendirectoryd.membership") '
        '(global-name "com.apple.system.logger") (global-name "com.apple.logd") '
        '(global-name "com.apple.bsd.dirhelper"))',
        '(allow file-write-data file-ioctl (literal "/dev/null"))',
        f"(allow file-read* file-write* (subpath {literal(scratch.resolve())}))",
    ]
    for path in reads:
        path = path.resolve(strict=True)
        kind = "subpath" if path.is_dir() else "literal"
        rules.append(f"(allow file-read* ({kind} {literal(path)}))")
    if port is not None:
        if type(port) is not int or not 1024 <= port <= 65535:
            raise BudgetStop("invalid broker port")
        rules.append(f'(allow network-outbound (remote ip "localhost:{port}"))')
    return "\n".join(rules)


class Sandbox:
    def __init__(
        self, claude: Path, cli_bin: Path, runtime: list[Path], plugins: list[Path]
    ):
        self.claude = claude.resolve(strict=True)
        self.cli_bin = cli_bin.resolve(strict=True)
        self.reads = [self.claude, self.cli_bin.parent, *runtime, *plugins]

    def run(
        self,
        argv,
        *,
        prompt="",
        timeout=120,
        port=None,
        on_line=None,
        broker_token=None,
        stop_requested=None,
    ):
        with tempfile.TemporaryDirectory(prefix="joint-sandbox-") as directory:
            scratch = Path(directory).resolve()
            env = {
                "HOME": str(scratch),
                "TMPDIR": str(scratch),
                "CLAUDE_CONFIG_DIR": str(scratch / ".claude"),
                "CLAUDE_CODE_TMPDIR": str(scratch),
                "PATH": f"{self.cli_bin}:/usr/bin:/bin",
                "LANG": "en_US.UTF-8",
                "CONFLUENCE_AS_TRANSPORT": "simulation",
                "CONFLUENCE_ALLOWED_SPACES": "DOCS",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                "DISABLE_AUTOUPDATER": "1",
                "DISABLE_TELEMETRY": "1",
                "DISABLE_ERROR_REPORTING": "1",
                "OPENSSL_CONF": "/dev/null",
            }
            if port is not None and Path(argv[0]).resolve() == self.claude:
                if not broker_token:
                    raise BudgetStop("local broker capability required")
                # The capability authenticates this one local broker session;
                # it is not a subscription/provider credential. No auth env
                # variable is supplied to this process or any descendant.
                capability = scratch / "broker-capability"
                capability.write_text(broker_token)
                capability.chmod(0o600)
                settings = {
                    "disableAllHooks": True,
                    "apiKeyHelper": f"/bin/cat {capability}",
                }
                argv = list(argv)
                if "--settings" in argv:
                    index = argv.index("--settings") + 1
                    original = json.loads(argv[index])
                    original.update(settings)
                    argv[index] = json.dumps(original)
                else:
                    argv.extend(["--settings", json.dumps(settings)])
                env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}"
            command = [
                "/usr/bin/sandbox-exec",
                "-p",
                profile(scratch, self.reads, port),
                *argv,
            ]
            try:
                process = subprocess.Popen(
                    command,
                    cwd=scratch,
                    env=env,
                    text=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                selector = selectors.DefaultSelector()
                collected = {process.stdout: bytearray(), process.stderr: bytearray()}
                for pipe in collected:
                    selector.register(pipe, selectors.EVENT_READ)
                process.stdin.write(prompt)
                process.stdin.close()
                deadline = time.monotonic() + timeout
                line_buffer = bytearray()
                try:
                    while selector.get_map():
                        if stop_requested is not None and stop_requested():
                            return 130, *(
                                bytes(collected[p]).decode("utf-8", errors="replace")
                                for p in (process.stdout, process.stderr)
                            )
                        if time.monotonic() >= deadline:
                            raise BudgetStop(
                                "sandbox child timeout; reservation retained"
                            )
                        for key, _ in selector.select(
                            min(0.1, max(0, deadline - time.monotonic()))
                        ):
                            chunk = os.read(key.fileobj.fileno(), 65536)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            collected[key.fileobj].extend(chunk)
                            if key.fileobj is process.stdout and on_line is not None:
                                line_buffer.extend(chunk)
                                while b"\n" in line_buffer:
                                    line, _, remainder = line_buffer.partition(b"\n")
                                    line_buffer = bytearray(remainder)
                                    if on_line(line.decode("utf-8", errors="replace")):
                                        return 0, *(
                                            bytes(collected[p]).decode(
                                                "utf-8", errors="replace"
                                            )
                                            for p in (process.stdout, process.stderr)
                                        )
                            if sum(len(v) for v in collected.values()) > 8_000_000:
                                raise BudgetStop(
                                    "sandbox output limit; reservation retained"
                                )
                    process.wait(timeout=max(0.1, deadline - time.monotonic()))
                    return process.returncode, *(
                        bytes(collected[p]).decode("utf-8", errors="replace")
                        for p in (process.stdout, process.stderr)
                    )
                finally:
                    selector.close()
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    process.stdout.close()
                    process.stderr.close()
            except subprocess.TimeoutExpired:
                raise BudgetStop(
                    "sandbox child timeout; reservation retained"
                ) from None
            except OSError:
                raise BudgetStop("sandbox child unavailable") from None

    def check(self):
        rc, _, _ = self.run(["/usr/bin/true"], timeout=5)
        if rc:
            raise BudgetStop("deny-default sandbox unavailable")
