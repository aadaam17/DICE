# DICE Operations

## Setup A Virtual Environment

From the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

If PowerShell blocks activation scripts, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Activate the same environment in every new terminal:

```powershell
.\.venv\Scripts\Activate.ps1
```

Set a secret password before creating jobs with private keys:

```powershell
$env:DICE_SECRET_PASSWORD = "use-a-long-random-password"
```

Use the same value in the daemon terminal and any terminal that imports private keys through the
TUI. DICE stores encrypted private key files in `storage/secrets` and stores only secret references
inside job JSON.

What this password does:

- It is used to derive the encryption key for private-key storage.
- It is not written into the job file.
- It is required again when the daemon later needs to decrypt the private key for signing.
- Losing it means the encrypted private key cannot be recovered by DICE.
- Leaking it together with `storage/secrets` can expose the private key.

## Test

```powershell
python -m pytest
```

## Run The Daemon

Start the long-running service:

```powershell
dice-daemon
```

Without installing entry points:

```powershell
python -m dice.service.daemon
```

By default, the daemon listens on:

```text
127.0.0.1:8765
```

It loads jobs from `storage/jobs` and starts every job with `enabled: true`.

Job logs are written to `logs/<job-id>.log`.

## RPC Modes

Use `mock://local` for local testing. It runs the watcher/executor flow without reaching a chain.

Use a real HTTP RPC endpoint for real EVM execution. Real execution requires the private key to be
imported, the daemon to have `DICE_SECRET_PASSWORD`, and the job to include a contract address plus
ABI path.

Before real execution, run `Check` in the TUI. DICE verifies the job configuration, plugin rules,
RPC connectivity, signer key, contract bytecode, ABI function, and transaction simulation where
applicable. The simulation builds the transaction and estimates gas without signing or broadcasting.
`Start` runs the same preflight automatically and refuses to launch jobs with failed checks.

## Run The TUI

Open the interactive interface:

```powershell
dice
```

Without installing entry points:

```powershell
python -m dice.app.main
```

You can also launch the package entry point directly:

```powershell
python -m dice
```

When the daemon is available, the TUI attaches to it. If the daemon is unavailable, the TUI runs in
embedded development mode.

## Current TUI Workflow

The TUI is organized into three areas:

- Sidebar navigation.
- Jobs table and selected-job actions.
- Right-side workflow panel.

The sidebar presents the operator choices:

```text
Home
Create Job
View Jobs
Logs
Global Settings
Exit
```

Choose `Create Job` to walk through:

1. Job type selection from the plugin registry.
2. Blockchain selection.
3. RPC endpoint.
4. Wallet configuration.
5. Sweep type.
6. Staking information.
7. Unlock method: manual, event, timestamp, block, claimable function, or balance change.
8. Withdrawal function.
9. Gas strategy.
10. Retry policy and summary.

Choose `View Jobs` to work with existing jobs. Select a row and use the action strip above the jobs
table: `Check`, `Start`, `Stop`, `Edit`, `Duplicate`, `Delete`, or `Refresh`. Use sidebar `Logs` to
inspect the selected job.

Recommended job start flow:

1. Select the job row.
2. Choose `Check`.
3. Fix any failed preflight result.
4. Choose `Start`.

For copyable values to enter in each wizard field, see [Job Input Examples](job-examples.md).

## Troubleshooting Start And Check

If `Start` or `Check` appears slow, DICE is usually running preflight against the selected RPC.
For real RPC jobs, preflight may need to connect to the chain, verify chain ID, decrypt the wallet
key, inspect contract bytecode, load the ABI, and simulate gas.

If you are only testing the app flow, use:

```text
HTTP RPC: mock://local
```

If you use a real RPC like `http://localhost:8545`, make sure that RPC node is actually running.
Otherwise DICE will fail preflight with an RPC connection error.

The backend already exposes built-in job plugins through the registry. Current plugins are:

- Stake Sweep
- Token Sweep
- Scheduled Transfer
- Wallet Watch
- Contract Call
- Balance Trigger
- Event Trigger
- Custom Workflow

## Recommended Server Workflow

1. Start `dice-daemon` under your process manager.
2. SSH into the server when you need to operate DICE.
3. Run `dice`.
4. Manage jobs, inspect status, and exit when done.
5. Leave the daemon running in the background.

On Linux, the daemon should eventually be installed as a `systemd` service. On Windows, it can be
run under Task Scheduler or a service wrapper.
