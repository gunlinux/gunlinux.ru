## Purpose

Guarantees the admin session signing key is never silently defaulted: the application and the deployment pipeline refuse to run with an unset or publicly-known SECRET_KEY.

## ADDED Requirements

### Requirement: Server fails fast on unset or default signing key

The server process SHALL refuse to start when the `SECRET_KEY` configuration is
unset or equals the known default value, exiting with an error message that
tells the operator to set it. A valid custom `SECRET_KEY` SHALL allow normal
startup.

#### Scenario: SECRET_KEY not configured

- **WHEN** the server starts with no `SECRET_KEY` provided and no environment file supplying one
- **THEN** the process exits with a non-zero status and an error naming `SECRET_KEY`
- **AND** no HTTP listener is opened

#### Scenario: SECRET_KEY equals the known default

- **WHEN** the server starts with `SECRET_KEY` set to the default value shipped in the application's defaults
- **THEN** the process exits with a non-zero status and an error naming `SECRET_KEY`
- **AND** no HTTP listener is opened

#### Scenario: custom SECRET_KEY configured

- **WHEN** the server starts with a `SECRET_KEY` that is neither unset nor the default value
- **THEN** the process starts normally and serves requests

#### Scenario: unrelated settings error cannot reset the secret

- **WHEN** settings loading fails for a field unrelated to `SECRET_KEY` (for example a malformed numeric value)
- **THEN** the process still refuses to start rather than silently falling back to a default signing key

### Requirement: Deployment pipeline refuses to ship without a signing key

The deployment script SHALL abort the deploy when the server host's environment
file does not contain a `SECRET_KEY` entry, so an insecure build is never
promoted to production.

#### Scenario: host environment file lacks SECRET_KEY

- **WHEN** the deployment script runs and the host `.env` file has no `SECRET_KEY` line
- **THEN** the deploy fails with an error instructing the operator to add `SECRET_KEY`
- **AND** the running service is left untouched

#### Scenario: host environment file has SECRET_KEY

- **WHEN** the deployment script runs and the host `.env` file contains a `SECRET_KEY` line
- **THEN** the deploy proceeds past the secret check
