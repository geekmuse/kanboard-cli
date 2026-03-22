# Kanboard API Specification Reference

> ← [Architecture](01-architecture.md) | [README](README.md) | [Milestone 1](03-milestone-1-foundation.md) →
>
> This file contains the complete API spec needed to implement every SDK resource module.

> Source: https://docs.kanboard.org/v1/api/
> Protocol: JSON-RPC 2.0 over HTTP POST to a single endpoint (e.g., `https://host/jsonrpc.php`).

### JSON-RPC Request/Response Format

```json
// Request
{"jsonrpc": "2.0", "method": "methodName", "id": 123, "params": {"key": "value"}}
// Success
{"jsonrpc": "2.0", "id": 123, "result": <value>}
// Error
{"jsonrpc": "2.0", "id": 123, "error": {"code": -32600, "message": "..."}}
```

Batch: send array of requests, receive array of responses.

### Authentication

**Application API** (used at launch): HTTP Basic Auth, username `jsonrpc`, token from Settings → API. Full access except `getMe*`/`getMy*` procedures (those require User API auth).

### API Category: Application (7 methods)

| Method | Params | Returns |
|---|---|---|
| `getVersion` | none | `string` |
| `getTimezone` | none | `string` |
| `getDefaultTaskColors` | none | `dict` |
| `getDefaultTaskColor` | none | `string` color_id |
| `getColorList` | none | `dict` color_id → name |
| `getApplicationRoles` | none | `dict` role → name |
| `getProjectRoles` | none | `dict` role → name |

### API Category: Projects (14 methods)

| Method | Params | Returns |
|---|---|---|
| `createProject` | `name` (str, **req**), `description` (str, opt), `owner_id` (int, opt), `identifier` (str, opt), `start_date` (str ISO8601, opt), `end_date` (str ISO8601, opt), `priority_default` (int, opt), `priority_start` (int, opt), `priority_end` (int, opt), `email` (str, opt) | `int` project_id or `false` |
| `getProjectById` | `project_id` (int, **req**) | project dict or `null` |
| `getProjectByName` | `name` (str, **req**) | project dict or `null` |
| `getProjectByIdentifier` | `identifier` (str, **req**) | project dict or `null` |
| `getProjectByEmail` | `email` (str, **req**) | project dict or `null` |
| `getAllProjects` | none | `list[dict]` or `false` |
| `updateProject` | `project_id` (int, **req**), `name` (str, opt), `description` (str, opt), `owner_id` (int, opt), `identifier` (str, opt), `start_date` (str, opt), `end_date` (str, opt), `priority_default` (int, opt), `priority_start` (int, opt), `priority_end` (int, opt), `email` (str, opt) | `true` or `false` |
| `removeProject` | `project_id` (int, **req**) | `true` or `false` |
| `enableProject` | `project_id` (int, **req**) | `true` or `false` |
| `disableProject` | `project_id` (int, **req**) | `true` or `false` |
| `enableProjectPublicAccess` | `project_id` (int, **req**) | `true` or `false` |
| `disableProjectPublicAccess` | `project_id` (int, **req**) | `true` or `false` |
| `getProjectActivity` | `project_id` (int, **req**) | `list[dict]` or `false` |
| `getProjectActivities` | `project_ids` (int[], **req**) | `list[dict]` or `false` |

### API Category: Board (1 method)

| Method | Params | Returns |
|---|---|---|
| `getBoard` | `project_id` (int, **req**) | nested board data or `[]` |

### API Category: Tasks (14 methods)

