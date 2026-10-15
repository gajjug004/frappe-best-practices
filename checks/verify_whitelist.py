import importlib.util
import pathlib
import sys

from werkzeug.test import Client

import frappe.app

# frappe reads the app name from __module__, so load the fake API under the frappe package
spec = importlib.util.spec_from_file_location("frappe.guide_api", pathlib.Path(__file__).with_name("guide_api.py"))
guide_api = importlib.util.module_from_spec(spec)
sys.modules["frappe.guide_api"] = guide_api
spec.loader.exec_module(guide_api)

site, password = sys.argv[1], sys.argv[2]
headers = {"Host": site, "Accept": "application/json"}
guest = Client(frappe.app.application)
user = Client(frappe.app.application)
user.post("/api/method/login", data={"usr": "Administrator", "pwd": password}, headers=headers)


def call(client, method, path, **kwargs):
	response = getattr(client, method)(f"/api/method/frappe.guide_api.{path}", headers=headers, **kwargs)
	return response.status_code, (response.json or {}).get("message")


def check(label, ok, got=None):
	print(("PASS " if ok else "FAIL ") + label + ("" if ok else f" (got {got})"))


got = call(user, "get", "double?n=5")
check("untyped argument arrives as a string: double(5) returns '55'", got == (200, "55"), got)
got = call(user, "get", "double_enforced?n=5")
check("with require_type_annotated_api_methods, untyped argument is rejected with 417", got[0] == 417, got)
got = call(user, "get", "double_typed?n=5")
check("typed argument is converted: double_typed(5) returns 10", got == (200, 10), got)
got = call(user, "get", "double_typed?n=abc")
check("typed argument rejects bad input with 417", got[0] == 417, got)
got = call(user, "get", "post_only")
check("methods=['POST'] blocks GET with 403", got[0] == 403, got)
got = call(user, "post", "post_only")
check("methods=['POST'] allows POST", got == (200, "ok"), got)
got = call(guest, "get", "logged_in_only")
check("guest cannot call a normal whitelisted method", got[0] == 403, got)
got = call(guest, "get", "guest_ok")
check("allow_guest=True lets anyone call it", got == (200, "Guest"), got)
got = call(user, "get", "not_whitelisted")
check("function without @frappe.whitelist is blocked", got[0] == 403, got)
