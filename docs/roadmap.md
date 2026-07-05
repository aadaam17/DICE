# DICE Roadmap

This roadmap prioritizes functionality that makes DICE more useful as an open-source blockchain
automation framework.

## 1. Preflight Validation

Status: implemented for core configuration, plugin validation, RPC connectivity, key checks,
contract bytecode, ABI function lookup, and transaction simulation.

Before a job can start, DICE verifies:

- RPC is reachable.
- RPC chain ID matches the selected chain.
- wallet address is valid.
- encrypted private key can be decrypted.
- signer address matches the configured wallet address.
- contract exists on chain.
- ABI file loads.
- target function exists in ABI.
- gas can be estimated where enough transaction data is available.
- max native-token fee can be shown from the simulated transaction.

Remaining improvement: extend simulation from direct contract-call jobs to every workflow action
once action handlers are complete.

## 2. Transaction Simulation

Status: implemented for direct real EVM contract execution.

The dry-run transaction simulation step now:

- build the exact transaction
- estimate gas
- detect likely revert reasons when RPC gas estimation fails
- show cost estimate in native gas token

Remaining improvement: include richer revert decoding and per-action simulation for multi-action
workflows.

## 3. Dynamic Plugin Forms

The TUI should build configuration forms from plugin schemas. Instead of one generic wizard for all
jobs, each plugin should expose fields such as:

- required chain fields
- trigger fields
- action fields
- validation rules
- summary display

This makes `Stake Sweep`, `Token Sweep`, and `Contract Call` feel like distinct workflows without
hardcoding their UI.

## 4. Real Workflow Action Handlers

The workflow engine should map action specs to handlers:

- transfer native coin
- transfer ERC20
- call contract
- wait
- notify
- run another workflow

Handlers should be injectable and testable.

## 5. Daemon API Hardening

The local control API should gain:

- request schema validation
- structured error codes
- auth token
- protocol compatibility checks
- optional Unix socket or named pipe support

## 6. Import, Export, Backup, Restore

DICE should support:

- export job without secrets
- import job templates
- duplicate job safely
- backup jobs and settings
- restore jobs and settings

Secrets should require explicit re-import or explicit reuse of an existing secret reference.

## 7. Dedicated Logs UI

Add a real Logs screen:

- per-job log selection
- live refresh
- level filtering
- error highlighting
- global app log

## 8. Plugin Developer Guide

Document how to create a new job plugin without modifying the manager, daemon, or UI.
