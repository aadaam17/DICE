# DICE Architecture

DICE is a terminal-first blockchain automation platform. It started as a staking watcher/sweep tool,
but the target architecture is now a generic EVM workflow engine.

The core abstraction is:

```text
Workflow
  |
  v
Trigger
  |
  v
Conditions
  |
  v
Actions
```

Jobs are independent workflow containers. "Stake Sweep", "Token Sweep", and "Contract Call" are
job plugins/templates, not special cases in the job manager.

DICE is split into two runtime modes:

- **Interactive mode**: the Textual TUI a user opens over SSH to view status, create jobs,
  edit jobs, start or stop jobs, and inspect logs.
- **Daemon mode**: the long-running service that owns job execution, watcher tasks,
  adapters, transaction building, and broadcasting.

The important rule is that jobs belong to the daemon, not to the terminal window. Closing the
TUI should not stop enabled jobs.

## Runtime Model

```text
SSH session
  |
  v
DICE TUI
  |
  | JSON control protocol
  v
DICE daemon
  |
  v
Job Manager
  |
  +--> Preflight -> Validation -> Adapter -> Signer -> ABI -> Simulation
  +--> Job A -> Workflow -> Trigger -> Conditions -> Actions
  +--> Job B -> Workflow -> Trigger -> Conditions -> Actions
  +--> Job C -> Workflow -> Trigger -> Conditions -> Actions
```

## Interactive Mode

Interactive mode is the operator interface. It should be safe to open and close repeatedly.

Responsibilities:

- Attach to the running daemon when available.
- Display live job and runtime state.
- Send commands such as start, stop, create, edit, duplicate, and delete.
- Avoid private-key display and avoid owning long-running execution state.

If no daemon is running, the current development TUI falls back to embedded mode. That keeps local
development simple, but production deployments should run the daemon separately.

## Daemon Mode

Daemon mode is the durable execution process.

Responsibilities:

- Load job JSON files from `storage/jobs`.
- Start every enabled job on boot.
- Keep each job isolated in its own async task.
- Run preflight checks before starting a job.
- Own workflow, watcher, trigger, execution, and broadcasting lifecycles.
- Expose a small local control API for the TUI and future CLIs.

The initial service uses a newline-delimited JSON protocol on `127.0.0.1:8765`. This is intentionally
small and local-first. It can later be replaced or wrapped with a Unix socket, named pipe, HTTP API,
or authenticated remote API without changing the core job manager.

## Job Plugin System

The job manager does not need to know whether a job is a stake sweep, token sweep, event trigger, or
custom workflow. Each job type is a plugin registered in `dice.jobs`.

Every plugin exposes:

- metadata
- form schema hints for the TUI
- default workflow template
- validation
- lifecycle methods: start, stop, pause, resume, execute
- serialization/deserialization through `JobConfig`

Built-in plugins:

- `stake_sweep`
- `token_sweep`
- `scheduled_transfer`
- `wallet_watch`
- `contract_call`
- `balance_trigger`
- `event_trigger`
- `custom_workflow`

The TUI and daemon discover job types from the registry rather than hardcoding a fixed list. The
same metadata includes field hints, so the wizard can show different guidance for `contract_call`,
`token_sweep`, `wallet_watch`, and other plugins.

## Workflow Engine

The generic workflow model lives in `dice.core.workflow`.

Supported trigger categories:

- block
- event
- time
- wallet change
- balance
- function result
- manual

Supported action categories:

- transfer native coin
- transfer ERC20
- call contract
- wait
- notify
- run another workflow
- withdraw
- sweep
- swap
- bridge

The execution layer processes actions sequentially through `dice.execution.actions`. Built-in action
handlers currently cover:

- contract call
- native transfer
- ERC20 transfer
- wait
- notify
- withdraw
- sweep

Real EVM contract calls use ABI-backed transaction building. Native and ERC20 transfers have EVM
transaction builders. Mock execution uses the same action dispatcher but broadcasts deterministic
mock transactions.

