import datetime
import sys

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate

frappe.init(site=sys.argv[1], sites_path=".")
frappe.connect()
frappe.set_user("Administrator")


def check(label, ok):
	print(("PASS " if ok else "FAIL ") + label)


try:
	print("== translations ==")
	frappe.get_doc(
		{"doctype": "Translation", "language": "de", "source_text": "Hello {0}", "translated_text": "Hallo {0}"}
	).insert()
	frappe.translate.clear_cache()
	frappe.local.lang = "de"
	name = "Ann"
	check("_() with placeholder translates", _("Hello {0}").format(name) == "Hallo Ann")
	check("_() with f-string does not translate", _(f"Hello {name}") == "Hello Ann")
	check("format inside _() does not translate", _("Hello {0}".format(name)) == "Hello Ann")
	frappe.local.lang = "en"

	print("== dates and time zones ==")
	frappe.db.set_single_value("System Settings", "time_zone", "Pacific/Kiritimati")
	frappe.clear_document_cache("System Settings")
	server_now = datetime.datetime.now()
	site_now = now_datetime()
	gap_hours = round((site_now - server_now).total_seconds() / 3600, 1)
	print("server clock:", server_now, "site clock:", site_now, "gap hours:", gap_hours)
	check("now_datetime follows System Settings time zone, not the server", gap_hours != 0)
	check("nowdate matches now_datetime", nowdate() == str(site_now.date()))

	todo = frappe.get_doc({"doctype": "ToDo", "description": "date test", "date": "2026-10-20"}).insert()
	todo.reload()
	check("date field loaded from DB is a date object", isinstance(todo.date, datetime.date))
	todo.date = "2026-10-21"
	try:
		todo.date > datetime.date(2026, 10, 1)
		check("comparing str field to date raises TypeError", False)
	except TypeError:
		check("comparing str field to date raises TypeError", True)
	check("getdate makes both safe to compare", getdate(todo.date) > getdate("2026-10-01"))

	print("== money and rounding ==")
	print("rounding_method:", frappe.get_system_settings("rounding_method"))
	check("float sum is not exact", 0.1 + 0.2 != 0.3)
	check("flt with precision fixes the sum", flt(0.1 + 0.2, 2) == 0.3)
	check("python round(2.675, 2) gives 2.67", round(2.675, 2) == 2.67)
	check(
		"flt(2.675, 2) gives 2.68 with Commercial Rounding",
		flt(2.675, 2, rounding_method="Commercial Rounding") == 2.68,
	)
	check("flt('abc') silently returns 0", flt("abc") == 0.0)
	check("flt strips thousands commas", flt("10,500.50") == 10500.5)
	check("Banker's Rounding: flt(2.5, 0) gives 2", flt(2.5, 0, rounding_method="Banker's Rounding") == 2)
	check("Commercial Rounding: flt(2.5, 0) gives 3", flt(2.5, 0, rounding_method="Commercial Rounding") == 3)
finally:
	frappe.local.lang = "en"
	frappe.db.rollback()
	frappe.translate.clear_cache()
	frappe.clear_document_cache("System Settings")
	frappe.destroy()
