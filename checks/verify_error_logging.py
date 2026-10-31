import os
import sys

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

import frappe
from frappe.app import handle_exception
from frappe.core.doctype.error_log.error_log import get_queued_error_log_count
from frappe.deferred_insert import save_to_db
from frappe.utils.background_jobs import execute_job
from frappe.utils.logging import get_log_db, is_log_doctype, log_table

frappe.init(site=sys.argv[1], sites_path=".")
frappe.connect()
frappe.set_user("Administrator")

MARKER = "bp-error-logging-check"


def check(label, ok):
	print(("PASS " if ok else "FAIL ") + label)


def error_logs(title_like=MARKER):
	return frappe.get_all("Error Log", filters={"method": ["like", f"%{title_like}%"]}, fields=["*"])


def queue_delta(action):
	before = get_queued_error_log_count()
	action()
	return get_queued_error_log_count() - before


def raise_and_handle(exception):
	try:
		raise exception
	except Exception as e:
		handle_exception(e)


def job_that_throws():
	frappe.throw(MARKER)


def fake_request():
	frappe.local.request = Request(EnvironBuilder(path="/api/method/test", method="POST").get_environ())
	frappe.local.is_ajax = True


def delete_marked_logs():
	save_to_db(doctype="Error Log")
	qb, table = log_table("Error Log")
	db = get_log_db()
	db.sql(qb.from_(table).where(table.method.like(f"%{MARKER}%") | table.error.like(f"%{MARKER}%")).delete())
	db.commit()


try:
	print("== where Error Log rows live ==")
	check("Error Log is a log DocType", is_log_doctype("Error Log"))
	frappe.log_error(f"{MARKER} where")
	check("frappe.get_all finds the log", len(error_logs(f"{MARKER} where")) == 1)
	check(
		"frappe.db.exists returns None for the same log, no error",
		frappe.db.exists("Error Log", {"method": f"{MARKER} where"}) is None,
	)
	try:
		frappe.db.delete("Error Log", {"method": f"{MARKER} where"})
		check("frappe.db.delete on Error Log raises", False)
	except Exception as e:
		check(f"frappe.db.delete on Error Log raises {type(e).__name__}, table missing", "1146" in str(e))
	frappe.db.rollback()
	frappe.delete_doc("Error Log", error_logs(f"{MARKER} where")[0].name)
	check("frappe.delete_doc deletes the log", not error_logs(f"{MARKER} where"))
	delete_marked_logs()

	print("== log_error inside except ==")
	try:
		1 / 0
	except ZeroDivisionError:
		frappe.log_error(f"{MARKER} payment sync", reference_doctype="User", reference_name="Administrator")
	log = error_logs()[0]
	check("title is stored in method", log.method == f"{MARKER} payment sync")
	check("traceback is captured automatically", "ZeroDivisionError" in log.error)
	check("reference doctype and name are stored", (log.reference_doctype, log.reference_name) == ("User", "Administrator"))
	check("fingerprint is set inside except", bool(log.fingerprint))
	delete_marked_logs()

	print("== log_error outside except ==")
	frappe.log_error(f"{MARKER} no exception")
	log = error_logs()[0]
	print("stored error:", repr(log.error))
	check("error body is empty outside except", log.error == "")
	check("no fingerprint outside except", not log.fingerprint)
	frappe.log_error(f"{MARKER} with message", message="order 42 has no customer")
	check("message is stored as the error body", error_logs(f"{MARKER} with message")[0].error == "order 42 has no customer")
	delete_marked_logs()

	print("== swapped arguments ==")
	frappe.log_error("line one\nline two", f"{MARKER} swapped")
	log = error_logs()[0]
	check("multi-line title is swapped into the body", log.method == f"{MARKER} swapped" and log.error == "line one\nline two")
	delete_marked_logs()

	print("== long title ==")
	frappe.log_error(MARKER + " x" * 100)
	log = error_logs()[0]
	check("title is cut to 140 chars", len(log.method) == 140)
	check("full title is kept in the error body", log.error.startswith(MARKER + " x" * 100))
	delete_marked_logs()

	print("== log then rollback ==")
	frappe.log_error(f"{MARKER} kept")
	frappe.db.rollback()
	check("log survives rollback (log database commits on its own)", len(error_logs(f"{MARKER} kept")) == 1)
	delete_marked_logs()

	print("== what the request handler logs ==")
	fake_request()
	for developer_mode in (0, 1):
		frappe.local.conf.developer_mode = developer_mode
		throw_delta = queue_delta(lambda: raise_and_handle(frappe.ValidationError(MARKER)))
		bug_delta = queue_delta(lambda: raise_and_handle(ZeroDivisionError(MARKER)))
		check(f"developer_mode={developer_mode}: ValidationError logged = {bool(throw_delta)}", throw_delta == developer_mode)
		check(f"developer_mode={developer_mode}: 500 error logged", bug_delta == 1)
	delete_marked_logs()

	print("== failed background job ==")
	try:
		execute_job(frappe.local.site, job_that_throws, None, None, {}, is_async=False)
	except frappe.ValidationError:
		pass
	logs = frappe.get_all("Error Log", filters={"error": ["like", f"%{MARKER}%"]}, pluck="method")
	print("job log titles:", logs)
	check("frappe.throw in a job is logged, titled with the method path", "__main__.job_that_throws" in logs)
	delete_marked_logs()

	print("== frappe.logger levels ==")
	log_path = os.path.join(frappe.get_site_path("logs"), f"{MARKER}.log")
	logger = frappe.logger(MARKER)
	print("logger level:", logger.level, "file:", log_path)
	logger.info("info line")
	logger.warning("warning line")
	logger.error("error line")
	for handler in logger.handlers:
		handler.flush()
	content = open(log_path).read() if os.path.exists(log_path) else ""
	check("logger.info is dropped at the default level", "info line" not in content)
	check("logger.error is written to sites/<site>/logs/<module>.log", "error line" in content)

	frappe.utils.logger.set_log_level("INFO")
	logger = frappe.logger(MARKER)
	logger.info("info after set_log_level")
	for handler in logger.handlers:
		handler.flush()
	check("set_log_level('INFO') turns on info", "info after set_log_level" in open(log_path).read())
finally:
	frappe.db.rollback()
	frappe.local.conf.developer_mode = frappe.get_site_config().get("developer_mode")
	delete_marked_logs()
	for name in os.listdir(frappe.get_site_path("logs")):
		if name.startswith(MARKER):
			os.remove(os.path.join(frappe.get_site_path("logs"), name))
	frappe.destroy()
