# Reading cached documents: `frappe.get_cached_doc`

## The rule

- Use `get_cached_doc` and `get_cached_value` for records that rarely change, such as settings, Company, Currency or Item Group.
- Treat a cached doc as read-only. Never change it.
- Use `frappe.get_doc` when you plan to change and save the record.

## How the cache works

- First call loads the doc and stores it in Redis for 1 hour.
- Inside one request, Frappe also keeps it in `frappe.local.cache` and returns the **same Python object** every time.
- Source: `frappe/model/document.py`, `get_cached_doc`, and `frappe/utils/redis_wrapper.py`, `get_value`.

## What we tested

On frappe `develop`:

| Action | Result |
|---|---|
| Change a field on a cached doc, then call `get_cached_doc` again in the same request | Got the changed object back. The change leaked. |
| Same, in a new request | Got the clean copy from Redis |
| Update the row with raw SQL, then call `get_cached_doc` | Got the old value. Cache was stale. |
| Update with `frappe.db.set_value`, then call `get_cached_doc` | Got the new value. `set_value` clears the cache. |
| `frappe.get_doc` after the raw SQL update | Got the new value |
| `doc.save()` on the record | Cache entry removed |

## Do

- Use `frappe.get_cached_value(doctype, name, field)` for a single field.
- Use `frappe.db.set_value` or `doc.save()` to write. Both clear the cache.
- If you must use raw SQL to update, call `frappe.clear_document_cache(doctype, name)` after.

## Do not

- Do not change fields on a cached doc. Other code in the same request will see your change.
- Do not call `.save()` on a cached doc.
- Do not cache records that change often, such as invoices or stock entries. The cache gets cleared on every save, so you gain nothing.

## Examples

Good:

```python
currency = frappe.get_cached_value("Company", company, "default_currency")
```

Bad. Changes the shared object for the rest of the request:

```python
settings = frappe.get_cached_doc("Selling Settings")
settings.allow_multiple_items = 1
```

Good. Load a fresh doc when you need to change it:

```python
settings = frappe.get_doc("Selling Settings")
settings.allow_multiple_items = 1
settings.save()
```
