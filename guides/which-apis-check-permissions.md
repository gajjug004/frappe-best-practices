# Which APIs check permissions

## The rule

- Most read APIs do **not** check permissions.
- In a `@frappe.whitelist()` method, check permission yourself before you return data.

## The list

Tested on frappe `develop` as a user with no access to Error Log:

| API | Checks permission? | What happened |
|---|---|---|
| `frappe.get_list` | Yes | Raised `PermissionError` |
| `frappe.get_all` | No | Returned the record |
| `frappe.db.get_value` | No | Returned the field |
| `frappe.db.get_all`, `frappe.db.sql` | No | Raw database access |
| `frappe.get_doc` | No | Loaded the record |
| `frappe.get_cached_doc` | No | Same as `get_doc` |
| `doc.has_permission("read")` | Yes | Returned `False` |
| `doc.check_permission("read")` | Yes | Raised `PermissionError` |
| `doc.insert()` | Yes, `create` | Raised `PermissionError` |
| `doc.save()` | Yes, `write` | Source: `model/document.py`, `_save` |
| `doc.submit()`, `doc.cancel()` | Yes | Source: `model/document.py` |
| `frappe.delete_doc` | Yes, `delete` | Source: `model/delete_doc.py` |

## Do

- Call `doc.check_permission("read")` right after `frappe.get_doc` in a whitelisted method.
- Use `frappe.get_list` for lists that go back to the user.
- Use `frappe.has_permission(doctype, "read", throw=True)` before `frappe.db.get_value` on user input.
- Pass `ignore_permissions=True` to `insert()` or `save()` only in trusted system code.

## Do not

- Do not trust that "the user can only reach this through the UI". Every whitelisted method is a public API.
- Do not set `frappe.flags.ignore_permissions = True` globally. It stays on for the rest of the request.
- Do not use `ignore_permissions=True` to hide a permission error you do not understand.

## Examples

Bad. Any logged-in user can read any document of any doctype:

```python
@frappe.whitelist()
def get_record(doctype, name):
	return frappe.get_doc(doctype, name).as_dict()
```

Good:

```python
@frappe.whitelist()
def get_record(doctype, name):
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return doc.as_dict()
```

Good. Check before a raw value read:

```python
@frappe.whitelist()
def get_customer_email(name):
	frappe.has_permission("Customer", "read", name, throw=True)
	return frappe.db.get_value("Customer", name, "email_id")
```
