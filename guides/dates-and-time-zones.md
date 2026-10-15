# Dates and time zones: use `frappe.utils`

## The rule

- Use `now_datetime()`, `nowdate()`, `today()` and `getdate()` from `frappe.utils`.
- Do not use `datetime.now()` or `date.today()`.
- Convert with `getdate()` or `get_datetime()` before you compare.

## Why

Frappe uses the time zone in **System Settings**, not the server clock. Source: `frappe/utils/data.py`, `now_datetime`.

Tested on frappe `develop` with System Settings set to `Pacific/Kiritimati`:

| Code | Result |
|---|---|
| `datetime.datetime.now()` | Server time |
| `frappe.utils.now_datetime()` | Site time, 8.5 hours ahead of the server |

Your code may work on your laptop and break on a server in another time zone. Cloud servers usually run in UTC.

## Date fields can be a string or a date

Tested on a ToDo `date` field:

| State | Type |
|---|---|
| Loaded from the database | `datetime.date` |
| Set from code or a form, `doc.date = "2026-10-21"` | `str` |
| `doc.date > datetime.date(2026, 10, 1)` on the string | `TypeError` |
| `getdate(doc.date) > getdate("2026-10-01")` | Works |

## Do

- Use `getdate()` and `get_datetime()` on both sides of a comparison.
- Use `add_days`, `add_months`, `date_diff` and `get_first_day` from `frappe.utils`.
- Store dates in Date and Datetime fields. Never in Data fields.
- Use `formatdate()` to show a date in the user's format.

## Do not

- Do not use `datetime.now()` for anything saved or compared.
- Do not compare a date field to a string with `<` or `>`.
- Do not hard-code a date format like `"%d-%m-%Y"`. Users pick their own format.

## Examples

Bad:

```python
if doc.delivery_date < datetime.date.today():
	frappe.throw(_("Delivery Date cannot be in the past"))
```

Good:

```python
from frappe.utils import getdate, today

if getdate(doc.delivery_date) < getdate(today()):
	frappe.throw(_("Delivery Date cannot be in the past"))
```