## Chain Adapters

DICE chooses the chain adapter from the job RPC configuration:

- `mock://...` uses the deterministic mock adapter for local workflow testing.
- `http://...` or `https://...` uses the Web3 EVM adapter for real chain execution.

The Web3 adapter verifies that the connected RPC chain ID matches the selected chain profile before
execution. Real contract execution requires a contract address, ABI path, function name, and function
arguments.

Adapters also expose small inspection hooks for preflight. The mock adapter reports deterministic
success for local tests. The EVM adapter can fetch bytecode and rejects RPCs whose chain ID does not
match the selected profile.

## Signing

Signing is isolated behind a signer layer. The execution engine asks the signer to decrypt the
private key from `private_key_ref`, sign the transaction in memory, and return only the raw signed
transaction for broadcasting.

## Persistence

Job definitions are stored as JSON files:

```text
storage/jobs/job-0001.json
storage/jobs/job-0002.json
```

Runtime state is in memory because it reflects the daemon's current execution. Job definitions are
the durable source of truth.

Job writes are atomic: DICE writes a temporary JSON file first, then replaces the saved job file.
That avoids half-written job files if the process is interrupted during save.

## Core Reliability

Before a job is saved, DICE validates the core configuration:

- supported chain profile
- RPC endpoint
- wallet and destination fields
- execution function
- trigger-specific required fields
- ERC20 token fields when the sweep type is ERC20
- gas replacement and fee values

Validation failures are returned to the TUI instead of crashing the interface. Warnings are written
to the job log.

Before a job starts, DICE runs preflight validation through `dice.core.preflight`. Preflight checks:

- core job configuration
- plugin validation
- RPC connectivity and chain ID
- private-key secret availability for real EVM jobs
- signer address matching the configured wallet when possible
- contract bytecode
- ABI file readability and target function presence
- transaction build, gas estimate, and max native-token fee estimate for real EVM jobs

Failed preflight reports keep the job from starting and transition it to `error`. Operators can run
the same check manually from the TUI with the `Check` action.

Transaction simulation lives in `dice.execution.simulation`. It uses the same adapter transaction
builder as execution, but stops before signing and broadcasting. This gives operators a chance to
catch bad ABI arguments, estimation failures, or expensive gas settings before a real transaction is
sent.

The daemon also exposes a lightweight status command with service version, protocol version, job
count, and running job count. This gives the TUI and future CLI tools a stable health check.

## Logs

Each job has a persistent log file:

```text
logs/job-0001.log
logs/job-0002.log
```

Runtime logs are also kept in memory for fast display while the daemon is running.

## Private Keys

Jobs do not store raw private keys. During job creation, the TUI accepts the private key once and
sends it to the active manager. The manager encrypts it into `storage/secrets` and stores only a
reference in the job file:

```json
"private_key_ref": "secret://wallets/job-0001"
```

DICE also supports reusable named wallet refs:

```json
"private_key_ref": "secret://wallets/base-sweeper"
```

That lets multiple jobs use the same encrypted wallet without re-entering the private key. The
wallet vault list exposes refs, labels, and addresses only. It never returns decrypted private keys.

Secret encryption requires `DICE_SECRET_PASSWORD` to be set before importing private keys. The same
password must be available to the daemon later when execution needs to decrypt the key for signing.

```powershell
$env:DICE_SECRET_PASSWORD = "use-a-long-random-password"
```

Internally, DICE uses the password to derive an encryption key, then encrypts the private key before
writing the secret file. The password itself is not stored by DICE. This means the encrypted secret
file is not useful by itself, but the password becomes critical recovery material.

## Security Notes

- The daemon should eventually run under a dedicated OS user.
- Control access should remain local by default.
- Private keys are referenced through encrypted local secret files, not stored directly in job JSON.
- Logs must redact credentials, RPC secrets, signed transactions, and raw private keys.
