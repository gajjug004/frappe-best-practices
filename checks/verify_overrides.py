import sys

import frappe

frappe.init(site=sys.argv[1], sites_path=".")
frappe.connect()
frappe.set_user("Administrator")

import guide_fake_apps
from guide_fake_apps import calls

sys.modules["frappe.guide_fake_apps"] = guide_fake_apps


fake_hooks = {}
original_get_hooks = frappe.get_hooks


def patched_get_hooks(hook=None, *args, **kwargs):
	if hook in fake_hooks:
		return fake_hooks[hook]
	return original_get_hooks(hook, *args, **kwargs)


def run(hooks):
	fake_hooks.clear()
	fake_hooks.update(hooks)
	frappe.controllers.pop(frappe.local.site, None)
	frappe.local.doc_events_hooks = None
	calls.clear()
	frappe.get_doc({"doctype": "ToDo", "description": "override test"}).insert()
	return list(calls)


frappe.get_hooks = patched_get_hooks
try:
	both_override = run(
		{"override_doctype_class": {"ToDo": ["frappe.guide_fake_apps.AppAToDo", "frappe.guide_fake_apps.AppBToDo"]}}
	)
	print("two apps override_doctype_class:", both_override)

	both_extend = run(
		{"extend_doctype_class": {"ToDo": ["frappe.guide_fake_apps.AppAMixin", "frappe.guide_fake_apps.AppBMixin"]}}
	)
	print("two apps extend_doctype_class:", both_extend)

	both_events = run(
		{
			"doc_events": {
				"ToDo": {"validate": ["frappe.guide_fake_apps.app_a_validate", "frappe.guide_fake_apps.app_b_validate"]}
			}
		}
	)
	print("two apps doc_events:", both_events)

	print("PASS override: last app wins" if both_override == ["app_b override"] else "FAIL override")
	print("PASS extend: both run" if set(both_extend) == {"app_a extend", "app_b extend"} else "FAIL extend")
	print("PASS doc_events: both run" if both_events == ["app_a doc_event", "app_b doc_event"] else "FAIL doc_events")
finally:
	frappe.get_hooks = original_get_hooks
	frappe.controllers.pop(frappe.local.site, None)
	frappe.db.rollback()
	frappe.destroy()
