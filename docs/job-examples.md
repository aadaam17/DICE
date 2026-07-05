# DICE Job Input Examples

This guide shows what to type into the current DICE TUI job wizard. It includes safe test examples
using `mock://local` and real-life examples using live EVM RPCs.

Never paste a real private key into screenshots, chat, docs, issue reports, or logs. In the TUI,
the private key is accepted once, encrypted into `storage/secrets`, and represented in the job file
as a `secret://...` reference.

## Wizard Field Glossary

The current TUI wizard asks for the same screens for every job type. Some fields matter only for
specific job types.

### 1. Job Type

Use one of these keys:

```text
stake_sweep
token_sweep
scheduled_transfer
wallet_watch
contract_call
balance_trigger
event_trigger
custom_workflow
```

### 2. Chain

Supported chain keys:

```text
ethereum
bnb
arbitrum
base
optimism
polygon
```

### 3. RPC Endpoint

Test mode:

```text
HTTP RPC: mock://local
WebSocket RPC optional:
```

Real examples:

```text
Ethereum HTTP RPC: https://mainnet.infura.io/v3/YOUR_PROJECT_ID
BNB HTTP RPC: https://bsc-dataseed.binance.org
Arbitrum HTTP RPC: https://arb1.arbitrum.io/rpc
Base HTTP RPC: https://mainnet.base.org
Optimism HTTP RPC: https://mainnet.optimism.io
Polygon HTTP RPC: https://polygon-rpc.com
```

Use your own reliable paid/private RPC for production. Public RPCs can rate-limit or disappear.

### 4. Wallet Configuration

```text
Wallet name: Operator Wallet
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourWalletAddress
Destination wallet: 0xWhereFundsShouldGo
```

For mock testing, you can leave the private key blank. For real EVM execution, import a real private
key and make sure `DICE_SECRET_PASSWORD` is set before opening the TUI or daemon.

### 5. Sweep Type

Native coin:

```text
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
```

ERC20 token:

```text
native or erc20: erc20
Token contract if ERC20: 0xTokenContractAddress
Token symbol if ERC20: USDC
```

### 6. Staking Or Target Contract

For contract jobs, this is the contract DICE will call.

```text
Staking contract: 0xTargetContractAddress
ABI path optional: C:\Users\DELL\Documents\Projects\Dice\abis\target.json
```

Mock jobs can leave this blank. Real contract calls need a contract address and ABI path.

### 7. Unlock Method

Manual trigger:

```text
Unlock method: manual
Parameter 1:
Parameter 2:
```

Event trigger:

```text
Unlock method: event
Parameter 1: TokensUnlocked
Parameter 2: TokensUnlocked(address,uint256)
```

Timestamp trigger:

```text
Unlock method: timestamp
Parameter 1: 1767225600
Parameter 2:
```

Block trigger:

```text
Unlock method: block
Parameter 1: 23000000
Parameter 2:
```

Claimable function trigger:

```text
Unlock method: claimable_function
Parameter 1: claimableAmount
Parameter 2: 0xYourWalletAddress
```

Balance change trigger:

```text
Unlock method: balance_change
Parameter 1: 0xWalletToWatch
Parameter 2:
```

### 8. Withdrawal Function

No arguments:

```text
Function name: withdraw
Arguments:
```

One argument:

```text
Function name: claim
Arguments: 1
```

Multiple arguments:

```text
Function name: withdrawFromPool
Arguments: 1, 0xRecipientAddress
```

Arguments are comma-separated. The current TUI stores them as strings, so ABI-sensitive real calls
should be tested carefully with `Check` before `Start`.

### 9. Gas Strategy

Default:

```text
Gas mode: standard
Priority fee gwei:
Max fee gwei:
```

Faster:

```text
Gas mode: aggressive
Priority fee gwei:
Max fee gwei:
```

Manual custom gas:

```text
Gas mode: custom
Priority fee gwei: 0.05
Max fee gwei: 1.5
```

### 10. Retry Policy

```text
Replacement percent: 15
```

This is the percentage DICE can use later when replacing or speeding up transactions.

## Test Examples

