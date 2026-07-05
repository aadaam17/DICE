# DICE

Licensed under the Apache License 2.0.

DICE means **Deterministic Intelligent Chain Executor**. It is a Python 3.12+
terminal application for managing independent blockchain execution jobs.

This first build provides:

- JSON-backed job storage
- Async job lifecycle management
- A daemon/client architecture so jobs can outlive the TUI
- A workflow model built from triggers, conditions, and actions
- A job plugin registry for extensible automation templates
- Chain adapter interfaces and EVM chain profiles
- A Web3-based EVM adapter for real RPC execution
- Encrypted private-key references and a signer layer
- Preflight checks before jobs start
- Non-broadcast transaction simulation with gas and max-cost estimates
- Watcher, trigger, builder, broadcaster, and executor boundaries
- A Textual dashboard for viewing and starting/stopping jobs
- A `mock://` execution path suitable for local development

## Setup

For local development from the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

After DICE is published, install the packaged app with:

```powershell
python -m pip install dice-chain-executor
```

Then run:

```powershell
dice
dice-daemon
```

Note: `pip install dice` installs an existing unrelated PyPI package. This project uses the PyPI
distribution name `dice-chain-executor` while keeping the command name `dice`.

If PowerShell blocks activation scripts, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

After setup, activate the environment in every new terminal before running DICE:

```powershell
.\.venv\Scripts\Activate.ps1
```

Before creating jobs with private keys, set the secret password in the daemon terminal:

```powershell
$env:DICE_SECRET_PASSWORD = "use-a-long-random-password"
```

DICE encrypts imported private keys into `storage/secrets` and stores only a `secret://...`
reference in each job file.

`DICE_SECRET_PASSWORD` is the master password for that encryption. When you enter a private key,
DICE derives an encryption key from this password, encrypts the private key, and writes only the
encrypted ciphertext to `storage/secrets/<job-id>.json`. If someone opens the job JSON, they will
only see a reference such as:

```json
"private_key_ref": "secret://wallets/job-0001"
```

Keep this password safe. If you lose it, DICE cannot decrypt the saved private key later. If someone
gets both the encrypted secret file and this password, they can unlock the private key.

## Run

```powershell
dice-daemon
dice
```

If you do not install the package, you can run the daemon and TUI directly:

```powershell
python -m dice.service.daemon
python -m dice.app.main
```

You can also launch the TUI package entry point directly:

```powershell
python -m dice
```

The TUI attaches to the daemon at `127.0.0.1:8765` when it is running. If no daemon is available,
the TUI falls back to embedded development mode.

## Real RPC Vs Mock RPC

Use `mock://local` when testing the DICE workflow without sending blockchain transactions.

Use a real HTTP RPC URL when you want the Web3 EVM adapter:

```text
https://...
http://...
```

Real execution currently requires:

- a supported EVM chain profile
- a reachable RPC whose chain ID matches the selected chain
- an encrypted private-key reference
- a staking/target contract address
- an ABI file path
- a function name and arguments that exist in the ABI

Before a job starts, DICE runs preflight checks. The manager verifies the saved configuration,
plugin rules, RPC connectivity, wallet key availability, signer address, contract bytecode, ABI
function, and transaction simulation where those checks apply. Real EVM simulation builds the
transaction, estimates gas, and shows the maximum native-token fee without signing or broadcasting.
If any required check fails, the job is marked `error` and does not start.

## Job Plugins

DICE treats job types as plugins. Built-in plugins include:

- Stake Sweep
- Token Sweep
- Scheduled Transfer
- Wallet Watch
- Contract Call
- Balance Trigger
- Event Trigger
- Custom Workflow

Each plugin provides metadata and a default workflow. The long-term UI flow is:

```text
Select Job Type
  |
  v
Select Chain
  |
  v
Dynamic Configuration Form
  |
  v
Validation
  |
  v
Summary
  |
  v
Save
```

## Current TUI Workflow

The interface uses a sidebar for primary navigation and a job action strip above the jobs table.
The first screen is the operator home:

```text
Welcome to DICE

Create Job
View Jobs
Global Settings
Exit
```

`Create Job` opens a guided wizard that follows this flow:

1. Select job type from the plugin registry.
2. Select blockchain: Ethereum, BNB Chain, Arbitrum, Base, Optimism, Polygon.
3. Configure RPC endpoint: HTTP RPC and optional WebSocket RPC.
4. Configure wallet: wallet name, private key, wallet address, destination wallet.
5. Choose sweep type: native coin or ERC20 token.
6. Enter staking information: staking contract and optional ABI path.
7. Choose unlock method: manual, event, timestamp, block, claimable function, or balance change.
8. Enter withdrawal function and arguments.
9. Choose gas strategy: standard, aggressive, ultra, or custom.
10. Review retry policy and summary, then save the job.

The sidebar contains:

- `Home`
- `Create Job`
- `View Jobs`
- `Logs`
- `Settings`
- `Exit`

The jobs table is the operator control panel. Select a job row, then use the action strip:

- `Start`
- `Check`
- `Stop`
- `Edit`
- `Duplicate`
- `Delete`
- `Refresh`

Use `Check` before `Start` to run preflight manually and see the result in the workflow panel.
`Start` also runs the same checks automatically.

The TUI asks for fields, but execution still belongs to the daemon/job manager. The UI does not own
long-running job state.

## Test

```powershell
python -m pytest
```

## Project Layout

```text
src/
  dice/
    adapters/    Chain profiles and adapter interfaces
    app/         Textual app entry point
    core/        Job models, storage, manager, and runtime state
    execution/   Transaction build/broadcast orchestration
    service/     Long-running daemon and local control client
    ui/          Textual screens and widgets
    watcher/     Watchers and trigger evaluation
docs/          Architecture and operations notes
storage/
  jobs/        Local job JSON files
logs/          Runtime logs
tests/         Core tests
```

## Docs

- [Architecture](docs/architecture.md)
- [Operations](docs/operations.md)
- [Job Input Examples](docs/job-examples.md)
- [Packaging](docs/packaging.md)
- [Roadmap](docs/roadmap.md)
- [Plugin Development](docs/plugin-development.md)

## Open Source

DICE is licensed under the [Apache License 2.0](LICENSE).

- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