| Method | Params | Returns |
|---|---|---|
| `createTask` | `title` (str, **req**), `project_id` (int, **req**), `color_id` (str, opt), `column_id` (int, opt), `owner_id` (int, opt), `creator_id` (int, opt), `date_due` (str `YYYY-MM-DD HH:MM`, opt), `description` (str, opt), `category_id` (int, opt), `score` (int, opt), `swimlane_id` (int, opt), `priority` (int, opt), `recurrence_status` (int, opt), `recurrence_trigger` (int, opt), `recurrence_factor` (int, opt), `recurrence_timeframe` (int, opt), `recurrence_basedate` (int, opt), `reference` (str, opt), `tags` (str[], opt), `date_started` (str, opt) | `int` task_id or `false` |
| `getTask` | `task_id` (int, **req**) | task dict or `null` |
| `getTaskByReference` | `project_id` (int, **req**), `reference` (str, **req**) | task dict or `null` |
| `getAllTasks` | `project_id` (int, **req**), `status_id` (int, **req**: 1=active, 0=inactive) | `list[dict]` or `false` |
| `getOverdueTasks` | none | `list[dict]` or `false` |
| `getOverdueTasksByProject` | `project_id` (int, **req**) | `list[dict]` or `false` |
| `updateTask` | `id` (int, **req**), `title` (str, opt), `color_id` (str, opt), `owner_id` (int, opt), `date_due` (str, opt), `description` (str, opt), `category_id` (int, opt), `score` (int, opt), `priority` (int, opt), `recurrence_status` (int, opt), `recurrence_trigger` (int, opt), `recurrence_factor` (int, opt), `recurrence_timeframe` (int, opt), `recurrence_basedate` (int, opt), `reference` (str, opt), `tags` (str[], opt), `date_started` (str, opt) | `true` or `false` |
| `openTask` | `task_id` (int, **req**) | `true` or `false` |
| `closeTask` | `task_id` (int, **req**) | `true` or `false` |
| `removeTask` | `task_id` (int, **req**) | `true` or `false` |
| `moveTaskPosition` | `project_id` (int, **req**), `task_id` (int, **req**), `column_id` (int, **req**), `position` (int, **req**), `swimlane_id` (int, **req**) | `true` or `false` |
| `moveTaskToProject` | `task_id` (int, **req**), `project_id` (int, **req**), `swimlane_id` (int, opt), `column_id` (int, opt), `category_id` (int, opt), `owner_id` (int, opt) | `true` or `false` |
| `duplicateTaskToProject` | `task_id` (int, **req**), `project_id` (int, **req**), `swimlane_id` (int, opt), `column_id` (int, opt), `category_id` (int, opt), `owner_id` (int, opt) | `int` task_id or `false` |
| `searchTasks` | `project_id` (int, **req**), `query` (str, **req**) | `list[dict]` or `false` |

### API Category: Columns (6 methods)

| Method | Params | Returns |
|---|---|---|
| `getColumns` | `project_id` (int, **req**) | `list[dict]` or `[]` |
| `getColumn` | `column_id` (int, **req**) | column dict or `null` |
| `changeColumnPosition` | `project_id` (int, **req**), `column_id` (int, **req**), `position` (int >=1, **req**) | `true` or `false` |
| `updateColumn` | `column_id` (int, **req**), `title` (str, **req**), `task_limit` (int, opt), `description` (str, opt) | `true` or `false` |
| `addColumn` | `project_id` (int, **req**), `title` (str, **req**), `task_limit` (int, opt), `description` (str, opt) | `int` column_id or `false` |
| `removeColumn` | `column_id` (int, **req**) | `true` or `false` |

### API Category: Swimlanes (11 methods)

| Method | Params | Returns |
|---|---|---|
| `getActiveSwimlanes` | `project_id` (int, **req**) | `list[dict]` or `null` |
| `getAllSwimlanes` | `project_id` (int, **req**) | `list[dict]` or `null` |
| `getSwimlane` | `swimlane_id` (int, **req**) | swimlane dict or `null` |
| `getSwimlaneById` | `swimlane_id` (int, **req**) | swimlane dict or `null` |
| `getSwimlaneByName` | `project_id` (int, **req**), `name` (str, **req**) | swimlane dict or `null` |
| `changeSwimlanePosition` | `project_id` (int, **req**), `swimlane_id` (int, **req**), `position` (int >=1, **req**) | `true` or `false` |
| `updateSwimlane` | `project_id` (int, **req**), `swimlane_id` (int, **req**), `name` (str, **req**), `description` (str, opt) | `true` or `false` |
| `addSwimlane` | `project_id` (int, **req**), `name` (str, **req**), `description` (str, opt) | `int` swimlane_id or `false` |
| `removeSwimlane` | `project_id` (int, **req**), `swimlane_id` (int, **req**) | `true` or `false` |
| `disableSwimlane` | `project_id` (int, **req**), `swimlane_id` (int, **req**) | `true` or `false` |
| `enableSwimlane` | `project_id` (int, **req**), `swimlane_id` (int, **req**) | `true` or `false` |

### API Category: Categories (5 methods)

