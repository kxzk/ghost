# /// script
# dependencies = ["modal"]
# ///
import os
import subprocess
from secrets import token_urlsafe

import modal


def get_remote_url() -> str:
    try:
        return subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Not in a git repository with a remote origin") from e


def get_repo_name(url: str) -> str:
    return url.removesuffix(".git").replace(":", "/").split("/")[-1]


def main() -> None:
    url = get_remote_url()
    repo_name = get_repo_name(url)
    ghost_id = f"ghost-{token_urlsafe(4)}"
    print(f"👻 [{ghost_id}] Cloning {repo_name}...")

    image = (
        modal.Image.debian_slim()
        .apt_install("curl", "git")
        .run_commands(
            # github (gh) cli
            "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
            "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | tee /etc/apt/sources.list.d/github-cli.list > /dev/null",
            "apt update && apt install gh -y",
            # claude code
            "curl -fsSL https://claude.ai/install.sh | bash",
        )
    )

    app = modal.App.lookup(ghost_id, create_if_missing=True)

    sandbox = modal.Sandbox.create(
        image=image,
        secrets=[modal.Secret.from_name(os.environ["GHOST_SECRET_TOKEN"])],
        app=app,
    )

    def run(cmd: str) -> str:
        proc = sandbox.exec("bash", "-c", cmd)
        stdout = proc.stdout.read()
        proc.wait()
        return stdout

    run(f"gh repo clone {url} /workspace/{repo_name}")

    prompt = "Describe this repository in exactly one sentence."
    result = run(f"""
        export PATH="$HOME/.local/bin:$PATH"
        cd /workspace/{repo_name}
        echo "{prompt}" | claude -p --allowedTools "Read,Glob,Grep"
    """)

    print(f"👻 [{ghost_id}] {result.strip()}")

    sandbox.terminate()


if __name__ == "__main__":
    main()
