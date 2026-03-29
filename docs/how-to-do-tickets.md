# How to Do Tickets

We use `TICKETS.md` at the project root as our ticket board. No external tools needed.

## Adding a ticket

1. Open `TICKETS.md`
2. Add a line under **Backlog**:
   ```
   - [ ] #NNN type: Short title
         Added: YYYY-MM-DD | Priority: medium
         Notes: Any extra context.
   ```
3. Increment the `Next ID` counter at the bottom of the file.

Types: `bug`, `feature`, `chore`, `docs`
Priorities: `low`, `medium`, `high`, `critical`

## Working on a ticket

1. Move the ticket block from **Backlog** to **In Progress**.
2. Only keep 1-2 tickets in progress at a time.

## Completing a ticket

1. Move the ticket block from **In Progress** to **Done**.
2. Change `- [ ]` to `- [x]`.
3. Optionally add a completion note:
   ```
   - [x] #003 bug: Fix cursor jump on delete
         Added: 2026-03-29 | Priority: high
         Done: 2026-03-30 | Commit: a1b2c3d
   ```

## Asking Claude to work on tickets

You can say things like:
- "Pick up the next high-priority ticket"
- "Add a bug: [description]"
- "Mark #003 as done"
- "What's in progress?"

Claude will read and update `TICKETS.md` directly.

## Tips

- Keep titles short (~60 chars). Put details in the Notes line.
- Use the Notes line for reproduction steps (bugs) or acceptance criteria (features).
- IDs are permanent. Don't renumber after deleting.
- Periodically clean out Done items by moving them to a `## Archive` section or deleting them.
