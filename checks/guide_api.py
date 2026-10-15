import frappe


@frappe.whitelist(force_types=False)
def double(n):
	return n * 2


@frappe.whitelist()
def double_enforced(n):
	return n * 2


@frappe.whitelist()
def double_typed(n: int):
	return n * 2


@frappe.whitelist(methods=["POST"])
def post_only():
	return "ok"


@frappe.whitelist()
def logged_in_only():
	return "ok"


@frappe.whitelist(allow_guest=True)
def guest_ok():
	return frappe.session.user


def not_whitelisted():
	return "secret"
