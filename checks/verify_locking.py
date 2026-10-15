import sys
import threading
import time

import frappe

site = sys.argv[1]
errors = []


def connect():
	frappe.init(site=site, sites_path=".")
	frappe.connect()
	frappe.set_user("Administrator")


def increment(name, mode, barrier):
	connect()
	try:
		barrier.wait()
		if mode in ("get_doc", "get_doc_plain"):
			doc = frappe.get_doc("ToDo", name, for_update=mode == "get_doc")
			time.sleep(1)
			doc.description = str(int(doc.description) + 1)
			doc.save()
		else:
			value = int(frappe.db.get_value("ToDo", name, "description", for_update=mode == "for_update"))
			time.sleep(1)
			frappe.db.set_value("ToDo", name, "description", str(value + 1))
		frappe.db.commit()
	except Exception as error:
		errors.append(type(error).__name__)
	finally:
		frappe.destroy()


def run_two(name, mode):
	frappe.db.set_value("ToDo", name, "description", "0")
	frappe.db.commit()
	barrier = threading.Barrier(2)
	threads = [threading.Thread(target=increment, args=(name, mode, barrier)) for _ in range(2)]
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join()
	return int(frappe.db.get_value("ToDo", name, "description"))


def check(label, ok, got=None):
	print(("PASS " if ok else "FAIL ") + label + ("" if ok else f" (got {got})"))


connect()
name = frappe.get_doc({"doctype": "ToDo", "description": "0"}).insert().name
frappe.db.commit()
try:
	got = run_two(name, "plain")
	check("two plain read-then-write updates lose one: 0 + 1 + 1 = 1", got == 1, got)
	got = run_two(name, "for_update")
	check("db.get_value(for_update=True): both updates count, 0 + 1 + 1 = 2", got == 2, got)
	errors.clear()
	got = run_two(name, "get_doc_plain")
	check(
		"plain get_doc + save: second save fails with TimestampMismatchError, 0 + 1 = 1",
		got == 1 and errors == ["TimestampMismatchError"],
		(got, errors),
	)
	errors.clear()
	got = run_two(name, "get_doc")
	check("get_doc(for_update=True) + save: both updates count, 0 + 1 + 1 = 2", got == 2, got)
finally:
	frappe.delete_doc("ToDo", name, force=1)
	frappe.db.commit()
	frappe.destroy()
