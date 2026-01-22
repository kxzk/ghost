# /// script
# dependencies = ["modal"]
# ///
import modal

image = (
    modal.Image.debian_slim()
    .apt_install("curl", "git")
    .run_commands(
        # gh cli
        "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
        "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | tee /etc/apt/sources.list.d/github-cli.list > /dev/null",
        "apt update && apt install gh -y",
        # claude code
        "curl -fsSL https://claude.ai/install.sh | bash",
    )
)

app = modal.App.lookup("claude-code-test", create_if_missing=True)

sandbox = modal.Sandbox.create(
    image=image,
    secrets=[modal.Secret.from_name("<insert>")],
    app=app,
)


def run(cmd):
    print(f"\n>>> {cmd}")
    proc = sandbox.exec("bash", "-c", cmd)
    print(proc.stdout.read())
    err = proc.stderr.read()
    if err:
        print(f"STDERR: {err}")


# Test 1: gh auth
# run("echo $GH_TOKEN | gh auth login --with-token")
# run("gh auth status")
#
# Test 2: list repos from your org
run("gh repo list <org> --limit 5")

# Test 3: claude code installed?
run("which claude || echo 'claude not in PATH'")
run('export PATH="$HOME/.local/bin:$PATH" && claude --version')

# Test 4: claude code can reach bedrock?
run("""
export PATH="$HOME/.local/bin:$PATH"
echo "Say hello in 5 words" | claude -p \
    --allowedTools "Bash,Write,Read" \
    --permission-mode acceptEdits
""")

# Cleanup
sandbox.terminate()
