# Do not call `frappe.db.commit()` in a request

## The rule

- Do not call `frappe.db.commit()` in whitelisted methods, controllers or hooks.
- Frappe commits for you at the end of a successful POST request.
- Send writes as POST. GET requests are rolled back.

## How Frappe handles the transaction

Source: `frappe/app.py`, `application` and `sync_database`.

- The whole request is one database transaction.
- Request succeeds and the method is POST, PUT, PATCH or DELETE: Frappe commits.
- Request succeeds and the method is GET: Frappe **rolls back**.
- Request raises an error: Frappe rolls back.

## What we tested

Real HTTP calls to API methods on frappe `develop`:

| Request | Result |
|---|---|
| GET that inserts a ToDo | Response was 200 with the new name. The ToDo was **not saved**. |
| POST that inserts a ToDo | Saved |
| POST that inserts A, commits, inserts B, then fails | A saved, B lost. Half-done data. |
| POST that inserts, then fails, with no commit | Nothing saved. Clean. |

## Why manual commit is bad

- It breaks "all or nothing". An error after the commit leaves half-done data.
- It also fires every `after_commit` callback early, such as jobs enqueued with `enqueue_after_commit=True`.
- Server Scripts for doc events cannot call commit at all. Frappe removes it.

## When commit is OK

- Background jobs and patches that process many records in batches. Commit after each batch so one failure does not undo hours of work.
- Long jobs that must save progress, such as an import with a progress log.
- Code that sends data to an outside system and must record that it was sent, even if the next step fails.

## Do

- Use `frappe.call` with default `type: "POST"` for anything that writes.
- Let the error rise. Frappe rolls back for you.
- Use `frappe.db.savepoint()` and `frappe.db.rollback(save_point=...)` to undo part of the work without ending the transaction.

## Do not

- Do not add `frappe.db.commit()` to "make the save work". If a save is lost, check if the request is a GET.
- Do not write to the database in a GET endpoint.
- Do not catch an exception and continue after a partial write without rolling back.

## Examples

Bad. If `create_invoice` fails, the order is already committed:

```python
@frappe.whitelist()
def place_order(data):
	order = frappe.get_doc(data).insert()
	frappe.db.commit()
	create_invoice(order)
```

Good. Both are saved, or neither:

```python
@frappe.whitelist(methods=["POST"])
def place_order(data):
	order = frappe.get_doc(data).insert()
	create_invoice(order)
```

Good. A background job commits per batch:

```python
def sync_all():
	for batch in frappe.utils.create_batch(names, 500):
		for name in batch:
			sync_one(name)
		frappe.db.commit()
```
