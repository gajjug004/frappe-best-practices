# Frappe Development Best Practices

Short, plain rules for building Frappe apps. What to do, what not to do, and when.

Each guide is checked against the Frappe source code. Line references point to the `develop` branch unless a guide says otherwise.

## Guides

- [Reading lists of records: `get_list` vs `get_all`](guides/get-list-vs-get-all.md)
- [Which APIs check permissions](guides/which-apis-check-permissions.md)
- [Updating a record: `frappe.db.set_value` vs `doc.save()`](guides/set-value-vs-save.md)
- [Raw SQL: always pass values as parameters](guides/sql-parameters.md)
- [Reading cached documents: `frappe.get_cached_doc`](guides/get-cached-doc.md)
- [Avoid one query per row (N+1 queries)](guides/avoid-n-plus-1-queries.md)

## Checks

`checks/verify_guides.py` runs the tests behind these guides on a local site. It rolls back every change.

```bash
cd frappe-bench/sites
../env/bin/python /path/to/checks/verify_guides.py your-site.localhost
```

## How to add a guide

- One topic per file in `guides/`.
- Start with the rule. Then why. Then examples.
- Use short points. One idea per point.
- Back every claim with a source file and line, or a test you ran.
- Add the guide to the list above.