These examples are meant for local workflow testing. They should save, run preflight, and start
without a private key because they use `mock://local`.

### Test 1: Contract Call On Mock Ethereum

Use this when you just want to prove the TUI, job manager, watcher, executor, logs, and status table
work.

```text
Job type: contract_call
Chain: ethereum
HTTP RPC: mock://local
WebSocket RPC optional:
Wallet name: Test Wallet
Private key:
Wallet address: 0x0000000000000000000000000000000000000000
Destination wallet: 0x0000000000000000000000000000000000000000
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract:
ABI path optional:
Unlock method: manual
Parameter 1:
Parameter 2:
Function name: claim
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

Expected result:

```text
Check: passes with mock warnings if no contract is configured.
Start: completes and writes a mock transaction hash.
```

### Test 2: Stake Sweep On Mock Polygon

```text
Job type: stake_sweep
Chain: polygon
HTTP RPC: mock://local
WebSocket RPC optional:
Wallet name: Polygon Test Wallet
Private key:
Wallet address: 0x0000000000000000000000000000000000000000
Destination wallet: 0x0000000000000000000000000000000000000000
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract:
ABI path optional:
Unlock method: block
Parameter 1: 100
Parameter 2:
Function name: withdraw
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

Expected result:

```text
Check: passes in mock mode.
Start: waits for the mock block trigger, then completes.
```

### Test 3: Token Sweep On Mock Base

```text
Job type: token_sweep
Chain: base
HTTP RPC: mock://local
WebSocket RPC optional:
Wallet name: Base Test Wallet
Private key:
Wallet address: 0x0000000000000000000000000000000000000000
Destination wallet: 0x0000000000000000000000000000000000000000
native or erc20: erc20
Token contract if ERC20: 0x0000000000000000000000000000000000000001
Token symbol if ERC20: TEST
Staking contract:
ABI path optional:
Unlock method: balance_change
Parameter 1: 0x0000000000000000000000000000000000000000
Parameter 2:
Function name: transfer
Arguments: 0x0000000000000000000000000000000000000000, 1000000
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

### Test 4: Event Trigger On Mock Arbitrum

Event jobs must include `Parameter 1`.

```text
Job type: event_trigger
Chain: arbitrum
HTTP RPC: mock://local
WebSocket RPC optional:
Wallet name: Arbitrum Test Wallet
Private key:
Wallet address: 0x0000000000000000000000000000000000000000
Destination wallet: 0x0000000000000000000000000000000000000000
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract:
ABI path optional:
Unlock method: event
Parameter 1: RewardsAvailable
Parameter 2: RewardsAvailable(address,uint256)
Function name: claimRewards
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

### Test 5: Scheduled Transfer On Mock Optimism

```text
Job type: scheduled_transfer
Chain: optimism
HTTP RPC: mock://local
WebSocket RPC optional:
Wallet name: Optimism Test Wallet
Private key:
Wallet address: 0x0000000000000000000000000000000000000000
Destination wallet: 0x0000000000000000000000000000000000000000
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract:
ABI path optional:
Unlock method: timestamp
Parameter 1: 1767225600
Parameter 2:
Function name: transfer
Arguments: 0x0000000000000000000000000000000000000000, 1000000000000000
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

## Real-Life Examples

These examples show realistic shapes. Replace every `YOUR_...` value before using them.

For real jobs:

1. Set `DICE_SECRET_PASSWORD`.
2. Use a real RPC URL for the selected chain.
3. Paste the private key once in the TUI.
4. Use `Check`.
5. Only choose `Start` after preflight passes.

### Real 1: Ethereum Contract Claim

Scenario: claim rewards from a rewards contract on Ethereum.

```text
Job type: contract_call
Chain: ethereum
HTTP RPC: https://mainnet.infura.io/v3/YOUR_PROJECT_ID
WebSocket RPC optional:
Wallet name: Mainnet Rewards Wallet
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourEthereumWallet
Destination wallet: 0xYourEthereumWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract: 0xRewardsContractAddress
ABI path optional: C:\Users\DELL\Documents\Projects\Dice\abis\rewards.json
Unlock method: manual
Parameter 1:
Parameter 2:
Function name: claim
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

