# CLI Reference

Complete reference for the `kanboard` command-line tool.

- [Global Options](#global-options)
- [Output Formats](#output-formats)
- [Command Groups](#command-groups)
  - [task](#task)
  - [project](#project)
  - [board](#board)
  - [column](#column)
  - [swimlane](#swimlane)
  - [comment](#comment)
  - [category](#category)
  - [subtask](#subtask)
  - [timer](#timer)
  - [user](#user)
  - [me](#me)
  - [tag](#tag)
  - [link](#link)
  - [task-link](#task-link)
  - [external-link](#external-link)
  - [group](#group)
  - [action](#action)
  - [project-file](#project-file)
  - [task-file](#task-file)
  - [project-meta](#project-meta)
  - [task-meta](#task-meta)
  - [project-access](#project-access)
  - [app](#app)
  - [config](#config)
  - [completion](#completion)
  - [workflow](#workflow)
  - [portfolio](#portfolio)
  - [milestone](#milestone)

---

## Global Options

Global options apply to every subcommand and must be placed **before** the
command group name.

```
kanboard [GLOBAL OPTIONS] COMMAND [ARGS]...
```

| Option | Short | Env var | Default | Description |
|---|---|---|---|---|
| `--url URL` | | `KANBOARD_URL` | config file | Kanboard JSON-RPC endpoint URL |
| `--token TOKEN` | | `KANBOARD_TOKEN` | config file | Kanboard API token |
| `--profile NAME` | | `KANBOARD_PROFILE` | config file | Named config profile to use |
| `--output FORMAT` | `-o` | | `table` | Output format: `table`, `json`, `csv`, `quiet` |
| `--verbose` | `-v` | | off | Enable DEBUG-level logging |
| `--auth-mode MODE` | | `KANBOARD_AUTH_MODE` | `app` | Auth mode: `app` (token) or `user` (username+password) |
| `--version` | | | | Print the CLI version and exit |
| `--help` / `-h` | | | | Show help and exit |

**Resolution order (lowest → highest priority):**

```
config file → environment variables → CLI flags
```

### Examples

```bash
# Use a named profile for a staging server
kanboard --profile staging project list

# Override URL and token on the fly
kanboard --url https://kb.example.com/jsonrpc.php --token abc123 task list 1

# Get JSON output for scripting
kanboard --output json task list 1

# Enable debug logging
kanboard --verbose task get 42

# Use user auth mode (required for 'me' commands)
kanboard --auth-mode user me
```

---

## Output Formats

All list and get commands support four output formats via `--output` / `-o`.

### `table` (default)

Rich-formatted, colorized table. Best for interactive use.

```bash
kanboard task list 1
```

```
 id   title                  is_active   priority   column_id   owner_id   date_due
 42   Fix login bug          True        2          3           1          2025-12-31
 43   Refactor API           True        1          2           None       None
```

### `json`

JSON output. Lists return a JSON array; single-resource commands return a JSON
object. Ideal for piping to `jq` or scripts.

```bash
kanboard --output json task list 1
```

```json
[
  {"id": 42, "title": "Fix login bug", "is_active": true, "priority": 2, ...},
  {"id": 43, "title": "Refactor API", "is_active": true, "priority": 1, ...}
]
```

```bash
kanboard --output json task get 42
```

```json
{"id": 42, "title": "Fix login bug", "project_id": 1, "column_id": 3, ...}
```

### `csv`

CSV output with a header row. Useful for import into spreadsheets or data
processing pipelines.

```bash
kanboard --output csv task list 1
```

```
id,title,is_active,priority,column_id,owner_id,date_due
42,Fix login bug,True,2,3,1,2025-12-31
43,Refactor API,True,1,2,,
```

### `quiet`

Prints only the IDs (or the primary identifier), one per line. Useful for
shell pipelines.

```bash
# Close all active tasks in project 1
kanboard --output quiet task list 1 | xargs -I{} kanboard task close {}
```

```
42
43
```

---

## Command Groups

### task

Manage Kanboard tasks.

```
kanboard task SUBCOMMAND [ARGS]...
```

#### `task list`

List tasks in a project.

```
kanboard task list PROJECT_ID [--status active|inactive]
```

| Argument / Option | Description |
|---|---|
| `PROJECT_ID` | Project to list tasks from |
| `--status` | Filter by status (`active` or `inactive`; default: `active`) |

```bash
kanboard task list 1
kanboard task list 1 --status inactive
kanboard --output json task list 1
```

#### `task get`

Show full details for a task.

```
kanboard task get TASK_ID
```

```bash
kanboard task get 42
kanboard --output json task get 42
```

#### `task create`

Create a new task.

```
kanboard task create PROJECT_ID TITLE [OPTIONS]
```

| Option | Description |
|---|---|
| `--owner-id INT` | Assign to this user ID |
| `--column-id INT` | Place in this column |
| `--swimlane-id INT` | Place in this swimlane |
| `--due DATE` | Due date (`YYYY-MM-DD`) |
| `--description / -d TEXT` | Task description |
| `--color TEXT` | Color identifier (e.g. `red`, `blue`, `green`) |
| `--category-id INT` | Category ID |
| `--score INT` | Complexity / effort score |
| `--priority INT` | Priority (higher = more urgent) |
| `--reference TEXT` | External reference (e.g. ticket number) |
| `--tag TAG` | Tag to apply (repeatable) |

```bash
kanboard task create 1 "Fix login bug"
kanboard task create 1 "API refactor" --due 2025-12-31 --priority 2
kanboard task create 1 "Feature" --tag backend --tag api --color green
```

#### `task update`

Update fields on an existing task. Only supplied options are changed.

```
kanboard task update TASK_ID [OPTIONS]
```

Options: `--title`, `--color`, `--due DATE`, `--description / -d`, `--owner-id INT`,
`--category-id INT`, `--score INT`, `--priority INT`, `--reference TEXT`, `--tag TAG`

```bash
kanboard task update 42 --title "Renamed task"
kanboard task update 42 --priority 3 --due 2025-11-01
```

#### `task close`

Close (complete) a task.

```
kanboard task close TASK_ID
```

#### `task open`

Reopen a closed task.

```
kanboard task open TASK_ID
```

#### `task remove`

Permanently delete a task. Requires `--yes` or interactive confirmation.

```
kanboard task remove TASK_ID [--yes]
```

```bash
kanboard task remove 42 --yes
```

#### `task search`

Search tasks using Kanboard's filter syntax.

```
kanboard task search PROJECT_ID QUERY
```

```bash
kanboard task search 1 "assignee:me status:open"
kanboard task search 1 "due:<2025-12-31"
```

#### `task move`

Move a task to a different column / position within the same project.

```
kanboard task move TASK_ID --project-id INT --column-id INT --position INT --swimlane-id INT
```

```bash
kanboard task move 42 --project-id 1 --column-id 3 --position 1 --swimlane-id 0
```

#### `task move-to-project`

Move a task to a different project.

```
kanboard task move-to-project TASK_ID PROJECT_ID [OPTIONS]
```

Options: `--swimlane-id INT`, `--column-id INT`, `--category-id INT`, `--owner-id INT`

```bash
kanboard task move-to-project 42 2
kanboard task move-to-project 42 2 --column-id 5 --owner-id 3
```

#### `task duplicate`

Duplicate a task into another project.

```
kanboard task duplicate TASK_ID PROJECT_ID [--swimlane-id INT] [--column-id INT]
```

```bash
kanboard task duplicate 42 3
kanboard task duplicate 42 3 --swimlane-id 1 --column-id 2
```

#### `task overdue`

List overdue tasks across all projects or within a specific project.

```
kanboard task overdue [--project-id INT]
```

```bash
kanboard task overdue
kanboard task overdue --project-id 1
```

---

### project

Manage Kanboard projects.

```
kanboard project SUBCOMMAND [ARGS]...
```

#### `project list`

List all accessible projects.

```bash
kanboard project list
kanboard --output json project list
```

#### `project get`

Show full details for a project.

```
kanboard project get PROJECT_ID
```

#### `project create`

Create a new project.

```
kanboard project create NAME [OPTIONS]
```

Options: `--description / -d TEXT`, `--owner-id INT`, `--identifier CODE`,
`--start-date DATE`, `--end-date DATE`

```bash
kanboard project create "My Project"
kanboard project create "Backend" --owner-id 2 --identifier BACK
kanboard project create "Sprint" --start-date 2025-01-01 --end-date 2025-03-31
```

#### `project update`

Update fields on a project. Only supplied options are changed.

```
kanboard project update PROJECT_ID [OPTIONS]
```

Options: `--name TEXT`, `--description / -d TEXT`, `--owner-id INT`, `--identifier CODE`

```bash
kanboard project update 1 --name "Renamed Project"
kanboard project update 1 --owner-id 3 --identifier NEW
```

#### `project remove`

Permanently delete a project and all its data. Requires `--yes` or
interactive confirmation.

```
kanboard project remove PROJECT_ID [--yes]
```

#### `project enable` / `project disable`

Enable or disable a project.

```bash
kanboard project enable 1
kanboard project disable 1
```

#### `project activity`

Show the activity feed for a project.

```
kanboard project activity PROJECT_ID
```

---

### board

View the board layout for a project.

```
kanboard board show PROJECT_ID
```

In `table` / `csv` mode the top-level column fields are shown. Use
`--output json` for the full nested structure including swimlanes and tasks.

```bash
kanboard board show 1
kanboard --output json board show 1
```

---

### column

Manage board columns.

```
kanboard column SUBCOMMAND [ARGS]...
```

#### `column list`

List all columns for a project.

```bash
kanboard column list 1
```

#### `column get`

Show full details for a column.

```bash
kanboard column get 5
```

#### `column add`

Add a new column to a project.

```
kanboard column add PROJECT_ID TITLE [--task-limit INT] [--description / -d TEXT]
```

```bash
kanboard column add 1 "In Review"
kanboard column add 1 "Done" --task-limit 20 --description "Completed tasks"
```

#### `column update`

Update a column title and optional fields.

```
kanboard column update COLUMN_ID TITLE [--task-limit INT] [--description / -d TEXT]
```

```bash
kanboard column update 5 "In Progress"
kanboard column update 5 "WIP" --task-limit 10
```

#### `column remove`

Permanently delete a column. Requires `--yes`.

```
kanboard column remove COLUMN_ID [--yes]
```

#### `column move`

Move a column to a new position (1-based, leftmost = 1).

```
kanboard column move PROJECT_ID COLUMN_ID POSITION
```

```bash
kanboard column move 1 5 3
```

---

### swimlane

Manage project swimlanes.

```
kanboard swimlane SUBCOMMAND [ARGS]...
```

#### Subcommands

| Subcommand | Description |
|---|---|
| `swimlane list PROJECT_ID [--all]` | List swimlanes (active only by default; `--all` includes inactive) |
| `swimlane get SWIMLANE_ID` | Show full details |
| `swimlane get-by-name PROJECT_ID NAME` | Look up by name |
| `swimlane add PROJECT_ID NAME [--description / -d TEXT]` | Add a swimlane |
| `swimlane update PROJECT_ID SWIMLANE_ID NAME [--description / -d TEXT]` | Update a swimlane |
| `swimlane remove PROJECT_ID SWIMLANE_ID [--yes]` | Delete a swimlane |
| `swimlane enable PROJECT_ID SWIMLANE_ID` | Enable a swimlane |
| `swimlane disable PROJECT_ID SWIMLANE_ID` | Disable a swimlane |
| `swimlane move PROJECT_ID SWIMLANE_ID POSITION` | Move to new position (1-based, topmost = 1) |

```bash
kanboard swimlane list 1
kanboard swimlane list 1 --all
kanboard swimlane add 1 "High Priority"
kanboard swimlane move 1 3 2
```

---

### comment

Manage task comments.

```
kanboard comment SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `comment list TASK_ID` | List all comments for a task |
| `comment get COMMENT_ID` | Show full details |
| `comment add TASK_ID CONTENT --user-id INT` | Add a comment |
| `comment update COMMENT_ID CONTENT` | Update comment text |
| `comment remove COMMENT_ID [--yes]` | Delete a comment |

```bash
kanboard comment list 42
kanboard comment add 42 "Looks good to me." --user-id 1
kanboard comment update 7 "Updated comment text."
kanboard comment remove 7 --yes
```

---

### category

Manage task categories within projects.

```
kanboard category SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `category list PROJECT_ID` | List all categories for a project |
| `category get CATEGORY_ID` | Show full details |
| `category create PROJECT_ID NAME [--color-id TEXT]` | Create a category |
| `category update CATEGORY_ID NAME [--color-id TEXT]` | Update a category |
| `category remove CATEGORY_ID [--yes]` | Delete a category |

```bash
kanboard category list 1
kanboard category create 1 "Frontend" --color-id blue
kanboard category remove 3 --yes
```

---

### subtask

Manage subtasks within tasks.

```
kanboard subtask SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `subtask list TASK_ID` | List all subtasks |
| `subtask get SUBTASK_ID` | Show full details |
| `subtask create TASK_ID TITLE [OPTIONS]` | Create a subtask (`--user-id INT`, `--time-estimated FLOAT`, `--status INT`) |
| `subtask update SUBTASK_ID TASK_ID [OPTIONS]` | Update a subtask (`--title`, `--user-id INT`, `--time-estimated FLOAT`, `--time-spent FLOAT`, `--status INT`) |
| `subtask remove SUBTASK_ID [--yes]` | Delete a subtask |

Subtask status values: `0` = todo, `1` = in progress, `2` = done.

```bash
kanboard subtask list 42
kanboard subtask create 42 "Write tests" --user-id 3 --time-estimated 1.5
kanboard subtask update 10 42 --status 1 --time-spent 0.5
kanboard subtask remove 10 --yes
```

---

### timer

Start and stop subtask time-tracking timers.

```
kanboard timer SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `timer status SUBTASK_ID [--user-id INT]` | Check whether a timer is running |
| `timer start SUBTASK_ID [--user-id INT]` | Start the timer |
| `timer stop SUBTASK_ID [--user-id INT]` | Stop the timer |
| `timer spent SUBTASK_ID [--user-id INT]` | Show total hours spent |

```bash
kanboard timer start 7
kanboard timer status 7
kanboard timer stop 7
kanboard timer spent 7
```

---

### user

Manage Kanboard users.

```
kanboard user SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `user list` | List all users |
| `user get USER_ID` | Show full details |
| `user get-by-name USERNAME` | Look up by username |
| `user create USERNAME [OPTIONS]` | Create a user (`--password TEXT`, `--name TEXT`, `--email TEXT`, `--role TEXT`) |
| `user update USER_ID [OPTIONS]` | Update user fields (`--username`, `--name`, `--email`, `--role`) |
| `user remove USER_ID [--yes]` | Delete a user |
| `user enable USER_ID` | Enable a user account |
| `user disable USER_ID` | Disable a user account |
| `user is-active USER_ID` | Report active/inactive status |

Common roles: `app-user`, `app-admin`, `app-manager`.

```bash
kanboard user create jdoe --name "John Doe" --email jdoe@example.com
kanboard user update 3 --role app-admin
kanboard user enable 3
kanboard user disable 3
kanboard user remove 3 --yes
```

---

### me

Commands for the authenticated user. All subcommands require
`--auth-mode user` with `KANBOARD_USERNAME` and `KANBOARD_PASSWORD`.

```
kanboard --auth-mode user me [SUBCOMMAND]
```

Invoked without a subcommand, `me` shows the current user profile.

| Subcommand | Description |
|---|---|
| *(none)* | Show current user profile |
| `me dashboard` | Show the current user's dashboard (projects, tasks, subtasks) |
| `me activity` | Show recent activity stream |
| `me projects` | List projects the current user is a member of |
| `me overdue` | List the current user's overdue tasks |
| `me create-project NAME [--description TEXT]` | Create a private project |

```bash
# Authenticate with username + password
export KANBOARD_USERNAME=admin
export KANBOARD_PASSWORD=admin

kanboard --auth-mode user me
kanboard --auth-mode user me dashboard
kanboard --auth-mode user me activity
kanboard --auth-mode user me projects
kanboard --auth-mode user me overdue
kanboard --auth-mode user me create-project "My Private Project"
```

---

### tag

Manage tags.

```
kanboard tag SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `tag list [--project-id INT]` | List tags (all, or filtered by project) |
| `tag get TASK_ID` | Show tags assigned to a task |
| `tag create PROJECT_ID TAG_NAME [--color-id TEXT]` | Create a tag |
| `tag update TAG_ID TAG_NAME [--color-id TEXT]` | Update a tag |
| `tag remove TAG_ID [--yes]` | Delete a tag |
| `tag set PROJECT_ID TASK_ID TAG...` | Assign tags to a task (replaces existing) |

```bash
kanboard tag list --project-id 1
kanboard tag create 1 "urgent" --color-id red
kanboard tag set 1 42 urgent bug
kanboard tag get 42
```

---

### link

Manage link type definitions (e.g. "blocks", "is blocked by").

```
kanboard link SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `link list` | List all link type definitions |
| `link get LINK_ID` | Show details for a link type |
| `link get-by-label LABEL` | Look up a link type by label |
| `link create LABEL [--opposite-label TEXT]` | Create a link type |
| `link update LINK_ID OPPOSITE_LINK_ID LABEL` | Update a link type |
| `link remove LINK_ID [--yes]` | Delete a link type |

```bash
kanboard link list
kanboard link create blocks --opposite-label "is blocked by"
kanboard link update 1 2 blocks
```

---

### task-link

Manage internal task-to-task links.

```
kanboard task-link SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `task-link list TASK_ID` | List all links for a task |
| `task-link get TASK_LINK_ID` | Show details for a link |
| `task-link create TASK_ID OPPOSITE_TASK_ID LINK_ID` | Create a link between two tasks |
| `task-link update TASK_LINK_ID TASK_ID OPPOSITE_TASK_ID LINK_ID` | Update a link |
| `task-link remove TASK_LINK_ID [--yes]` | Delete a link |

```bash
kanboard task-link list 42
kanboard task-link create 10 20 1
kanboard task-link remove 7 --yes
```

---

### external-link

Manage external (URL-based) links on tasks.

```
kanboard external-link SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `external-link list TASK_ID` | List external links for a task |
| `external-link get EXTERNAL_LINK_ID` | Show details |
| `external-link types` | List available external link types |
| `external-link add TASK_ID URL [OPTIONS]` | Add an external link (`--link-type TEXT`, `--dependency TEXT`, `--title TEXT`) |
| `external-link update EXTERNAL_LINK_ID [OPTIONS]` | Update an external link |
| `external-link remove EXTERNAL_LINK_ID [--yes]` | Delete an external link |

```bash
kanboard external-link list 42
kanboard external-link add 42 https://github.com/org/repo/issues/10 --link-type weblink
kanboard external-link remove 5 --yes
```

---

### group

Manage user groups.

```
kanboard group SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `group list` | List all groups |
| `group get GROUP_ID` | Show group details |
| `group create NAME [--external-id TEXT]` | Create a group |
| `group update GROUP_ID [--name TEXT] [--external-id TEXT]` | Update a group |
| `group remove GROUP_ID [--yes]` | Delete a group |

```bash
kanboard group create "Developers"
kanboard group update 1 --name "Engineering"
kanboard group remove 1 --yes
```

#### `group member` (sub-group)

| Subcommand | Description |
|---|---|
| `group member list GROUP_ID` | List members of a group |
| `group member groups USER_ID` | List groups a user belongs to |
| `group member add GROUP_ID USER_ID` | Add a user to a group |
| `group member remove GROUP_ID USER_ID [--yes]` | Remove a user from a group |
| `group member check GROUP_ID USER_ID` | Check whether a user is a member |

```bash
kanboard group member list 1
kanboard group member add 1 5
kanboard group member check 1 5
kanboard group member remove 1 5 --yes
```

---

### action

Manage automatic actions on projects.

```
kanboard action SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `action list PROJECT_ID` | List automatic actions for a project |
| `action available` | List all available action types |
| `action events` | List all available action events |
| `action compatible-events ACTION_NAME` | List events compatible with an action type |
| `action create PROJECT_ID EVENT_NAME ACTION_NAME [-p KEY=VALUE]...` | Create an automatic action |
| `action remove ACTION_ID [--yes]` | Delete an automatic action |

```bash
kanboard action available
kanboard action events
kanboard action create 1 task.move.column "\\TaskClose" -p column_id=5
kanboard action list 1
kanboard action remove 5 --yes
```

---

### project-file

Manage file attachments on projects.

```
kanboard project-file SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `project-file list PROJECT_ID` | List all files attached to a project |
| `project-file get FILE_ID` | Show file details |
| `project-file upload PROJECT_ID PATH [--filename TEXT]` | Upload a file to a project |
| `project-file download FILE_ID PATH` | Download a project file |
| `project-file remove FILE_ID [--yes]` | Delete a file |
| `project-file remove-all PROJECT_ID [--yes]` | Delete all files from a project |

---

### task-file

Manage file attachments on tasks.

```
kanboard task-file SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `task-file list TASK_ID` | List all files attached to a task |
| `task-file get FILE_ID` | Show file details |
| `task-file upload TASK_ID PATH [--filename TEXT]` | Upload a file to a task |
| `task-file download FILE_ID PATH` | Download a task file |
| `task-file remove FILE_ID [--yes]` | Delete a file |
| `task-file remove-all TASK_ID [--yes]` | Delete all files from a task |

---

### project-meta

Manage project key-value metadata.

```
kanboard project-meta SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `project-meta list PROJECT_ID` | List all metadata for a project |
| `project-meta get PROJECT_ID NAME` | Get a metadata value by name |
| `project-meta set PROJECT_ID NAME VALUE` | Set (create or update) a metadata value |
| `project-meta remove PROJECT_ID NAME [--yes]` | Delete a metadata entry |

```bash
kanboard project-meta set 1 sprint "Sprint 5"
kanboard project-meta get 1 sprint
kanboard project-meta list 1
```

---

### task-meta

Manage task key-value metadata.

```
kanboard task-meta SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `task-meta list TASK_ID` | List all metadata for a task |
| `task-meta get TASK_ID NAME` | Get a metadata value by name |
| `task-meta set TASK_ID NAME VALUE` | Set (create or update) a metadata value |
| `task-meta remove TASK_ID NAME [--yes]` | Delete a metadata entry |

---

### project-access

Manage user and group access to projects.

```
kanboard project-access SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `project-access list PROJECT_ID` | List users assigned to a project |
| `project-access assignable PROJECT_ID` | List users assignable to tasks in a project |
| `project-access add-user PROJECT_ID USER_ID [--role TEXT]` | Add a user to a project |
| `project-access add-group PROJECT_ID GROUP_ID [--role TEXT]` | Add a group to a project |
| `project-access remove-user PROJECT_ID USER_ID [--yes]` | Remove a user from a project |
| `project-access remove-group PROJECT_ID GROUP_ID [--yes]` | Remove a group from a project |
| `project-access set-user-role PROJECT_ID USER_ID ROLE` | Change a user's project role |
| `project-access set-group-role PROJECT_ID GROUP_ID ROLE` | Change a group's project role |
| `project-access user-role PROJECT_ID USER_ID` | Get a user's current role |

Common project roles: `project-viewer`, `project-member`, `project-manager`.

```bash
kanboard project-access add-user 1 42 --role project-member
kanboard project-access set-user-role 1 42 project-manager
kanboard project-access user-role 1 42
kanboard project-access remove-user 1 42 --yes
```

---

### app

Application-level information from the Kanboard server.

```
kanboard app SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `app version` | Show the Kanboard server version |
| `app timezone` | Show the server default timezone |
| `app colors` | Show all task colour definitions |
| `app default-color` | Show the default task colour identifier |
| `app roles` | Show application-level and project-level roles |

```bash
kanboard app version
kanboard app colors
kanboard app roles
```

---

### config

Manage the CLI configuration file (`~/.config/kanboard/config.toml`).

```
kanboard config SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `config init [--force]` | Create the config file interactively (prompts for URL and token) |
| `config show` | Display the active config with token masked |
| `config path` | Print the config file path |
| `config profiles` | List all profile names |
| `config test` | Test connectivity to the configured server |

```bash
# First-time setup
kanboard config init

# Overwrite existing config
kanboard config init --force

# Verify active configuration
kanboard config show

# Check where the config file lives
kanboard config path

# List all named profiles
kanboard config profiles

# Verify server connectivity
kanboard config test
```

---

### completion

Generate and install shell completion scripts.

```
kanboard completion SUBCOMMAND
```

| Subcommand | Description |
|---|---|
| `completion bash` | Output bash completion script to stdout |
| `completion zsh` | Output zsh completion script to stdout |
| `completion fish` | Output fish completion script to stdout |
| `completion install bash\|zsh\|fish` | Install completion to the appropriate shell config file |

```bash
# One-time evaluation in the current shell
eval "$(kanboard completion bash)"
eval "$(kanboard completion zsh)"

# Permanent installation
kanboard completion install bash    # appends to ~/.bashrc
kanboard completion install zsh     # appends to ~/.zshrc
kanboard completion install fish    # writes to ~/.config/fish/completions/kanboard.fish
```

---

### workflow

List and run workflow plugins.

```
kanboard workflow list
```

Plugins are discovered from `~/.config/kanboard/workflows/`. Each `.py` file
that contains a `BaseWorkflow` subclass is loaded automatically. Once
registered, plugins appear as top-level `kanboard` subcommands.

```bash
kanboard workflow list         # Show all discovered plugins
kanboard my-workflow           # Run a custom workflow
```

See the main [README](../README.md) for workflow plugin development details.

---

### portfolio

Cross-project portfolio management, task aggregation, dependency analysis, and critical-path computation.
Portfolio state is stored locally in `~/.config/kanboard/portfolios.json` — no server-side plugin is required.

```
kanboard portfolio SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `portfolio list` | List all portfolios (name, description, project count, milestone count) |
| `portfolio show NAME` | Portfolio dashboard: summary, milestone progress bars, at-risk items |
| `portfolio create NAME [--description TEXT]` | Create a new portfolio in the local store |
| `portfolio remove NAME --yes` | Delete a portfolio from the local store (best-effort metadata cleanup) |
| `portfolio add-project NAME PROJECT_ID` | Add a project to a portfolio (validates project exists via API) |
| `portfolio remove-project NAME PROJECT_ID --yes` | Remove a project from a portfolio |
| `portfolio tasks NAME [--status active\|closed] [--project ID] [--assignee ID]` | List all tasks across all portfolio projects |
| `portfolio sync NAME` | Push portfolio/milestone metadata to Kanboard project and task metadata |
| `portfolio dependencies NAME [--cross-project-only] [--format graph\|table\|json]` | Visualise task dependency graph |
| `portfolio blocked NAME` | List cross-project tasks blocked by unresolved dependencies |
| `portfolio blocking NAME` | List cross-project open tasks that are blocking others |
| `portfolio critical-path NAME` | Numbered list of the longest dependency chain; marks the bottleneck task |

#### Portfolio list

```bash
kanboard portfolio list
kanboard --output json portfolio list
```

#### Portfolio show

Displays a portfolio dashboard combining local store data with live API data. Falls back to cached store data with a warning if the API is unreachable.

```bash
kanboard portfolio show "Platform Launch"
```

#### Portfolio create / remove

```bash
kanboard portfolio create "Platform Launch" --description "Q3 release programme"
kanboard portfolio remove "Platform Launch" --yes
```

#### Portfolio add-project / remove-project

```bash
# Add projects (validates project exists via API first)
kanboard portfolio add-project "Platform Launch" 1
kanboard portfolio add-project "Platform Launch" 2

kanboard portfolio remove-project "Platform Launch" 2 --yes
```

#### Portfolio tasks

Lists all tasks across every project in the portfolio. Columns: `id`, `title`, `project_name`, `column_title`, `owner_username`, `date_due`, `priority`.

```bash
kanboard portfolio tasks "Platform Launch"
kanboard portfolio tasks "Platform Launch" --status closed
kanboard portfolio tasks "Platform Launch" --project 1
kanboard --output json portfolio tasks "Platform Launch"
```

#### Portfolio sync

Pushes portfolio and milestone membership into Kanboard project/task metadata using the `kanboard_cli:` key prefix.

```bash
kanboard portfolio sync "Platform Launch"
# Synced 2 projects, 47 tasks
```

#### Portfolio dependencies

Visualises task dependency relationships across all portfolio projects.

```bash
# ASCII dependency graph (default)
kanboard portfolio dependencies "Platform Launch"

# Cross-project dependencies only
kanboard portfolio dependencies "Platform Launch" --cross-project-only

# Flat table of edges
kanboard portfolio dependencies "Platform Launch" --format table

# Structured JSON (nodes + edges)
kanboard portfolio dependencies "Platform Launch" --format json
```

Example ASCII output:

```
── Project: Product Alpha ─────────────────────────────────────────
  ● #42 Implement OAuth login
      → blocks #99 (Marketing Site)
  ✓ #38 Write API docs

── Project: Marketing Site ────────────────────────────────────────
  ● #99 Launch landing page
      ← blocked by #42 (Product Alpha)
```

#### Portfolio blocked / blocking

Lists tasks with unresolved cross-project blockers (or tasks that are blocking others). All four output formats supported.

```bash
kanboard portfolio blocked "Platform Launch"
kanboard portfolio blocking "Platform Launch"
kanboard --output json portfolio blocked "Platform Launch"
```

#### Portfolio critical-path

Computes the longest dependency chain (topological sort). The task whose completion unblocks the most downstream tasks is labelled `← BOTTLENECK`.

```bash
kanboard portfolio critical-path "Platform Launch"
```

Example output:

```
Critical path (4 tasks):
  1. ● #42 Implement OAuth login  ← BOTTLENECK
  2. ● #99 Launch landing page
  3. ● #12 Write release notes
  4. ● #7  Publish to app store
```

#### Common workflows

```bash
# Create a portfolio from scratch
kanboard portfolio create "Platform Launch" --description "Q3 release"
kanboard portfolio add-project "Platform Launch" 1
kanboard portfolio add-project "Platform Launch" 2

# Daily stand-up view
kanboard portfolio show "Platform Launch"
kanboard portfolio blocked "Platform Launch"

# Sprint planning
kanboard portfolio dependencies "Platform Launch" --cross-project-only
kanboard portfolio critical-path "Platform Launch"

# Sync to Kanboard metadata (for external tool integration)
kanboard portfolio sync "Platform Launch"
```

---

### milestone

Cross-project milestone management. Milestones group tasks from multiple projects and track completion, at-risk status, and overdue state.

```
kanboard milestone SUBCOMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `milestone list PORTFOLIO_NAME` | List milestones for a portfolio (name, target date, task count, critical count) |
| `milestone show PORTFOLIO_NAME MILESTONE_NAME` | Progress bar + task list with status indicators and blocker info |
| `milestone create PORTFOLIO_NAME MILESTONE_NAME [--target-date YYYY-MM-DD]` | Create a new milestone |
| `milestone remove PORTFOLIO_NAME MILESTONE_NAME --yes` | Delete a milestone + clean task metadata |
| `milestone add-task PORTFOLIO_NAME MILESTONE_NAME TASK_ID [--critical]` | Add a task to a milestone (validates task belongs to a portfolio project) |
| `milestone remove-task PORTFOLIO_NAME MILESTONE_NAME TASK_ID --yes` | Remove a task from a milestone |
| `milestone progress PORTFOLIO_NAME [MILESTONE_NAME]` | Show progress bars — single milestone or all milestones in the portfolio |

#### Milestone list

```bash
kanboard milestone list "Platform Launch"
kanboard --output json milestone list "Platform Launch"
```

#### Milestone show

Displays a live progress bar (requires API), task counts, and blocked task IDs. Falls back to cached store data with a warning if the API is unreachable.

```bash
kanboard milestone show "Platform Launch" "Beta Release"
```

Example output:

```
Milestone: Beta Release
Portfolio: Platform Launch
Target:    2026-06-30

Progress: ██████████░░░░░░░░░░  50.0%   ⚠ AT RISK
Tasks: 6 total, 3 completed, 2 blocked
```

#### Milestone create / remove

```bash
kanboard milestone create "Platform Launch" "Beta Release" --target-date 2026-06-30
kanboard milestone remove "Platform Launch" "Beta Release" --yes
```

#### Milestone add-task / remove-task

Validates that the task's project is a member of the portfolio before adding.

```bash
# Add a task (must belong to a portfolio project)
kanboard milestone add-task "Platform Launch" "Beta Release" 42

# Mark as critical (appears in critical_task_ids and milestone progress)
kanboard milestone add-task "Platform Launch" "Beta Release" 99 --critical

kanboard milestone remove-task "Platform Launch" "Beta Release" 42 --yes
```

#### Milestone progress

```bash
# All milestones in portfolio
kanboard milestone progress "Platform Launch"

# Single milestone detail
kanboard milestone progress "Platform Launch" "Beta Release"
```

Example output (all milestones):

```
Platform Launch milestones:
  ██████████████░░░░░░  70.0%  Alpha Release         → 2026-05-15
  ⚠ ██████████░░░░░░░░░░  50.0%  Beta Release       → 2026-06-30
  🔴 ░░░░░░░░░░░░░░░░░░░░   0.0%  GA Release         → 2026-03-01
```

Progress bar indicators:

| Symbol | Meaning |
|---|---|
| `⚠` | At risk — target date within 7 days and completion < 80% |
| `🔴` | Overdue — target date has passed and completion < 100% |
