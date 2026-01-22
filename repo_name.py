import sys


def main() -> None:
    import subprocess

    def get_repo_full_name() -> str | None:
        """Returns 'org/repo' or 'user/repo' from git remote."""
        try:
            url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()

            # SSH: git@github.com:org/repo.git
            if ":" in url and "@" in url:
                path = url.split(":")[-1]
            # HTTPS: https://github.com/org/repo.git
            else:
                path = "/".join(url.split("/")[-2:])

            return path.removesuffix(".git")
        except subprocess.CalledProcessError:
            return None

    print(f"Repository full name: {get_repo_full_name()}")


if __name__ == "__main__":
    sys.exit(main())