| Method | Params | Returns |
|---|---|---|
| `createCategory` | `project_id` (int, **req**), `name` (str, **req**, unique per project), `color_id` (str, opt) | `int` category_id or `false` |
| `getCategory` | `category_id` (int, **req**) | category dict or `null` |
| `getAllCategories` | `project_id` (int, **req**) | `list[dict]` or `false` |
| `updateCategory` | `id` (int, **req**), `name` (str, **req**), `color_id` (str, opt) | `true` or `false` |
| `removeCategory` | `category_id` (int, **req**) | `true` or `false` |

### API Category: Comments (5 methods)

| Method | Params | Returns |
|---|---|---|
| `createComment` | `task_id` (int, **req**), `user_id` (int, **req**), `content` (str, **req**), `reference` (str, opt), `visibility` (str, opt: "app-user"/"app-manager"/"app-admin") | `int` comment_id or `false` |
| `getComment` | `comment_id` (int, **req**) | comment dict or `null` |
| `getAllComments` | `task_id` (int, **req**) | `list[dict]` or `false` |
| `updateComment` | `id` (int, **req**), `content` (str, **req**) | `true` or `false` |
| `removeComment` | `comment_id` (int, **req**) | `true` or `false` |

### API Category: Subtasks (5 methods)

| Method | Params | Returns |
|---|---|---|
| `createSubtask` | `task_id` (int, **req**), `title` (str, **req**), `user_id` (int, opt), `time_estimated` (int, opt), `time_spent` (int, opt), `status` (int, opt) | `int` subtask_id or `false` |
| `getSubtask` | `subtask_id` (int, **req**) | subtask dict or `null` |
| `getAllSubtasks` | `task_id` (int, **req**) | `list[dict]` or `false` |
| `updateSubtask` | `id` (int, **req**), `task_id` (int, **req**), `title` (str, opt), `user_id` (int, opt), `time_estimated` (int, opt), `time_spent` (int, opt), `status` (int, opt) | `true` or `false` |
| `removeSubtask` | `subtask_id` (int, **req**) | `true` or `false` |

### API Category: Subtask Time Tracking (4 methods)

| Method | Params | Returns |
|---|---|---|
| `hasSubtaskTimer` | `subtask_id` (int, **req**), `user_id` (int, opt) | `true` or `false` |
| `setSubtaskStartTime` | `subtask_id` (int, **req**), `user_id` (int, opt) | `true` or `false` |
| `setSubtaskEndTime` | `subtask_id` (int, **req**), `user_id` (int, opt) | `true` or `false` |
| `getSubtaskTimeSpent` | `subtask_id` (int, **req**), `user_id` (int, opt) | `float` hours or `false` |

### API Category: Users (10 methods)

| Method | Params | Returns |
|---|---|---|
| `createUser` | `username` (str, **req**, unique), `password` (str, **req**, >=6 chars), `name` (str, opt), `email` (str, opt), `role` (str, opt: "app-admin"/"app-manager"/"app-user") | `int` user_id or `false` |
| `createLdapUser` | `username` (str, **req**) | `int` user_id or `false` |
| `getUser` | `user_id` (int, **req**) | user dict or `null` |
| `getUserByName` | `username` (str, **req**) | user dict or `null` |
| `getAllUsers` | none | `list[dict]` or `false` |
| `updateUser` | `id` (int, **req**), `username` (str, opt), `name` (str, opt), `email` (str, opt), `role` (str, opt) | `true` or `false` |
| `removeUser` | `user_id` (int, **req**) | `true` or `false` |
| `disableUser` | `user_id` (int, **req**) | `true` or `false` |
| `enableUser` | `user_id` (int, **req**) | `true` or `false` |
| `isActiveUser` | `user_id` (int, **req**) | `true` or `false` |

### API Category: Current User / "Me" (7 methods)

> **Requires User API authentication** — not Application API. Raise `KanboardAuthError` until Task 46.

| Method | Params | Returns |
|---|---|---|
| `getMe` | none | user session dict or `false` |
| `getMyDashboard` | none | dashboard dict or `false` |
| `getMyActivityStream` | none | `list[dict]` (last 100) or `false` |
| `createMyPrivateProject` | `name` (str, **req**), `description` (str, opt) | `int` project_id or `false` |
| `getMyProjectsList` | none | `dict` project_id -> name or `false` |
| `getMyOverdueTasks` | none | `list[dict]` or `false` |
| `getMyProjects` | none | `list[dict]` or `false` |

### API Category: Tags (7 methods)

