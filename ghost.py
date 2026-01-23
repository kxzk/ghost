# /// script
# dependencies = ["modal"]
# ///
import os
import sys
import subprocess
from secrets import token_urlsafe

import modal


def ghost_print(msg: str) -> None:
    print(f"👻 {msg}")


def get_remote_url() -> str:
    try:
        return subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Not in a git repository with a remote origin") from e


def get_repo_name(url: str) -> str:
    return url.removesuffix(".git").replace(":", "/").split("/")[-1]


def main(prompt: str) -> None:
    modal.enable_output()
    url = get_remote_url()
    repo_name = get_repo_name(url)
    ghost_id = f"ghost-{token_urlsafe(4)}"
    ghost_print(f"[{ghost_id}] spawning sandbox -> {repo_name}...")

    image = (
        modal.Image.debian_slim(python_version="3.12")
        .apt_install("curl")
        .run_commands(
            "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
            "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | tee /etc/apt/sources.list.d/github-cli.list > /dev/null",
        )
        .apt_install("gh")
        .uv_pip_install("claude-agent-sdk")
        .add_local_dir("src", "/src")
    )

    app = modal.App.lookup(ghost_id, create_if_missing=True)

    sandbox = modal.Sandbox.create(
        image=image, secrets=[modal.Secret.from_name(os.environ["GHOST_SECRET_TOKEN"])], app=app
    )

    ghost_print(f"[{ghost_id}] ghost clone -> {repo_name}...")
    clone_proc = sandbox.exec("gh", "repo", "clone", url, f"/workspace/{repo_name}")
    clone_proc.wait()

    ghost_print(f"[{ghost_id}] ghost do -> {prompt}")

    proc = sandbox.exec("python", "/src/agent.py", prompt)

    for line in proc.stdout:
        print(line, end="")

    stderr = proc.stderr.read()
    if stderr:
        print(f"[stderr] {stderr}", file=sys.stderr)

    proc.wait()
    sandbox.terminate()


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "List my Linear issues"
    main(prompt)
