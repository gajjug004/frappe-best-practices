# Writing safe whitelisted methods

## The rule

- Every `@frappe.whitelist()` function is a public API. Anyone logged in can call it with any arguments.
- Add type hints to every argument.
- Limit the HTTP method with `methods=[...]`.
- Use `allow_guest=True` only for truly public endpoints.

## What we tested

Real requests through the full Frappe request stack on frappe `develop`:

| Case | Result |
|---|---|
| `def double(n)` with types off, called with `n=5` | Returned `"55"`. The argument arrived as a string. |
| `def double(n)` in an app with `require_type_annotated_api_methods = True` | 417. Untyped argument rejected. |
| `def double_typed(n: int)` called with `n=5` | Returned `10`. Frappe converted it. |
| `def double_typed(n: int)` called with `n=abc` | 417 |
| `methods=["POST"]`, called with GET | 403 |
| `methods=["POST"]`, called with POST | 200 |
| Normal whitelisted method, called as Guest | 403 |
| `allow_guest=True`, called as Guest | 200 |
| Function without `@frappe.whitelist` | 403 |

Source: `frappe/__init__.py`, `whitelist`, and `frappe/utils/typing_validations.py`.

## Type hints

- Form and query values arrive as strings. Without a type hint, `n * 2` on `"5"` gives `"55"`.
- With a type hint, Frappe converts the value or rejects it with 417.
- frappe, erpnext, hrms, crm, helpdesk and others set `require_type_annotated_api_methods = True` in `hooks.py`. Then every argument **must** have a type hint.
- Add the same line to your app's `hooks.py`.

## Do

- Use `methods=["POST"]` for anything that writes. GET requests are rolled back anyway.
- Check permissions inside the method. See [Which APIs check permissions](which-apis-check-permissions.md).
- Use `frappe.only_for("System Manager")` for admin-only methods.
- Add `@rate_limit(...)` from `frappe.rate_limiter` to guest endpoints, such as contact forms.
- Keep helper functions without `@frappe.whitelist`. Only the entry point needs it.

## Do not

- Do not whitelist a function "just in case". Every whitelisted function is attack surface.
- Do not accept `doctype` or `fieldname` from the user and pass it straight into a query.
- Do not use `allow_guest=True` on anything that reads private data.
- Do not trust `**kwargs`. Name every argument.

## Examples

Bad. Untyped, any method, no permission check:

```python
@frappe.whitelist()
def set_discount(invoice, percent):
	frappe.db.set_value("Sales Invoice", invoice, "additional_discount_percentage", percent)
```

Good:

```python
@frappe.whitelist(methods=["POST"])
def set_discount(invoice: str, percent: float):
	doc = frappe.get_doc("Sales Invoice", invoice)
	doc.check_permission("write")
	doc.additional_discount_percentage = percent
	doc.save()
```

Good. A public form with a rate limit:

```python
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def contact_us(email: str, message: str):
	...
```
