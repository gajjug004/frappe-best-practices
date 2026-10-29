# Link field names: a name that matches a default gets filled for you

## The rule

- Before you name a Link field, check `frappe.defaults.get_defaults()`. If a key there has the same name, a new record gets that value without asking.
- If you want the field empty until someone picks a value, give it a name that is not a defaults key.

## Why

When a new record is made, Frappe fills each empty Link field from the defaults whose key equals the fieldname. Source: `frappe/model/create_new.py`, `get_user_default_value`, the line `user_default = defaults.get(df.fieldname)`.

- `frappe.new_doc()` fills it at once.
- `frappe.get_doc({...}).insert()` fills it on insert, through `Document._set_defaults` in `frappe/model/document.py`.
- Data import skips it (`frappe.flags.in_import`).
- The defaults hold system settings and user defaults. On a fresh site `language` is the site language, and `time_zone`, `country`, `currency` and, with ERPNext, `company` are there too.

This is on purpose for `company` in ERPNext. It is a trap when "empty" has a meaning, like "no language set, follow the reader's".

## What we tested

On frappe `develop`, with two Link to Language custom fields on ToDo, `language` and `content_language`, and `defaults["language"] == "en"`:

| Check | Result |
|---|---|
| `frappe.new_doc("ToDo").language` | `en` |
| `frappe.new_doc("ToDo").content_language` | empty |
| `frappe.get_doc({...}).language` before insert | empty |
| `frappe.get_doc({...}).insert().language` | `en` |
| `frappe.get_doc({...}).insert().content_language` | empty |

The test is `checks/verify_link_defaults.py`.

## Do

- Run `frappe.defaults.get_defaults()` on a site and look for your fieldname before you add a Link field.
- Pick a more specific name when empty must stay empty: `content_language`, `billing_country`.
- Keep the plain name when the default is what you want, like `company` on an ERPNext transaction.

## Do not

- Do not name a Link field `language`, `country`, `currency` or `time_zone` and expect a new record to start empty.
- Do not clear the value in `before_insert` to undo it. You cannot tell the filled default from a value the user picked.

## Examples

Bad: every new space silently gets the site language, so "follow the reader's language" never happens.

```json
{"fieldname": "language", "fieldtype": "Link", "options": "Language"}
```

Good: the field starts empty. The label can still say Language.

```json
{"fieldname": "content_language", "fieldtype": "Link", "label": "Language", "options": "Language"}
```
