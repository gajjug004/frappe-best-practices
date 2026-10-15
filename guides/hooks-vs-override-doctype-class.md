# Changing another app's DocType: hooks vs `override_doctype_class`

## The rule

- Use `doc_events` in `hooks.py` first.
- On v16 and later, use `extend_doctype_class` when you need to add methods.
- Use `override_doctype_class` only when nothing else works.

## Why

`override_doctype_class` replaces the controller. If two apps override the same DocType, Frappe uses only the last one. Source: `frappe/model/base_document.py`, `import_controller`, which takes `class_overrides[doctype][-1]`.

Tested on frappe `develop` with two apps hooking into ToDo `validate`:

| Hook | What ran |
|---|---|
| `override_doctype_class` in both apps | Only app B. App A's code was **silently skipped**. |
| `extend_doctype_class` in both apps | Both |
| `doc_events` in both apps | Both, in app install order |

## The three options

| | `doc_events` | `extend_doctype_class` | `override_doctype_class` |
|---|---|---|---|
| Works with other apps doing the same | Yes | Yes | No, last app wins |
| Add new methods to the doc | No | Yes | Yes |
| Change how a core method works | No | Yes, with `super()` | Yes |
| Available in | All versions | v16 and later | All versions |

## Do

- Use `doc_events` for "do something when X happens": validate, on_submit, on_cancel.
- Use `extend_doctype_class` to add methods or wrap a method with `super()`.
- Always call `super()` in an extended or overridden method.
- Override only the methods you need.

## Do not

- Do not override a class just to add a `validate` rule. Use `doc_events`.
- Do not override a DocType that ERPNext, HRMS or another app you use may also override.
- Do not copy a whole method from core into your override. It breaks on the next update.

## Examples

Good. `hooks.py`:

```python
doc_events = {
	"Sales Invoice": {
		"validate": "my_app.overrides.sales_invoice.validate",
	}
}
```

```python
def validate(doc, method):
	if doc.grand_total > 100000 and not doc.approval_note:
		frappe.throw(_("Approval Note is required for invoices above 100,000"))
```

Good on v16. `hooks.py`:

```python
extend_doctype_class = {
	"Sales Invoice": ["my_app.overrides.sales_invoice.SalesInvoiceMixin"],
}
```

```python
class SalesInvoiceMixin:
	def validate(self):
		super().validate()
		self.check_credit_limit()

	def check_credit_limit(self):
		...
```

Last resort. `hooks.py`:

```python
override_doctype_class = {
	"Sales Invoice": "my_app.overrides.sales_invoice.CustomSalesInvoice",
}
```