| Method | Params | Returns |
|---|---|---|
| `getAllTags` | none | `list[dict]` or `false`/`null` |
| `getTagsByProject` | `project_id` (int, **req**) | `list[dict]` or `false`/`null` |
| `createTag` | `project_id` (int, **req**), `tag` (str, **req**), `color_id` (str, opt) | `int` tag_id or `false` |
| `updateTag` | `tag_id` (int, **req**), `tag` (str, **req**), `color_id` (str, opt) | `true` or `false` |
| `removeTag` | `tag_id` (int, **req**) | `true` or `false` |
| `setTaskTags` | `project_id` (int, **req**), `task_id` (int, **req**), `tags` (str[], **req**) | `true` or `false` |
| `getTaskTags` | `task_id` (int, **req**) | `dict` or `false`/`null` |

### API Category: Link Types (7 methods)

| Method | Params | Returns |
|---|---|---|
| `getAllLinks` | none | `list[dict]` or `false` |
| `getOppositeLinkId` | `link_id` (int, **req**) | `int` or `false` |
| `getLinkByLabel` | `label` (str, **req**) | link dict or `false` |
| `getLinkById` | `link_id` (int, **req**) | link dict or `false` |
| `createLink` | `label` (str, **req**), `opposite_label` (str, opt) | `int` link_id or `false` |
| `updateLink` | `link_id` (int, **req**), `opposite_link_id` (int, **req**), `label` (str, **req**) | `true` or `false` |
| `removeLink` | `link_id` (int, **req**) | `true` or `false` |

### API Category: Internal Task Links (5 methods)

| Method | Params | Returns |
|---|---|---|
| `createTaskLink` | `task_id` (int, **req**), `opposite_task_id` (int, **req**), `link_id` (int, **req**) | `int` task_link_id or `false` |
| `updateTaskLink` | `task_link_id` (int, **req**), `task_id` (int, **req**), `opposite_task_id` (int, **req**), `link_id` (int, **req**) | `true` or `false` |
| `getTaskLinkById` | `task_link_id` (int, **req**) | task link dict or `false` |
| `getAllTaskLinks` | `task_id` (int, **req**) | `list[dict]` or `false` |
| `removeTaskLink` | `task_link_id` (int, **req**) | `true` or `false` |

### API Category: External Task Links (7 methods)

| Method | Params | Returns |
|---|---|---|
| `getExternalTaskLinkTypes` | none | `dict` |
| `getExternalTaskLinkProviderDependencies` | `providerName` (str, **req**) | `dict` |
| `createExternalTaskLink` | `task_id` (int, **req**), `url` (str, **req**), `dependency` (str, **req**), `type` (str, opt), `title` (str, opt) | `int` link_id or `false` |
| `updateExternalTaskLink` | `task_id` (int, **req**), `link_id` (int, **req**), `title` (str, **req**), `url` (str, **req**), `dependency` (str, opt) | `true` or `false` |
| `getExternalTaskLinkById` | `task_id` (int, **req**), `link_id` (int, **req**) | `dict` or `false` |
| `getAllExternalTaskLinks` | `task_id` (int, **req**) | `list[dict]` or `false` |
| `removeExternalTaskLink` | `task_id` (int, **req**), `link_id` (int, **req**) | `true` or `false` |

### API Category: Groups (5 methods)

| Method | Params | Returns |
|---|---|---|
| `createGroup` | `name` (str, **req**), `external_id` (str, opt) | `int` group_id or `false` |
| `getGroup` | `group_id` (int, **req**) | group dict or `false` |
| `getAllGroups` | none | `list[dict]` or `false` |
| `updateGroup` | `group_id` (int, **req**), `name` (str, opt), `external_id` (str, opt) | `true` or `false` |
| `removeGroup` | `group_id` (int, **req**) | `true` or `false` |

### API Category: Group Members (5 methods)

| Method | Params | Returns |
|---|---|---|
| `getMemberGroups` | `user_id` (int, **req**) | `list[dict]` or `false` |
| `getGroupMembers` | `group_id` (int, **req**) | `list[dict]` or `false` |
| `addGroupMember` | `group_id` (int, **req**), `user_id` (int, **req**) | `true` or `false` |
| `removeGroupMember` | `group_id` (int, **req**), `user_id` (int, **req**) | `true` or `false` |
| `isGroupMember` | `group_id` (int, **req**), `user_id` (int, **req**) | `true` or `false` |

### API Category: Automatic Actions (6 methods)

