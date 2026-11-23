import json
import multiprocessing
import os
import shutil
import sys

import frappe
from frappe.config import clear_site_config_cache, get_site_config
from frappe.utils.password import decrypt, encrypt, get_encryption_key

# Copies the real site's config without its key into a throwaway site folder.
# The real site and its database are never touched.
source_site = sys.argv[1]
site = "_guide_encryption_key_check"


def check(label, ok):
	print(("PASS " if ok else "FAIL ") + label)


def key_on_disk():
	with open(os.path.join(site, "site_config.json")) as f:
		return json.load(f).get("encryption_key")


def load_conf(cached):
	return get_site_config(sites_path=".", site_path=site, cached=cached)


with open(os.path.join(source_site, "site_config.json")) as f:
	conf = json.load(f)
conf.pop("encryption_key", None)
os.makedirs(site)
with open(os.path.join(site, "site_config.json"), "w") as f:
	json.dump(conf, f)

try:
	frappe.init(site=site, sites_path=".")
	clear_site_config_cache()

	print("== site with no encryption_key ==")
	check("new site config has no key", key_on_disk() is None)
	check("web request caches the config without a key", "encryption_key" not in load_conf(cached=True))

	# A forked process stands in for a running web worker with its own in-memory config cache.
	ctx = multiprocessing.get_context("fork")
	ready, go, result = ctx.Event(), ctx.Event(), ctx.Queue()

	def web_worker():
		ready.set()
		go.wait(10)
		frappe.local.conf = load_conf(cached=True)
		result.put(("encryption_key" in frappe.local.conf, get_encryption_key()))

	worker = ctx.Process(target=web_worker)
	worker.start()
	ready.wait(10)

	frappe.local.conf = load_conf(cached=False)
	key_a = get_encryption_key()
	token = encrypt("api-secret")
	check("first process generates a key and writes it", key_on_disk() == key_a)

	go.set()
	worker_saw_key, key_b = result.get(timeout=10)
	worker.join(10)
	check("web worker within 60s still sees no key", not worker_saw_key)
	check("web worker generates a second, different key", key_b != key_a)
	check("second key overwrites the first on disk", key_on_disk() == key_b)

	frappe.local.conf = load_conf(cached=False)
	try:
		decrypt(token)
		check("value encrypted with the first key can no longer be read", False)
	except frappe.ValidationError:
		check("value encrypted with the first key can no longer be read", True)

	print("== key written before first use ==")
	frappe.local.conf = load_conf(cached=False)
	token = encrypt("api-secret")
	clear_site_config_cache()
	frappe.local.conf = load_conf(cached=True)
	check("web request after cache refresh reuses the key on disk", get_encryption_key() == key_on_disk())
	check("value round-trips", decrypt(token) == "api-secret")
finally:
	frappe.destroy()
	clear_site_config_cache()
	shutil.rmtree(site, ignore_errors=True)
