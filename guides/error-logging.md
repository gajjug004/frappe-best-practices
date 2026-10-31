# Logging errors: `frappe.log_error` and `frappe.logger`

## The rule

- Call `frappe.log_error(title)` inside an `except` block when you catch an error and do not re-raise it.
- Give it a short, searchable title. Pass `reference_doctype` and `reference_name` when a record is involved.
- Do not log errors Frappe already logs for you. Uncaught 500 errors and failed background jobs are logged on their own.
- Use `frappe.logger("your_app")` for trace lines in a file, not for errors someone must act on.

## Why

- A swallowed exception with no log is invisible. Nobody knows the sync failed.
- `log_error` saves the traceback, the request or job details, the user, and a fingerprint that groups repeats.
- The Error Log list is where admins look. A log file on the server is not.

## What we tested

Tested on frappe `develop` with MariaDB, after frappe#43000. Check: `checks/verify_error_logging.py`.

| Case | Result |
|---|---|
| `log_error("title")` inside `except` | Traceback saved automatically, fingerprint set |
| `log_error("title")` outside `except` | Error body is empty, no fingerprint |
| `log_error("title", message="...")` | Your message is the error body |
| `log_error(traceback, "title")`, args swapped | Fixed for you if the first arg has a newline |
| Title longer than 140 chars | Cut to 140. Full title moved to the error body |
| `log_error` then `frappe.db.rollback()` | Log is kept. The log database commits on its own, so rollback does not touch it |
| `frappe.get_all("Error Log", ...)` | Works |
| `frappe.db.exists("Error Log", ...)` | Returns `None` even when the log exists. No error |
| `frappe.db.delete("Error Log", ...)` or raw SQL | Raises 1146, table does not exist |
| Request raises `frappe.ValidationError` (`frappe.throw`) | Not logged. Logged only when `developer_mode` is on |
| Request raises any 500 error | Logged |
| Background job raises, even `frappe.throw` | Logged. Title is the job's method path |
| `frappe.logger("x").info(...)` | Dropped. Default level is ERROR, or WARNING under `bench start` |
| `frappe.logger("x").error(...)` | Written to `sites/<site>/logs/x.log` |

- Source: `frappe/utils/error.py`, `log_error` and `log_error_snapshot`. `frappe/app.py`, `handle_exception`. `frappe/utils/background_jobs.py`, `execute_job`. `frappe/utils/logger.py`.
- On `develop`, Error Log is a virtual DocType. Its rows live in a separate SQLite file, `sites/<site>/private/files/sqlite.db`, not in MariaDB. Access Log, Activity Log, Route History and Web Page View work the same way. Source: frappe#43000, `frappe/utils/sqlite_document.py`, `frappe/utils/logging.py`.
- On `version-16` and older, Error Log is still a MyISAM table in MariaDB.
- Error Logs are deleted after 14 days by default. Change it in Log Settings. Source: `default_log_clearing_doctypes` in `frappe/hooks.py`.

## Do

- Log inside `except`, so the traceback is captured.
- Use a fixed title per failure type, like `"Shopify order sync failed"`. Put the changing part in `reference_name` or `message`.
- Pass `message=` when there is no exception, so the log has a body.
- Log and then `frappe.throw` when the user must see the error and you also want a record. The log survives the rollback on MariaDB.
- Use `frappe.logger("your_app")` for debug and audit lines. Call `.warning` or `.error`, or turn on lower levels with `frappe.utils.logger.set_log_level("INFO")`.

## Do not

- Do not write `except Exception: pass`. Log it or let it raise.
- Do not call `log_error` and then re-raise a bug or a job error. Frappe logs uncaught 500 errors and job failures again, so you get two logs.
- Do not log `frappe.throw` validation errors. They are user mistakes, not bugs.
- Do not put the record name or a timestamp in the title. Every log gets a new title and grouping by title breaks.
- Do not put passwords, tokens, or full API payloads with secrets in `message`. Any System Manager can read Error Logs.
- Do not read or delete Error Log with `frappe.db.*` or raw SQL. Use `frappe.get_all`, `frappe.get_doc` or `frappe.delete_doc`. In tests, patch `frappe.log_error` and assert the call.
- Do not use `print` for errors. It goes to the worker console and is lost.
- Do not expect `logger.info` to show up in production. It is dropped unless you raise the log level.

## Examples

Bad. The failure disappears:

```python
for order in orders:
	try:
		create_sales_order(order)
	except Exception:
		pass
```

Bad. Name in the title, no traceback:

```python
for order in orders:
	try:
		create_sales_order(order)
	except Exception as e:
		frappe.log_error(f"Order {order.id} failed: {e}")
```

Good. One failed order does not stop the rest, and each failure is logged with a stable title:

```python
for order in orders:
	try:
		create_sales_order(order)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Shopify order sync failed", reference_doctype="Shopify Order", reference_name=order.id)
```

Good. Nothing to catch, so pass the details as `message`:

```python
if response.status_code != 200:
	frappe.log_error("Shopify API error", message=f"Status {response.status_code}\n{response.text}")
```

Good. Trace lines in a file:

```python
logger = frappe.logger("shopify")
logger.warning(f"Rate limited, retrying order {order.id}")
```
