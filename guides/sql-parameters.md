# Raw SQL: always pass values as parameters

## The rule

- Never put a value into a SQL string with f-strings, `%` or `.format()`.
- Pass values as the second argument to `frappe.db.sql`.
- Prefer `frappe.qb` or `frappe.get_all` over raw SQL.

## Why

Tested on frappe `develop` with `name = "nobody' or '1'='1"` on a site with 40 users:

| Query | Rows returned |
|---|---|
| `frappe.db.sql(f"... where name = '{name}'")` | 40, every user |
| `frappe.db.sql("... where name = %s", name)` | 0 |
| `frappe.db.sql("... where name = %(name)s", {"name": name})` | 0 |

The f-string query let the input rewrite the query. The parameter version treated it as plain text.

## Do

- Use `%s` with a value or tuple, or `%(key)s` with a dict.
- Use `frappe.qb` when you build queries in code.
- Check table and column names against a fixed list. Parameters cannot hold names, only values.

## Do not

- Do not quote `%s` yourself. Write `name = %s`, not `name = '%s'`.
- Do not build `IN (...)` lists by joining strings. Pass a tuple: `name in %s`, with `(tuple(names),)`.
- Do not pass user input as a field name or an `order_by`.

## Examples

Bad:

```python
frappe.db.sql(f"select name from `tabCustomer` where territory = '{territory}'")
```

Good:

```python
frappe.db.sql("select name from `tabCustomer` where territory = %s", territory)
```

Good. Several values with a dict:

```python
frappe.db.sql(
	"""select name from `tabSales Invoice`
	where customer = %(customer)s and posting_date >= %(from_date)s""",
	{"customer": customer, "from_date": from_date},
	as_dict=True,
)
```

Best. No SQL string at all:

```python
Invoice = frappe.qb.DocType("Sales Invoice")
frappe.qb.from_(Invoice).select(Invoice.name).where(Invoice.customer == customer).run()
```
