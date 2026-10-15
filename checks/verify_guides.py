import sys

import frappe

site = sys.argv[1]
frappe.init(site=site, sites_path=".")
frappe.connect()
frappe.set_user("Administrator")


def check(label, ok):
	print(("PASS " if ok else "FAIL ") + label)


try:
	print("== A: set_value vs save ==")
	todo = frappe.get_doc({"doctype": "ToDo", "description": "guide test"}).insert()
	before_modified = todo.modified
	versions_before = frappe.db.count("Version", {"ref_doctype": "ToDo", "docname": todo.name})
	print("ToDo track_changes:", frappe.get_meta("ToDo").track_changes)

	frappe.db.set_value("ToDo", todo.name, "description", "")
	check("set_value saved empty mandatory field", frappe.db.get_value("ToDo", todo.name, "description") in ("", None))
	check(
		"set_value created no Version",
		frappe.db.count("Version", {"ref_doctype": "ToDo", "docname": todo.name}) == versions_before,
	)
	after_modified = frappe.db.get_value("ToDo", todo.name, "modified")
	check("set_value updated modified", after_modified != before_modified)

	frappe.db.set_value("ToDo", todo.name, "priority", "High", update_modified=False)
	check(
		"update_modified=False kept modified",
		frappe.db.get_value("ToDo", todo.name, "modified") == after_modified,
	)

	todo.reload()
	todo.description = ""
	try:
		todo.save()
		check("save rejects empty mandatory field", False)
	except frappe.MandatoryError:
		check("save rejects empty mandatory field", True)

	todo.reload()
	todo.description = "changed via save"
	todo.save()
	check(
		"save created a Version",
		frappe.db.count("Version", {"ref_doctype": "ToDo", "docname": todo.name}) > versions_before,
	)

	print("== B: which APIs check permissions ==")
	user = frappe.get_doc(
		{"doctype": "User", "email": "guide.tester@example.com", "first_name": "Guide", "send_welcome_email": 0}
	).insert(ignore_permissions=True)
	error_log = frappe.get_doc({"doctype": "Error Log", "method": "guide", "error": "x"}).insert(
		ignore_permissions=True
	)
	frappe.set_user(user.name)
	print("roles:", frappe.get_roles())
	check("db.get_value reads without permission", frappe.db.get_value("Error Log", error_log.name, "method") == "guide")
	check("get_all reads without permission", len(frappe.get_all("Error Log", limit=1)) == 1)
	try:
		frappe.get_list("Error Log", limit=1)
		check("get_list blocks", False)
	except frappe.PermissionError:
		check("get_list blocks", True)
	doc = frappe.get_doc("Error Log", error_log.name)
	check("get_doc loads without permission", doc.method == "guide")
	check("doc.has_permission is False", doc.has_permission("read") is False)
	try:
		doc.check_permission("read")
		check("doc.check_permission raises", False)
	except frappe.PermissionError:
		check("doc.check_permission raises", True)
	try:
		frappe.get_doc({"doctype": "Error Log", "method": "x", "error": "x"}).insert()
		check("insert checks create permission", False)
	except frappe.PermissionError:
		check("insert checks create permission", True)
	frappe.set_user("Administrator")

	print("== C: SQL parameters ==")
	attack = "nobody' or '1'='1"
	unsafe = frappe.db.sql(f"select name from `tabUser` where name = '{attack}'")
	safe = frappe.db.sql("select name from `tabUser` where name = %s", attack)
	safe_named = frappe.db.sql("select name from `tabUser` where name = %(name)s", {"name": attack})
	print("users total:", frappe.db.count("User"), "unsafe rows:", len(unsafe), "safe rows:", len(safe))
	check("f-string query leaks every row", len(unsafe) == frappe.db.count("User"))
	check("parameter query returns nothing", len(safe) == 0 and len(safe_named) == 0)

	print("== D: get_cached_doc ==")
	first = frappe.get_cached_doc("User", user.name)
	first.first_name = "Mutated"
	second = frappe.get_cached_doc("User", user.name)
	print("same object:", first is second, "second.first_name:", second.first_name)
	check("mutating cached doc leaks to next call in same request", second is first and second.first_name == "Mutated")
	frappe.local.cache = {}
	check("next request (fresh local cache) gets Redis copy", frappe.get_cached_doc("User", user.name).first_name == "Guide")
	frappe.db.sql("update `tabUser` set first_name = 'RawSQL' where name = %s", user.name)
	frappe.local.cache = {}
	check("raw SQL update leaves Redis cache stale", frappe.get_cached_doc("User", user.name).first_name == "Guide")
	check("get_doc sees raw SQL update", frappe.get_doc("User", user.name).first_name == "RawSQL")
	frappe.db.set_value("User", user.name, "first_name", "SetValue")
	check("db.set_value clears cache", frappe.get_cached_doc("User", user.name).first_name == "SetValue")
	check("get_cached_value reads same cache", frappe.get_cached_value("User", user.name, "first_name") == "SetValue")

	print("== E: N+1 queries ==")
	for i in range(20):
		frappe.get_doc({"doctype": "ToDo", "description": f"n1 {i}"}).insert()
	names = frappe.get_all("ToDo", filters={"description": ["like", "n1 %"]}, pluck="name")

	count = {"n": 0}
	original_sql = frappe.db.sql

	def counting_sql(*args, **kwargs):
		count["n"] += 1
		return original_sql(*args, **kwargs)

	frappe.db.sql = counting_sql
	for name in names:
		frappe.get_doc("ToDo", name).description
	loop_queries = count["n"]
	count["n"] = 0
	frappe.get_all("ToDo", filters={"name": ["in", names]}, fields=["name", "description"])
	bulk_queries = count["n"]
	count["n"] = 0
	for name in names:
		frappe.db.get_value("ToDo", name, "description")
	get_value_loop = count["n"]
	frappe.db.sql = original_sql
	print("get_doc loop:", loop_queries, "get_value loop:", get_value_loop, "one get_all:", bulk_queries)
	check("get_all uses far fewer queries", bulk_queries < loop_queries / 10)

finally:
	frappe.db.rollback()
	frappe.destroy()
