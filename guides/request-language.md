# Request language and text direction: use `frappe.local.lang` and `is_rtl()`

## The rule

- Read the current language from `frappe.local.lang`. In Jinja it is `frappe.lang`.
- Decide right to left with `is_rtl()` from `frappe.utils.jinja_globals`. In Jinja it is a global.
- Do not read `User.language` to find the language of a request.

## Why

Frappe works out the language once per request and stores it in `frappe.local.lang`. Every `_()` call uses it. Source: `frappe/translate.py`, `get_language` and `get_user_lang`.

The order:

1. The `_lang` URL parameter.
2. For a signed-in user: `User.language`, then System Settings.
3. For a guest: the `preferred_language` cookie, then `Accept-Language`, then System Settings.

`User.language` only covers part of this:

- It is empty for Administrator and for any user whose language was cleared. Frappe fills it from the system default only when a user is created.
- It knows nothing about a guest's browser language or cookie.
- `get_all_translations(None)` returns `{}`. No error, just no translations.

`is_rtl()` reads `frappe.local.lang` and also matches a regional code by its parent, so `ar-SA` counts as Arabic.

## What we tested

On frappe `develop`, `/login` renders `<html lang dir>` from the request language:

| Request | `<html>` |
|---|---|
| `Accept-Language: ar` | `lang="ar" dir="rtl"` |
| `Accept-Language: ar-SA` | `lang="ar" dir="rtl"` |
| `Accept-Language: en` | `lang="en" dir="ltr"` |
| `?_lang=ar` | `lang="ar" dir="rtl"` |
| Cookie `preferred_language=fa` and `Accept-Language: ar` | `lang="fa" dir="rtl"` |

In code:

| Check | Result |
|---|---|
| A new user's `language` | System language at the time of creation |
| `get_all_translations(None)` | `{}` |
| `is_rtl()` with `ar`, `ar-SA`, `fa`, `he`, `ur` | `True` |
| `is_rtl()` with `en`, `fr` | `False` |

## Do

- Put `lang` and `dir` on `<html>` in every page you render. Use the same language your `_()` strings use.
- Send `frappe.local.lang` to a Vue or React front end in its boot data, and load translations for that same language.
- Use logical CSS (`margin-inline-start`, Tailwind `ms-`, `ps-`, `start-`) so one stylesheet works both ways.

## Do not

- Do not use `frappe.db.get_value("User", frappe.session.user, "language")` for the current language.
- Do not keep your own list of right-to-left languages. Frappe already ships one, and it handles regional codes.
- Do not hard-code `<html lang="en">`.

## Examples

Bad:

```python
@frappe.whitelist()
def get_translations():
	language = frappe.db.get_value("User", frappe.session.user, "language")
	return get_all_translations(language)  # {} for Administrator
```

Good:

```python
@frappe.whitelist()
def get_translations():
	return get_all_translations(frappe.local.lang)
```

Good. Jinja:

```html
<html lang="{{ frappe.lang }}" dir="{{ 'rtl' if is_rtl() else 'ltr' }}">
```
