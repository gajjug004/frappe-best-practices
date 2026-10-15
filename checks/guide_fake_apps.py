from frappe.desk.doctype.todo.todo import ToDo

calls = []


class AppAToDo(ToDo):
	def validate(self):
		super().validate()
		calls.append("app_a override")


class AppBToDo(ToDo):
	def validate(self):
		super().validate()
		calls.append("app_b override")


class AppAMixin:
	def validate(self):
		super().validate()
		calls.append("app_a extend")


class AppBMixin:
	def validate(self):
		super().validate()
		calls.append("app_b extend")


def app_a_validate(doc, method):
	calls.append("app_a doc_event")


def app_b_validate(doc, method):
	calls.append("app_b doc_event")


