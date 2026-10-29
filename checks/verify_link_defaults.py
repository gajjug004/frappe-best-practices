import sys

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

site = sys.argv[1]
frappe.init(site=site, sites_path=".")
frappe.connect()
frappe.set_user("Administrator")


def check(label, ok):
	print(("PASS " if ok else "FAIL ") + label)


fieldnames = ("language", "content_language")
try:
	defaults = frappe.defaults.get_defaults()
	print("defaults['language']:", defaults.get("language"))
	for fieldname in fieldnames:
		create_custom_field(
			"ToDo", {"fieldname": fieldname, "label": fieldname, "fieldtype": "Link", "options": "Language"}
		)
	frappe.clear_cache(doctype="ToDo")

	todo = frappe.new_doc("ToDo")
	check("new_doc: 'language' filled from the system default", todo.language == defaults.get("language"))
	check("new_doc: 'content_language' left empty", not todo.content_language)

	todo = frappe.get_doc({"doctype": "ToDo", "description": "link default check"})
	check("get_doc: 'language' still empty before insert", not todo.language)
	todo.insert()
	check("insert: 'language' filled from the system default", todo.language == defaults.get("language"))
	check("insert: 'content_language' left empty", not todo.content_language)
finally:
	frappe.db.rollback()
	for fieldname in fieldnames:
		name = frappe.db.get_value("Custom Field", {"dt": "ToDo", "fieldname": fieldname})
		if name:
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)
		if frappe.db.has_column("ToDo", fieldname):
			frappe.db.sql_ddl(f"alter table `tabToDo` drop column `{fieldname}`")
	frappe.db.commit()
	frappe.clear_cache(doctype="ToDo")
	frappe.destroy()
