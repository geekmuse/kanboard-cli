# Configuration Reference

> Complete reference for `kanboard-cli` configuration — config file format, environment variables, CLI flags, resolution order, and named profiles.

---

## Table of Contents

- [Config File Location](#config-file-location)
- [Config File Format](#config-file-format)
  - [Profile Fields](#profile-fields)
  - [Settings Section](#settings-section)
  - [Workflow Sections](#workflow-sections)
- [Environment Variable Reference](#environment-variable-reference)
- [CLI Flag Reference](#cli-flag-reference)
- [Resolution Order](#resolution-order)
- [Named Profiles](#named-profiles)
  - [Defining Profiles](#defining-profiles)
  - [Switching Profiles](#switching-profiles)
- [Authentication Modes](#authentication-modes)
  - [Application API (app)](#application-api-app)
  - [User API (user)](#user-api-user)
- [Portfolio Backend Selection](#portfolio-backend-selection)
- [Minimal Configurations](#minimal-configurations)

---

## Config File Location

The primary configuration file lives at:

```
~/.config/kanboard/config.toml
```

The directory (`~/.config/kanboard/`) is also home to workflow plugins (see [Workflows](workflows.md)).

You can print the exact path at any time:

```bash
kanboard config path
```

---

## Config File Format

The config file is a [TOML](https://toml.io/) document with three top-level sections:

| Section              | Purpose                                             |
|----------------------|-----------------------------------------------------|
| `[settings]`         | Global defaults (e.g. default profile)              |
| `[profiles.<name>]`  | Per-instance connection and auth settings           |
| `[workflows.<name>]` | Per-workflow plugin configuration                   |

### Full Example

```toml
# ~/.config/kanboard/config.toml

[settings]
default_profile = "work"       # profile used when no --profile flag is given
output_format = "table"        # global default output format (overridable per-profile)

[profiles.default]
url   = "http://localhost/jsonrpc.php"
token = "my-local-api-token"
output_format = "json"         # overrides [settings] output_format for this profile

[profiles.work]
url   = "https://kanboard.example.com/jsonrpc.php"
token = "work-api-token-here"

[profiles.staging]
url   = "https://staging.kanboard.example.com/jsonrpc.php"
token = "staging-token"

[profiles.me]
url       = "https://kanboard.example.com/jsonrpc.php"
auth_mode = "user"
username  = "brad"
password  = "my-password-or-PAT"

[workflows.sprint-close]
target_project = 42
close_tag      = "sprint-done"
```

---

### Profile Fields

Every `[profiles.<name>]` section supports the following fields:

| Field                | Type   | Default   | Description                                                                       |
|----------------------|--------|-----------|-----------------------------------------------------------------------------------|
| `url`                | string | —         | **Required.** Kanboard JSON-RPC endpoint URL                                      |
| `token`              | string | —         | API token. Required when `auth_mode = "app"` (default)                           |
| `output_format`      | string | `"table"` | Output format: `table`, `json`, `csv`, or `quiet`                                |
| `auth_mode`          | string | `"app"`   | Authentication mode: `"app"` or `"user"`                                         |
| `username`           | string | —         | Username. Required when `auth_mode = "user"`                                      |
| `password`           | string | —         | Password or personal access token. Required for `"user"` auth                    |
| `portfolio_backend`  | string | `"local"` | Portfolio storage backend: `"local"` (JSON file) or `"remote"` (plugin API)      |

**Notes:**

- All fields accept TOML string values (quoted with `"`).
- When `auth_mode = "user"`, `token` is ignored by the SDK and may be omitted.
- `output_format` in a profile overrides `[settings].output_format` for that profile.

---

### Settings Section

The `[settings]` table holds global defaults that apply across all profiles:

| Field             | Type   | Default     | Description                                           |
|-------------------|--------|-------------|-------------------------------------------------------|
| `default_profile` | string | `"default"` | Name of the profile to use when no `--profile` is given |
| `output_format`   | string | `"table"`   | Fallback output format (overridden by profile-level setting) |

```toml
[settings]
default_profile = "work"
output_format   = "table"
```

---

### Workflow Sections

Each workflow plugin can have its own `[workflows.<name>]` section. The plugin reads these values via `self.get_config()` (see [Workflows — Workflow Config Section](workflows.md#workflow-config-section)).

```toml
[workflows.sprint-close]
target_project = 42
sprint_tag     = "active-sprint"
```

Field names are plugin-defined. `kanboard-cli` passes the entire section dictionary to the plugin as-is.

---

## Environment Variable Reference

Environment variables override config file values for the active profile.

| Variable                       | Overrides                                | Example                                              |
|--------------------------------|------------------------------------------|------------------------------------------------------|
| `KANBOARD_URL`                 | `profiles.<active>.url`                  | `https://kanboard.example.com/jsonrpc.php`           |
| `KANBOARD_TOKEN`               | `profiles.<active>.token`                | `abc123def456`                                       |
| `KANBOARD_PROFILE`             | `settings.default_profile`               | `work`                                               |
| `KANBOARD_OUTPUT_FORMAT`       | `profiles.<active>.output_format`        | `json`                                               |
| `KANBOARD_AUTH_MODE`           | `profiles.<active>.auth_mode`            | `user`                                               |
| `KANBOARD_USERNAME`            | `profiles.<active>.username`             | `brad`                                               |
| `KANBOARD_PASSWORD`            | `profiles.<active>.password`             | `s3cr3t`                                             |
| `KANBOARD_PORTFOLIO_BACKEND`   | `profiles.<active>.portfolio_backend`    | `remote`                                             |

### Usage Examples

```bash
# Use a different Kanboard instance for a single command
KANBOARD_URL="http://localhost:8080/jsonrpc.php" \
KANBOARD_TOKEN="devtoken" \
kanboard project list

# Use user auth without changing your config file
KANBOARD_AUTH_MODE=user \
KANBOARD_USERNAME=admin \
KANBOARD_PASSWORD=admin \
kanboard me dashboard
```

---

## CLI Flag Reference

CLI flags take the highest priority — they override both env vars and config file values.

| Flag                            | Env Var equivalent             | Description                                                               |
|---------------------------------|--------------------------------|---------------------------------------------------------------------------|
| `--url URL`                     | `KANBOARD_URL`                 | Kanboard JSON-RPC endpoint URL                                            |
| `--token TOKEN`                 | `KANBOARD_TOKEN`               | Application API token                                                     |
| `--profile NAME`                | `KANBOARD_PROFILE`             | Config profile to activate                                                |
| `--output FORMAT`               | `KANBOARD_OUTPUT_FORMAT`       | Output format: `table`, `json`, `csv`, `quiet`                            |
| `--auth-mode MODE`              | `KANBOARD_AUTH_MODE`           | Auth mode: `app` or `user`                                                |
| `--verbose`                     | —                              | Enable DEBUG-level logging                                                |
| `--portfolio-backend BACKEND`   | `KANBOARD_PORTFOLIO_BACKEND`   | Portfolio backend: `local` (JSON file) or `remote` (plugin API)           |

All flags are **global** — they are placed before the subcommand:

```bash
kanboard --url https://other.host/jsonrpc.php --token mytoken project list
kanboard --profile staging --output json task list 1
kanboard --auth-mode user --verbose me dashboard
```

---

## Resolution Order

For each configuration field, the value is resolved in the following order (first non-empty value wins):

```
CLI flag  →  Environment variable  →  Config file (active profile)  →  Built-in default
```

**Profile selection** follows a separate order:

```
--profile flag  →  KANBOARD_PROFILE env var  →  settings.default_profile  →  "default"
```

### Illustrated Example

Suppose your config file defines:

```toml
[settings]
default_profile = "work"

[profiles.work]
url   = "https://work.kanboard.example.com/jsonrpc.php"
token = "work-token"
```

And you run:

```bash
KANBOARD_URL="https://override.example.com/jsonrpc.php" \
kanboard --token mytoken project list
```

Resolution produces:

| Field    | Source      | Resolved Value                                   |
|----------|-------------|--------------------------------------------------|
| profile  | config file | `work`                                           |
| url      | env var     | `https://override.example.com/jsonrpc.php`       |
| token    | CLI flag    | `mytoken`                                        |

---

## Named Profiles

Named profiles let you manage multiple Kanboard instances (e.g. production, staging, dev, personal) from a single config file.

### Defining Profiles

Add one `[profiles.<name>]` section per instance:

```toml
[profiles.default]
url   = "http://localhost:8080/jsonrpc.php"
token = "dev-token"

[profiles.prod]
url   = "https://kanboard.company.com/jsonrpc.php"
token = "prod-api-token"

[profiles.personal]
url   = "https://my.kanboard.org/jsonrpc.php"
token = "personal-token"
output_format = "json"
```

### Switching Profiles

**Default profile** (used when no `--profile` is given):

```toml
[settings]
default_profile = "prod"
```

**Temporary profile switch via CLI flag:**

```bash
kanboard --profile personal project list
```

**Temporary profile switch via env var:**

```bash
KANBOARD_PROFILE=staging kanboard task list 1
```

**List all defined profiles:**

```bash
kanboard config profiles
```

---

## Authentication Modes

### Application API (app)

The default mode. Uses a Kanboard Application API token for authentication.

```toml
[profiles.default]
url       = "https://kanboard.example.com/jsonrpc.php"
token     = "your-api-token"
auth_mode = "app"   # optional — "app" is the default
```

**Getting your API token:**

1. Log into Kanboard
2. Navigate to **Settings → API**
3. Copy the Application API token

> **Note:** Application API auth is supported by all Kanboard API methods.

---

### User API (user)

Uses HTTP Basic Auth with a username and password (or personal access token). Required for accessing the `me` resource group (user-specific dashboard, activity, and notifications).

```toml
[profiles.me]
url       = "https://kanboard.example.com/jsonrpc.php"
auth_mode = "user"
username  = "brad"
password  = "my-password-or-personal-token"
```

**Via CLI flags:**

```bash
kanboard --auth-mode user me dashboard
# Requires KANBOARD_USERNAME and KANBOARD_PASSWORD env vars (or use config profile)
```

> **Note:** When `auth_mode = "user"`, the `token` field is ignored.

---

## Portfolio Backend Selection

`kanboard-cli` supports two interchangeable backends for portfolio and milestone data:

| Backend | Value | Description |
|---|---|---|
| Local JSON file | `"local"` | Persists portfolios to `~/.config/kanboard/portfolios.json`. Works without any server-side plugin. **Default.** |
| Plugin API | `"remote"` | Persists portfolios via the [Kanboard Portfolio plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management) JSON-RPC API. Requires the plugin to be installed on your Kanboard server. |

### Configuring the backend

**In the TOML profile:**

```toml
[profiles.work]
url                = "https://kanboard.example.com/jsonrpc.php"
token              = "work-token"
portfolio_backend  = "remote"   # use server-side plugin storage
```

**Via environment variable:**

```bash
export KANBOARD_PORTFOLIO_BACKEND=remote
kanboard portfolio list
```

**Via CLI flag (one-off override):**

```bash
kanboard --portfolio-backend remote portfolio list
kanboard --portfolio-backend local  portfolio list
```

**Resolution order** (highest → lowest priority):

```
--portfolio-backend flag  →  KANBOARD_PORTFOLIO_BACKEND env var  →  portfolio_backend in TOML profile  →  "local" (default)
```

### Plugin detection

When `portfolio_backend = "remote"` is active, the CLI probes the Kanboard server for the Portfolio plugin on the first API call. If the plugin is not installed, a clear error is raised:

```
Error: Portfolio plugin not installed on the Kanboard server.
Install kanboard-plugin-portfolio-management, then retry.
Or use --portfolio-backend local to use the local JSON backend.
```

### Migration between backends

Use `kanboard portfolio migrate` to move data between backends without losing information:

```bash
# Preview what would be migrated
kanboard portfolio migrate local-to-remote --all --dry-run

# Migrate all local portfolios to the plugin
kanboard portfolio migrate local-to-remote --all

# Fetch remote data back to local
kanboard portfolio migrate remote-to-local --all

# Compare local vs. remote state
kanboard portfolio migrate diff --all
kanboard portfolio migrate status
```

See [CLI Reference — portfolio migrate](cli-reference.md#portfolio-migrate) for full syntax.

---

## Minimal Configurations

### Quickstart (no config file)

```bash
export KANBOARD_URL="https://kanboard.example.com/jsonrpc.php"
export KANBOARD_TOKEN="your-api-token"
kanboard project list
```

### Single-instance config file

```toml
# ~/.config/kanboard/config.toml
[profiles.default]
url   = "https://kanboard.example.com/jsonrpc.php"
token = "your-api-token"
```

### Multi-instance config file

```toml
[settings]
default_profile = "prod"

[profiles.prod]
url   = "https://kanboard.company.com/jsonrpc.php"
token = "prod-token"

[profiles.dev]
url   = "http://localhost:8080/jsonrpc.php"
token = "dev-token"
output_format = "json"
```

### Initialize interactively

```bash
kanboard config init        # guided prompts for URL and token
kanboard config show        # verify the resolved configuration
kanboard config test        # verify connectivity
```
