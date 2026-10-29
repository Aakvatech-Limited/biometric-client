# Copyright (c) 2025, elius mgani and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	# Ensure filters are a dictionary
	filters = frappe._dict(frappe.parse_json(filters) if isinstance(filters, str) else filters or {})

	# Validate mandatory filters
	for field in ("from_date", "to_date"):
		if not filters.get(field):
			frappe.throw(_("{0} is mandatory").format(field))

	columns = [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 150},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 220},
		{"label": _("Attendance Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
		{"label": _("Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 100},
		{"label": _("Attendance Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 130},
	]

	attendance = frappe.qb.DocType("Attendance")
	assignment = frappe.qb.DocType("Shift Assignment")
	data = (
		frappe.qb.from_(attendance)
		.inner_join(assignment)
		.on(
			(attendance.employee == assignment.employee)
			& (assignment.docstatus == 1)
			& (assignment.status == "Active")
			& (assignment.start_date <= attendance.attendance_date)
			& (assignment.end_date >= attendance.attendance_date)
		)
		.select(
			attendance.employee,
			attendance.employee_name,
			attendance.status,
			attendance.shift,
			attendance.attendance_date,
		)
		.distinct()
		.where(
			attendance.attendance_date.between(filters.from_date, filters.to_date)
			& (attendance.docstatus == 1)
		)
		.orderby(attendance.employee_name)
		.orderby(attendance.attendance_date)
	).run(as_dict=True)

	return columns, data
