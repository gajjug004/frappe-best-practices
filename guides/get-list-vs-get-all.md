# Reading lists of records: `get_list` vs `get_all`

## The rule

- Use `frappe.get_list` when the code runs for a user.
- Use `frappe.get_all` only in trusted system code.

## The difference

`get_all` is `get_list` with two settings changed:

```python
def get_all(doctype, *args, **kwargs):
	kwargs["ignore_permissions"] = True
	if "limit_page_length" not in kwargs:
		kwargs["limit_page_length"] = 0
	return get_list(doctype, *args, **kwargs)
```

Source: `frappe/__init__.py`, `get_all`.

### 1. Permissions

| Check | `get_list` | `get_all` |
|---|---|---|
| Role permission (read or select) | Yes | No |
| User Permissions (Link restrictions) | Yes | No |
| `permission_query_conditions` hooks and Server Scripts | Yes | No |
| Shared documents | Yes | Not needed, it returns everything |
| Field permissions (perm level) | Yes | No |

### 2. Limit

- `get_all` returns all rows unless you pass a limit.
- `get_list` also has no default limit in Python code, even though its docstring says 20.
- The default of 20 applies to the REST API (`/api/resource`) and to virtual doctypes.
- Always pass `limit` when you only need a few rows.

Everything else is the same: `fields`, `filters`, `or_filters`, `order_by`, `group_by`, `pluck`, `as_list`.

## Use `get_list` for

- `@frappe.whitelist()` methods.
- Portal and web pages.
- Reports and dashboards.
- Any code where the user picks the filters.

## Use `get_all` for

- Background jobs and scheduled tasks.
- Patches.
- Controller logic that must see every row, such as a uniqueness check.
- Internal lookups whose result never goes back to the user as is.

## Do not

- Do not return `get_all` results from a whitelisted method. Users will see records they are not allowed to see.
- Do not use `get_all` just to "make the permission error go away". Fix the permission instead.
- Do not use `get_all` without a limit on large tables.
- Do not pass `limit_page_length` or `limit_start` in new code. They are deprecated and go away in v17. Use `limit` and `offset`.

## When you need something in between

Skip only User Permissions and keep the role check:

```python
frappe.get_list("Customer", filters={...}, ignore_user_permissions=True)
```

## Examples

Good. A user-facing API respects permissions:

```python
@frappe.whitelist()
def my_open_tasks():
	return frappe.get_list(
		"ToDo",
		filters={"status": "Open"},
		fields=["name", "description"],
		limit=50,
	)
```

Bad. Any logged-in user can read every customer:

```python
@frappe.whitelist()
def customers():
	return frappe.get_all("Customer", fields=["*"])
```

Good. A scheduled job that must see every record:

```python
def close_stale_todos():
	for name in frappe.get_all("ToDo", filters={"status": "Open", "date": ["<", today()]}, pluck="name"):
		frappe.db.set_value("ToDo", name, "status", "Closed")
```