| Method | Params | Returns |
|---|---|---|
| `getAvailableActions` | none | `dict` or `false` |
| `getAvailableActionEvents` | none | `dict` or `false` |
| `getCompatibleActionEvents` | `action_name` (str, **req**) | `list` or `false` |
| `getActions` | `project_id` (int, **req**) | `list[dict]` or `false` |
| `createAction` | `project_id` (int, **req**), `event_name` (str, **req**), `action_name` (str, **req**), `params` (dict, **req**) | `int` action_id or `false` |
| `removeAction` | `action_id` (int, **req**) | `true` or `false` |

### API Category: Project Files (6 methods)

| Method | Params | Returns |
|---|---|---|
| `createProjectFile` | `project_id` (int, **req**), `filename` (str, **req**), `blob` (str base64, **req**) | `int` file_id or `false` |
| `getAllProjectFiles` | `project_id` (int, **req**) | `list[dict]` or `false` |
| `getProjectFile` | `project_id` (int, **req**), `file_id` (int, **req**) | file dict or `false` |
| `downloadProjectFile` | `project_id` (int, **req**), `file_id` (int, **req**) | `string` base64 or `""` |
| `removeProjectFile` | `project_id` (int, **req**), `file_id` (int, **req**) | `true` or `false` |
| `removeAllProjectFiles` | `project_id` (int, **req**) | `true` or `false` |

### API Category: Task Files (6 methods)

| Method | Params | Returns |
|---|---|---|
| `createTaskFile` | `project_id` (int, **req**), `task_id` (int, **req**), `filename` (str, **req**), `blob` (str base64, **req**) | `int` file_id or `false` |
| `getAllTaskFiles` | `task_id` (int, **req**) | `list[dict]` or `false` |
| `getTaskFile` | `file_id` (int, **req**) | file dict or `false` |
| `downloadTaskFile` | `file_id` (int, **req**) | `string` base64 or `""` |
| `removeTaskFile` | `file_id` (int, **req**) | `true` or `false` |
| `removeAllTaskFiles` | `task_id` (int, **req**) | `true` or `false` |

### API Category: Project Metadata (4 methods)

| Method | Params | Returns |
|---|---|---|
| `getProjectMetadata` | `project_id` (int, **req**) | `dict` or `false` |
| `getProjectMetadataByName` | `project_id` (int, **req**), `name` (str, **req**) | mixed or `""` |
| `saveProjectMetadata` | `project_id` (int, **req**), `values` (dict, **req**) | `true` or `false` |
| `removeProjectMetadata` | `project_id` (int, **req**), `name` (str, **req**) | `true` or `false` |

### API Category: Task Metadata (4 methods)

| Method | Params | Returns |
|---|---|---|
| `getTaskMetadata` | `task_id` (int, **req**) | `dict` or `[]` |
| `getTaskMetadataByName` | `task_id` (int, **req**), `name` (str, **req**) | mixed or `""` |
| `saveTaskMetadata` | `task_id` (int, **req**), `values` (dict, **req**) | `true` or `false` |
| `removeTaskMetadata` | `task_id` (int, **req**), `name` (str, **req**) | `true` or `false` |

### API Category: Project Permissions (9 methods)

| Method | Params | Returns |
|---|---|---|
| `getProjectUsers` | `project_id` (int, **req**) | `dict` user_id -> name or `false` |
| `getAssignableUsers` | `project_id` (int, **req**), `prepend_unassigned` (bool, opt) | `dict` user_id -> name or `false` |
| `addProjectUser` | `project_id` (int, **req**), `user_id` (int, **req**), `role` (str, opt) | `true` or `false` |
| `addProjectGroup` | `project_id` (int, **req**), `group_id` (int, **req**), `role` (str, opt) | `true` or `false` |
| `removeProjectUser` | `project_id` (int, **req**), `user_id` (int, **req**) | `true` or `false` |
| `removeProjectGroup` | `project_id` (int, **req**), `group_id` (int, **req**) | `true` or `false` |
| `changeProjectUserRole` | `project_id` (int, **req**), `user_id` (int, **req**), `role` (str, **req**) | `true` or `false` |
| `changeProjectGroupRole` | `project_id` (int, **req**), `group_id` (int, **req**), `role` (str, **req**) | `true` or `false` |
| `getProjectUserRole` | `project_id` (int, **req**), `user_id` (int, **req**) | `string` role or `false` |

---

