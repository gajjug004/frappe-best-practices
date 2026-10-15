# Counters and stock: lock the row with `for_update=True`

## The rule

- When you read a value, change it, and write it back, lock the row first.
- Use `frappe.db.get_value(..., for_update=True)` or `frappe.get_doc(..., for_update=True)`.

## Why

Two requests can read the same value at the same time. Both add 1. Both write. One update is lost.

`for_update=True` runs `SELECT ... FOR UPDATE`. The second request waits until the first one commits, then reads the new value.

## What we tested

Two threads on frappe `develop`, each adds 1 to the same record at the same time, starting from 0:

| Code | Final value | Result |
|---|---|---|
| `db.get_value`, then `db.set_value` | 1 | One update **silently lost** |
| `db.get_value(..., for_update=True)`, then `db.set_value` | 2 | Correct |
| `get_doc`, change, `save()` | 1 | Second save failed with `TimestampMismatchError` |
| `get_doc(..., for_update=True)`, change, `save()` | 2 | Correct |

- `doc.save()` has its own safety net. It compares the `modified` timestamp and refuses to overwrite a newer version. That stops the silent loss, but the user gets an error.
- `db.set_value` has no safety net at all.

## Use `for_update=True` for

- Counters and running totals.
- Stock, seats, credits, balances, or any "take one" logic.
- Picking the next free item from a list.
- Any read-check-write where the check must stay true until you write.

## Do

- Keep the locked part short. Do the slow work before you lock.
- Lock rows in the same order everywhere, to avoid deadlocks.
- Let the request commit to release the lock. In a background job, commit when done.

## Do not

- Do not call an outside API while holding a lock.
- Do not lock rows in GET endpoints or list views.
- Do not use `for_update` on reads that never write back. It only slows other users down.

## Examples

Bad. Two users can book the last seat:

```python
seats = frappe.db.get_value("Event", event, "seats_left")
if seats > 0:
	frappe.db.set_value("Event", event, "seats_left", seats - 1)
```

Good:

```python
seats = frappe.db.get_value("Event", event, "seats_left", for_update=True)
if seats <= 0:
	frappe.throw(_("No seats left"))
frappe.db.set_value("Event", event, "seats_left", seats - 1)
```

Good. With the full document:

```python
event = frappe.get_doc("Event", name, for_update=True)
event.seats_left -= 1
event.save()
```
