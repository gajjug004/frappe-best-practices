# Updating a record: `frappe.db.set_value` vs `doc.save()`

## The rule

- Use `doc.save()` by default.
- Use `frappe.db.set_value` only when you must skip validation and hooks on purpose.

## The difference

`frappe.db.set_value` runs one `UPDATE` query. Its own docstring says: "will not call Document events and should be avoided in normal cases".

Source: `frappe/database/database.py`, `set_value`.

| | `doc.save()` | `frappe.db.set_value` |
|---|---|---|
| Runs `validate`, `on_update` and other hooks | Yes | No |
| Checks mandatory fields | Yes | No |
| Checks `write` permission | Yes | No |
| Creates a Version (change history) | Yes, if Track Changes is on | No |
| Updates `modified` | Yes | Yes, unless `update_modified=False` |
| Clears the document cache | Yes | Yes |
| Number of queries | Many | One |

Tested on frappe `develop` with a ToDo:

- `set_value` saved an empty `description`, which is a mandatory field. `save()` raised `MandatoryError` for the same change.
- `set_value` created no Version. `save()` created one.

## Use `doc.save()` for

- Any change a user makes.
- Any change that other code may react to through hooks.
- Any field that has validation rules.

## Use `frappe.db.set_value` for

- Patches that fix data in bulk.
- Status or counter fields that you update from inside a hook, where saving again would loop.
- Background bookkeeping, with `update_modified=False` so users do not see a fake edit.

## Do not

- Do not use `set_value` to get around a validation error. Fix the data or the rule.
- Do not use `set_value` in a whitelisted method on user input. It skips the permission check.
- Do not call `doc.save()` inside the same doc's `on_update`. Use `self.db_set("field", value)` instead.

## Examples

Good. A user action goes through the full lifecycle:

```python
doc = frappe.get_doc("ToDo", name)
doc.check_permission("write")
doc.status = "Closed"
doc.save()
```

Good. Inside a hook, update one field without running hooks again:

```python
def on_update(self):
	self.db_set("last_synced", now(), update_modified=False)
```

Bad. Skips validation, permissions and history:

```python
@frappe.whitelist()
def close(name):
	frappe.db.set_value("ToDo", name, "status", "Closed")
```
