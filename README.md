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
- [Do not call `frappe.db.commit()` in a request](guides/db-commit-in-requests.md)
- [Background jobs: use `enqueue_after_commit=True`](guides/enqueue-after-commit.md)
- [Showing errors: `frappe.throw` vs `raise`](guides/throw-vs-raise.md)
- [Changing another app's DocType: hooks vs `override_doctype_class`](guides/hooks-vs-override-doctype-class.md)

## Checks

The `checks/` folder has the tests behind these guides. Run them on a local dev site. Each one cleans up after itself.

| Script | Covers | Needs |
|---|---|---|
| `verify_guides.py` | Permissions, set_value, SQL, cache, N+1 | Site |
| `verify_enqueue.py` | enqueue_after_commit | Site and a running worker |
| `verify_overrides.py` | Hooks vs override | Site |
| `verify_http.sh` | Commit in requests, throw vs raise | Running bench, server scripts on |

```bash
cd frappe-bench/sites
../env/bin/python /path/to/checks/verify_guides.py your-site.localhost
../env/bin/python /path/to/checks/verify_enqueue.py your-site.localhost
../env/bin/python /path/to/checks/verify_overrides.py your-site.localhost
/path/to/checks/verify_http.sh your-site.localhost admin-password
```

## How to add a guide

- One topic per file in `guides/`.
- Start with the rule. Then why. Then examples.
- Use short points. One idea per point.
- Back every claim with a source file and line, or a test you ran.
- Add the guide to the list above.
