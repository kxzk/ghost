# Ghost

CLI for autonomous codebase tasks via sandboxed Claude agents.

**Flow:**
```
ghost "<task>" → Modal sandbox → clone repo → Claude plans → Linear issue → Claude executes → GitHub draft PR
```

## Architecture

1. **Ingestion**: Parse natural language task, identify target repo
2. **Sandbox**: Spin up Modal container with repo clone + tooling (gh CLI, etc.)
3. **Planning Agent**: Claude analyzes codebase, generates structured execution plan
4. **Coordination**: Create Linear issue with plan as description (serves as work ticket + audit trail)
5. **Execution Agent**: Separate Claude session fetches Linear issue, implements plan in sandbox
6. **Output**: Create draft PR via `gh pr create --draft`

## Design Choices

- **Two-phase agent separation** (plan vs execute) for reviewability and retry isolation
- **Linear as coordination layer**—human can review/modify plan before execution proceeds
- **Modal sandbox** for hermetic execution (no local state pollution, reproducible)
- **Draft PR as output**—human remains in the loop for merge decision

## Formatting

After every series of changes, run the following commands to ensure code quality:

```bash
uvx ruff check .
uvx ruff check --select I . --fix
uvx ruff format .
```

## Modal Links

Modal Sandboxes: https://modal.com/docs/guide/sandboxes
Running Commands in Sandboxes: https://modal.com/docs/guide/sandbox-spawn
Networking and Security: https://modal.com/docs/guide/sandbox-networking
Filesystem Access: https://modal.com/docs/guide/sandbox-files
Snapshots: https://modal.com/docs/guide/sandbox-snapshots
