# Translatable text: use `_()` with placeholders

## The rule

- Wrap every user-facing string in `_()`.
- Put values in with `{0}` placeholders and `.format()` **after** `_()`.
- Never use f-strings or `.format()` inside `_()`.

## Why

`_()` looks up the exact text in the translation table. If the text has a value baked in, there is no match.

Tested on frappe `develop` with a German translation `"Hello {0}"` to `"Hallo {0}"`:

| Code | Result |
|---|---|
| `_("Hello {0}").format(name)` | `Hallo Ann` |
| `_(f"Hello {name}")` | `Hello Ann`, not translated |
| `_("Hello {0}".format(name))` | `Hello Ann`, not translated |

Translation tools also scan code for `_("...")`. They cannot pick up a string built at runtime, so it never reaches translators.

## Do

- Use numbered placeholders: `{0}`, `{1}`. Translators may need to change the order.
- Keep whole sentences in one `_()`. Word order differs between languages.
- Use `context=` when the same word means different things: `_("Open", context="Status")`.
- In JS, use `__("Hello {0}", [name])`.

## Do not

- Do not join translated pieces: `_("Total") + ": " + _("Paid")`.
- Do not translate values from the database, such as customer names.
- Do not put HTML inside `_()` when you can avoid it.
- Do not pass a variable to `_()`, as in `_(message)`. The tools cannot find it.

## Examples

Bad:

```python
frappe.throw(_(f"Row {idx}: Item {item_code} is disabled"))
```

Good:

```python
frappe.throw(_("Row {0}: Item {1} is disabled").format(idx, frappe.bold(item_code)))
```

Good. JS:

```js
frappe.msgprint(__("Row {0}: Item {1} is disabled", [idx, item_code]));
```
