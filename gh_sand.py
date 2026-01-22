# /// script
# dependencies = ["modal"]
# ///
import modal

# 1. Build image with gh installed
image = (
    modal.Image.debian_slim()
    .apt_install("curl")
    .run_commands(
        "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
        "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | tee /etc/apt/sources.list.d/github-cli.list > /dev/null",
        "apt update && apt install gh -y",
    )
)

app = modal.App.lookup("gh-sandbox", create_if_missing=True)

# 2. Store your GH token as a Modal secret (do this once via CLI or dashboard)
# modal secret create gh-token GH_TOKEN=ghp_xxxxx

# 3. Create sandbox with the secret injected
sandbox = modal.Sandbox.create(
    image=image,
    secrets=[modal.Secret.from_name("<org>-gh-token")],
    app=app,
)

# 4. Auth gh using the token (non-interactive)
process = sandbox.exec("bash", "-c", "echo $GH_TOKEN | gh auth login --with-token")
process.wait()

# Now gh is authenticated
process = sandbox.exec("gh", "repo", "list", "<org>", "--limit", "5")
print(process.stdout.read())