Preflight should verify:

```text
RPC chain id is Ethereum mainnet.
Private key decrypts.
Signer address matches Wallet address.
Contract bytecode exists.
ABI exposes claim.
Simulation estimates gas and max ETH fee.
```

### Real 2: Base Manual Withdraw

Scenario: call `withdraw(uint256)` on a Base contract.

```text
Job type: contract_call
Chain: base
HTTP RPC: https://mainnet.base.org
WebSocket RPC optional:
Wallet name: Base Operator
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourBaseWallet
Destination wallet: 0xYourBaseWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract: 0xBaseVaultContract
ABI path optional: C:\Users\DELL\Documents\Projects\Dice\abis\base-vault.json
Unlock method: manual
Parameter 1:
Parameter 2:
Function name: withdraw
Arguments: 1000000000000000000
Gas mode: aggressive
Priority fee gwei:
Max fee gwei:
Replacement percent: 20
```

### Real 3: Polygon ERC20 Token Sweep

Scenario: sweep USDC-like tokens from an operational wallet to cold storage.

```text
Job type: token_sweep
Chain: polygon
HTTP RPC: https://polygon-rpc.com
WebSocket RPC optional:
Wallet name: Polygon Hot Wallet
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourPolygonHotWallet
Destination wallet: 0xYourColdStorageWallet
native or erc20: erc20
Token contract if ERC20: 0xYourTokenContract
Token symbol if ERC20: USDC
Staking contract: 0xYourTokenContract
ABI path optional: C:\Users\DELL\Documents\Projects\Dice\abis\erc20.json
Unlock method: balance_change
Parameter 1: 0xYourPolygonHotWallet
Parameter 2:
Function name: transfer
Arguments: 0xYourColdStorageWallet, 1000000
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

Note: ERC20 token amounts use the token's smallest unit. For a 6-decimal token, `1000000` means
`1.0` token.

### Real 4: BNB Chain Event-Based Reward Claim

Scenario: wait for a contract event, then call a claim function.

```text
Job type: event_trigger
Chain: bnb
HTTP RPC: https://bsc-dataseed.binance.org
WebSocket RPC optional:
Wallet name: BNB Rewards Wallet
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourBnbWallet
Destination wallet: 0xYourBnbWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract: 0xBnbRewardsContract
ABI path optional: C:\Users\DELL\Documents\Projects\Dice\abis\bnb-rewards.json
Unlock method: event
Parameter 1: RewardUnlocked
Parameter 2: RewardUnlocked(address,uint256)
Function name: claimReward
Arguments:
Gas mode: aggressive
Priority fee gwei:
Max fee gwei:
Replacement percent: 20
```

### Real 5: Arbitrum Stake Sweep At Block

Scenario: after a known unlock block, withdraw from a staking contract.

```text
Job type: stake_sweep
Chain: arbitrum
HTTP RPC: https://arb1.arbitrum.io/rpc
WebSocket RPC optional:
Wallet name: Arbitrum Staking Wallet
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourArbitrumWallet
Destination wallet: 0xYourDestinationWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract: 0xArbitrumStakingContract
ABI path optional: C:\Users\DELL\Documents\Projects\Dice\abis\arbitrum-staking.json
Unlock method: block
Parameter 1: 350000000
Parameter 2:
Function name: withdraw
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

### Real 6: Optimism Scheduled Native Transfer

Scenario: transfer native ETH on Optimism at a scheduled Unix timestamp.

```text
Job type: scheduled_transfer
Chain: optimism
HTTP RPC: https://mainnet.optimism.io
WebSocket RPC optional:
Wallet name: Optimism Treasury Wallet
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourOptimismWallet
Destination wallet: 0xRecipientWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract:
ABI path optional:
Unlock method: timestamp
Parameter 1: 1767225600
Parameter 2:
Function name: transfer
Arguments: 0xRecipientWallet, 10000000000000000
Gas mode: custom
Priority fee gwei: 0.001
Max fee gwei: 0.05
Replacement percent: 15
```

