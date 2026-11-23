# Site encryption key: set `encryption_key` before the site serves traffic

## The rule

- Give every site an `encryption_key` in `site_config.json` before it serves requests or runs workers.
- Never change or delete the key on a site that already has encrypted values.

## Why

- Password fields (API secrets, email passwords, integration tokens) are encrypted with this key.
- `bench new-site` does not write a key. `make_site_config` in `frappe/installer.py` has no `encryption_key`.
- The key is made on first use. `get_encryption_key()` in `frappe/utils/password.py` generates a new key and writes it to disk when `frappe.local.conf` has none.
- Web requests read `site_config.json` through an in-memory cache with a 60 second TTL (`frappe/config.py`, `_cached_get_site_config`).
- `update_site_config` clears that cache only in the process that writes. Other processes keep their old copy.
- So a web worker that loaded the config before the key existed makes its own key and overwrites the first one.
- Every value encrypted with the first key is now lost. Reading it fails with "Encryption key is invalid!".

## What we tested

On frappe `version-16` (`49789a1`). Script: `checks/verify_encryption_key.py`.

| Action | Result |
|---|---|
| Read a new site config | No `encryption_key` |
| Web worker loads the config | Cached copy has no key |
| Another process encrypts a value | Generates key A and writes it to disk |
| Same web worker handles a request within 60 seconds | Still sees no key. Generates key B. |
| Check the file | Key B overwrote key A |
| Decrypt the value encrypted with key A | Fails with `ValidationError` |
| Key on disk before first use, cache refreshed | Web worker reuses the key on disk. Values round-trip. |
| `bench --site x set-config encryption_key <Fernet key>` | Writes a valid key |

We first hit this on a dev site. A script set an Administrator API secret while `bench start` was running. The secret could not be read right after.

## Do

- Set the key right after `bench new-site`, before you start the bench.
- After you set it on a running bench, restart, or wait 60 seconds before you save any Password field.
- Copy `site_config.json` with the key when you move or restore a site.
- If values were already lost, set them again. Regenerate API secrets, re-enter email and integration passwords.

## Do not

- Do not leave a site without a key and rely on the first use to make one.
- Do not delete or regenerate `encryption_key` on a site with encrypted data.
- Do not set Password fields from a script while a bench is running on a site with no key.

## Examples

Good. Set the key once, before first use:

```bash
bench --site mysite.localhost set-config encryption_key \
  "$(./env/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
bench restart
```

Bad. A site with no key, a running bench and a script that saves a secret:

```python
user = frappe.get_doc("User", "Administrator")
user.api_secret = frappe.generate_hash(length=15)
user.save()
```
