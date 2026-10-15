# Avoid one query per row (N+1 queries)

## The rule

- Do not call `frappe.get_doc` or `frappe.db.get_value` inside a loop over many records.
- Fetch all the rows you need in one `frappe.get_all` call.

## Why

Tested on frappe `develop` with 20 ToDo records, counting calls to `frappe.db.sql`:

| Code | Queries |
|---|---|
| `frappe.get_doc` in a loop | 20 |
| `frappe.db.get_value` in a loop | 20 |
| One `frappe.get_all` with `fields` | 1 |

- Queries grow with the number of rows. 10,000 rows means 10,000 queries.
- `get_doc` also loads every child table. One `get_doc("User", ...)`, which has 6 child tables, ran 9 queries.

## Do

- Use `frappe.get_all` or `frappe.get_list` with `fields=[...]` and `filters={"name": ["in", names]}`.
- Build a dict once, then look up in the loop.
- Use `pluck="name"` when you only need names.
- Use `get_doc` in a loop only when you need to call methods or save each doc, and the list is small.

## Do not

- Do not use `fields=["*"]` when you need two columns.
- Do not load full docs just to read one field.

## Examples

Bad. One query per invoice:

```python
for name in invoice_names:
	customer = frappe.db.get_value("Sales Invoice", name, "customer")
	...
```

Good. One query in total:

```python
customers = dict(
	frappe.get_all(
		"Sales Invoice",
		filters={"name": ["in", invoice_names]},
		fields=["name", "customer"],
		as_list=True,
	)
)
for name in invoice_names:
	customer = customers[name]
	...
```
