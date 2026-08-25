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

Wallets can be reused across jobs. Enter a raw private key once when creating a job, then use the
wallet vault reference shown in Settings for later jobs:

```text
secret://wallets/base-sweeper
```

You can paste that `secret://wallets/...` value into the private-key field instead of entering the
raw private key again.

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

For Solana native SOL jobs, use:

```text
Chain: solana
HTTP RPC: https://api.mainnet-beta.solana.com
native or erc20/token: native
```

Solana private keys must be imported as either a base58 keypair string or a JSON byte array. DICE
also supports SPL token sweeping. For SPL tokens, use:

```text
native or erc20/token: erc20
Token contract or mint: SPL_TOKEN_MINT_ADDRESS
Token symbol: USDC
Token decimals optional: 6
```

DICE derives associated token accounts for the source and destination wallets. If the destination
associated token account does not exist, DICE adds an idempotent create instruction before the token
transfer.

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
10. Run behavior: once or continuous, repeat delay, poll interval, and gas replacement.
11. Review summary and save.

Choose `View Jobs` to work with existing jobs. Select a row and use the action strip above the jobs
table: `Check`, `Start`, `Stop`, `Edit`, `Duplicate`, `Delete`, or `Refresh`. Use sidebar `Logs` to
inspect the selected job.

Recommended job start flow:

1. Select the job row.
2. Choose `Check`.
3. Fix any failed preflight result.
4. Choose `Start`.

For copyable values to enter in each wizard field, see [Job Input Examples](job-examples.md).

For sweep and transfer jobs, use the execution screen's minimum amount field to avoid dust
transactions. Enter normal decimal amounts, not wei or raw token units. For example, setting
`Minimum amount` to `1` for USDC means DICE skips transfers below `1.0` USDC. Setting it to `0.001`
for Base ETH means DICE skips transfers below `0.001` ETH.

For ERC20 jobs, fill `Token decimals` if you know it. Common examples are `6` for USDC/USDT, `18`
for DAI/LINK/WETH, and `8` for WBTC. If left blank, DICE uses known defaults where possible and
asks the token contract for decimals during real execution.

For `balance_trigger`, DICE watches the address in `Parameter 1`. When that address reaches the
minimum amount, the default action is now `sweep`. If you leave `Arguments` empty, DICE calculates
the amount from the live wallet balance. For native coins, it subtracts estimated gas first so it
does not try to spend the full balance and fail.

For sweep or transfer jobs, `Parameter 1` must be the same address as `Wallet address`, because
DICE can only move funds from wallets whose private key you imported.

Use the final wizard screen to choose run mode:

```text
Run mode: once
```

means the job completes after one successful trigger/execution.

```text
Run mode: continuous
Repeat delay seconds: 5
Poll interval seconds: 1
```

means the job keeps watching after each execution until you stop it.

`Repeat delay seconds` controls the pause after an execution before continuous watching resumes.
`Poll interval seconds` controls how often DICE checks the trigger while waiting. For faster
response, reduce the poll interval, for example:

```text
Poll interval seconds: 0.25
```

Very low values can increase RPC usage and may hit rate limits on public RPC endpoints.

## Sweep Timing Logs

Every started job writes timing lines to its job log. These lines show where time is spent:

```text
timing: preflight finished in 0.812s
triggered: Trigger detected after 1.004s
timing: +0.214s fast native sweep amount resolved
timing: +0.318s transaction signed
timing: +0.642s transaction broadcast accepted
timing: execution finished in 0.642s
timing: full run cycle finished in 1.646s
```

Use these timings to tell whether delay came from polling, RPC balance updates, gas estimation,
signing, broadcasting, or chain inclusion.

Native balance sweeps also use a faster build path during real EVM execution. DICE calculates the
transferable balance and builds the transaction in one adapter step, reducing duplicate RPC work
before broadcast.

## Security Audit

Run a dependency audit before publishing or deploying:

```powershell
python -m pip_audit
```

CI runs the same audit automatically. Dependabot is configured to open weekly pull requests for
Python dependency updates and GitHub Actions updates.

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
