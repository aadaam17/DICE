# Security Policy

DICE handles private keys and blockchain execution. Please treat security issues carefully.

## Reporting Vulnerabilities

Do not open public issues for vulnerabilities involving:

- private-key disclosure
- secret storage bypass
- transaction signing misuse
- command injection
- daemon control API abuse
- unsafe logging of secrets

For now, report security issues privately to the project maintainer. If this project moves to a
public GitHub organization, replace this section with the official private security advisory link.

## Secret Handling Expectations

- Raw private keys must never be stored in job JSON.
- Raw private keys must never be logged.
- Decrypted keys should exist only in memory for signing.
- `storage/secrets/*.json` must not be committed.
- `DICE_SECRET_PASSWORD` must not be committed or printed in logs.

## Supported Versions

This project is pre-1.0. Security fixes target the latest main branch until release branches exist.
