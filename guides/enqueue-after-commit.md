# Background jobs: use `enqueue_after_commit=True`

## The rule

- When a job reads data you just wrote, enqueue it with `enqueue_after_commit=True`.

## Why

- `frappe.enqueue` pushes the job to Redis right away.
- A worker can pick it up before your request commits.
- The job then runs in its own transaction and cannot see your uncommitted rows.
- If your request fails and rolls back, the job still runs.

With `enqueue_after_commit=True`, Frappe holds the job and pushes it only after the commit. If the transaction rolls back, the job is dropped.

Source: `frappe/utils/background_jobs.py`, `enqueue`.

## What we tested

On frappe `develop` with a real worker. Each case inserts a ToDo, then enqueues a job that counts it:

| Case | Result |
|---|---|
| Plain `enqueue`, job runs before commit | Job counted **0** rows |
| `enqueue_after_commit=True`, before commit | No job in Redis yet |
| `enqueue_after_commit=True`, then commit | Job counted **1** row |
| `enqueue_after_commit=True`, then rollback | Job never created |

## Use `enqueue_after_commit=True` for

- Jobs started from `on_update`, `on_submit` and other doc hooks.
- Jobs that read the record you just saved.
- Sending emails or calling outside APIs about a new record.

## A plain `enqueue` is fine for

- Jobs that do not depend on the current transaction.
- Code that runs outside a transaction, such as a scheduler entry point.

## Do not

- Do not call `frappe.db.commit()` before `enqueue` to fix the timing. Use the flag.
- Do not pass a whole `doc` object to a job. Pass the name and load it in the job.
- Do not use `now=True` outside tests. It runs the job inside the request.

## Examples

Bad. The worker may not find the invoice, or may email about one that was rolled back:

```python
def on_submit(self):
	frappe.enqueue("my_app.api.send_invoice_email", invoice=self.name)
```

Good:

```python
def on_submit(self):
	frappe.enqueue(
		"my_app.api.send_invoice_email",
		invoice=self.name,
		enqueue_after_commit=True,
	)
```