Current limitation: direct native transfers are represented as workflow intent, but the real EVM
adapter currently focuses on contract calls with ABI-backed transaction building. Use `Check` before
relying on scheduled transfers for real funds.

### Real 7: Wallet Watch On Base

Scenario: monitor a wallet and later connect it to a notification or workflow action.

```text
Job type: wallet_watch
Chain: base
HTTP RPC: https://mainnet.base.org
WebSocket RPC optional:
Wallet name: Base Watch Wallet
Private key:
Wallet address: 0xWalletToWatch
Destination wallet: 0xOperatorWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract:
ABI path optional:
Unlock method: balance_change
Parameter 1: 0xWalletToWatch
Parameter 2:
Function name: notify
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

Current limitation: notification handlers are workflow-level placeholders until real action handlers
are implemented.

### Real 8: Balance Trigger On Ethereum

Scenario: react when an address balance changes.

```text
Job type: balance_trigger
Chain: ethereum
HTTP RPC: https://mainnet.infura.io/v3/YOUR_PROJECT_ID
WebSocket RPC optional:
Wallet name: Balance Monitor
Private key:
Wallet address: 0xWalletToMonitor
Destination wallet: 0xOperatorWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract:
ABI path optional:
Unlock method: balance_change
Parameter 1: 0xWalletToMonitor
Parameter 2:
Function name: notify
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

### Real 9: Custom Workflow On Polygon

Scenario: save a custom manual workflow template that can later be expanded with plugin-specific
forms and real action handlers.

```text
Job type: custom_workflow
Chain: polygon
HTTP RPC: https://polygon-rpc.com
WebSocket RPC optional:
Wallet name: Polygon Automation Wallet
Private key: 0xYOUR_PRIVATE_KEY
Wallet address: 0xYourPolygonWallet
Destination wallet: 0xYourDestinationWallet
native or erc20: native
Token contract if ERC20:
Token symbol if ERC20:
Staking contract: 0xOptionalTargetContract
ABI path optional: C:\Users\DELL\Documents\Projects\Dice\abis\optional-target.json
Unlock method: manual
Parameter 1:
Parameter 2:
Function name: execute
Arguments:
Gas mode: standard
Priority fee gwei:
Max fee gwei:
Replacement percent: 15
```

## Common Scenarios

### I Just Want To Test DICE

Use:

```text
Job type: contract_call
Chain: ethereum
HTTP RPC: mock://local
Unlock method: manual
Function name: claim
```

Leave private key, contract, and ABI blank.

### I Want A Real Contract Call

Use:

```text
HTTP RPC: real chain RPC
Private key: real private key
Wallet address: address for that private key
Staking contract: target contract
ABI path optional: path to ABI JSON
Function name: exact ABI function
Arguments: exact ABI arguments
```

Then press `Check`. Do not start until the simulation passes.

### I Got `event_name is required`

You selected or defaulted to:

```text
Unlock method: event
```

Fix it one of two ways:

```text
Unlock method: manual
```

or keep event and fill:

```text
Parameter 1: EventName
Parameter 2: EventName(type1,type2)
```

### I Got `Real EVM jobs require an imported private key`

You are using a real RPC URL. Import a private key in the wallet step and make sure
`DICE_SECRET_PASSWORD` is set in the daemon/TUI environment.

### I Got `ABI does not expose function`

The function name in the wizard does not match the ABI. Check capitalization and overloads.

```text
Function name: claimRewards
```

is different from:

```text
Function name: claimrewards
```

### I Got `RPC chain id does not match`

The selected chain and RPC URL do not match. For example, do not use a Polygon RPC with:

```text
Chain: ethereum
```

## What Works Best Today

The strongest real execution path today is:

```text
contract_call + real RPC + private key + contract address + ABI path + manual trigger
```

Mock testing works well for all job types because it exercises the DICE manager, TUI, watcher,
executor, logging, and status lifecycle without touching real funds.

Some workflow plugins already exist as templates, but their full real-world behavior will become
stronger as dynamic plugin forms and action handlers are added.
