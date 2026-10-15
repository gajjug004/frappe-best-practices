import sys
import time

import frappe
from frappe.utils.background_jobs import create_job_id, get_redis_conn
from rq.job import Job

frappe.init(site=sys.argv[1], sites_path=".")
frappe.connect()
frappe.set_user("Administrator")

conn = get_redis_conn()


def wait_result(job_id):
	for _ in range(40):
		if Job.exists(job_id, connection=conn):
			job = Job.fetch(job_id, connection=conn)
			if job.is_finished:
				return job.return_value()
		time.sleep(0.5)
	return "timeout"


def check(label, ok):
	print(("PASS " if ok else "FAIL ") + label)


def job_exists(job_id):
	return Job.exists(job_id, connection=conn)


def enqueue_count(tag, job_id, after_commit):
	return frappe.enqueue(
		"frappe.client.get_count",
		doctype="ToDo",
		filters={"description": tag},
		job_id=job_id,
		enqueue_after_commit=after_commit,
	)


try:
	tag = f"enqueue-test-{time.time()}"

	frappe.get_doc({"doctype": "ToDo", "description": tag}).insert()
	enqueue_count(tag, f"{tag}-plain", after_commit=False)
	check("plain enqueue runs before commit and sees 0 rows", wait_result(create_job_id(f"{tag}-plain")) == 0)
	frappe.db.rollback()

	frappe.get_doc({"doctype": "ToDo", "description": tag}).insert()
	enqueue_count(tag, f"{tag}-rolled", after_commit=True)
	frappe.db.rollback()
	time.sleep(2)
	check("after_commit job is dropped on rollback", not job_exists(create_job_id(f"{tag}-rolled")))

	frappe.get_doc({"doctype": "ToDo", "description": tag}).insert()
	enqueue_count(tag, f"{tag}-after", after_commit=True)
	check("after_commit job waits for commit", not job_exists(create_job_id(f"{tag}-after")))
	frappe.db.commit()
	check("after_commit job sees the committed row", wait_result(create_job_id(f"{tag}-after")) == 1)
finally:
	frappe.db.rollback()
	for name in frappe.get_all("ToDo", filters={"description": ["like", "enqueue-test-%"]}, pluck="name"):
		frappe.delete_doc("ToDo", name, force=1)
	frappe.db.commit()
	frappe.destroy()
