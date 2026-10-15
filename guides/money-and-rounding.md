# Money and rounding: use `flt` with precision

## The rule

- Use `flt(value, precision)` for every amount.
- Get the precision from the field: `doc.precision("grand_total")`.
- Do not use `float()` or Python's `round()` for money.

## Why

Tested on frappe `develop`:

| Code | Result |
|---|---|
| `0.1 + 0.2 == 0.3` | `False` |
| `flt(0.1 + 0.2, 2) == 0.3` | `True` |
| `round(2.675, 2)` | `2.67` |
| `flt(2.675, 2)` with Commercial Rounding | `2.68` |
| `flt(2.5, 0)` with Banker's Rounding | `2` |
| `flt(2.5, 0)` with Commercial Rounding | `3` |
| `flt("10,500.50")` | `10500.5`, commas removed |
| `flt("abc")` | `0.0`, **no error** |

- Floats cannot store most decimals exactly. Small errors add up across rows.
- Python's `round()` gives a different answer than a calculator in some cases.
- `flt` uses the **Rounding Method** in System Settings. Source: `frappe/utils/data.py`, `rounded`.
- `doc.precision(field)` returns the precision set on the field. If none is set, it falls back to the currency precision for Currency fields, and to the float precision (default 3) for Float and Percent fields. It returns `None` for other field types. Source: `frappe/model/meta.py`, `get_field_precision`.

## Do

- Round each row amount, then sum. Round the total again.
- Use `flt(x, precision)` before you compare two amounts.
- Use `doc.precision("fieldname")` instead of a hard-coded `2`.
- Validate user input yourself. `flt` turns bad input into `0` without warning.

## Do not

- Do not compare amounts with `==` without rounding both sides.
- Do not hard-code the precision. Some currencies use 0 or 3 decimals.
- Do not use `float()` on user input. It raises on commas and on empty strings.

## Examples

Bad:

```python
total = sum(row.qty * row.rate for row in doc.items)
if total != doc.grand_total:
	frappe.throw(_("Total mismatch"))
```

Good:

```python
precision = doc.precision("grand_total")
total = flt(sum(flt(row.qty * row.rate, precision) for row in doc.items), precision)
if total != flt(doc.grand_total, precision):
	frappe.throw(_("Total mismatch"))
```
