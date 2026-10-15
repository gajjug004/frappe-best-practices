# Showing errors: `frappe.throw` vs `raise`

## The rule

- Use `frappe.throw(_("message"))` for errors the user should read and fix.
- Let real bugs raise on their own. Do not hide them.

## The difference

Tested with real HTTP calls on frappe `develop`:

| | `frappe.throw("Customer is required")` | Code that raises `ZeroDivisionError` |
|---|---|---|
| HTTP status | 417 | 500 |
| Exception type | `ValidationError` | `ZeroDivisionError` |
| `_server_messages` with the message | Yes | No |
| What the user sees | Your message in a dialog | A generic server error |
| Transaction | Rolled back | Rolled back |

- `frappe.throw` adds your message to the response, then raises. Default exception is `frappe.ValidationError`.
- Source: `frappe/utils/messages.py`, `throw`, and `frappe/app.py`, `handle_exception`.

## Pick the right exception class

Pass it as the second argument. The class sets the HTTP status. Source: `frappe/exceptions.py`.

| Use | Class | Status |
|---|---|---|
| Bad input, broken rule | `frappe.ValidationError` (default) | 417 |
| User not allowed | `frappe.PermissionError` | 403 |
| Record not found | `frappe.DoesNotExistError` | 404 |
| Duplicate record | `frappe.DuplicateEntryError` | 409 |

## Do

- Wrap every message in `_()` so it can be translated.
- Say what is wrong and how to fix it: "Delivery Date cannot be before Order Date".
- Use `frappe.bold()` for field values in the message.
- Use `frappe.msgprint` for a message that should not stop the action.

## Do not

- Do not `raise Exception("...")` for user errors. The user gets a 500 and no message.
- Do not catch all exceptions and return `{"error": str(e)}`. The transaction is not rolled back, and the status is 200.
- Do not put a traceback or SQL in the message.

## Examples

Bad:

```python
if not self.customer:
	raise Exception("Customer is required")
```

Good:

```python
if not self.customer:
	frappe.throw(_("Customer is required"))
```

Good. Right status for a permission problem:

```python
if not frappe.has_permission("Sales Invoice", "submit", self.name):
	frappe.throw(_("You cannot submit this invoice"), frappe.PermissionError)
```
