# Copyright (c) 2025, elius mgani and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate


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
		{"label": _("Shift Type"), "fieldname": "shift_type", "fieldtype": "Data", "width": 100},
		{"label": _("Shift Start Date"), "fieldname": "shift_start", "fieldtype": "Date", "width": 130},
		{"label": _("Shift End Date"), "fieldname": "shift_end", "fieldtype": "Date", "width": 130},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 130},
		{"label": _("Day"), "fieldname": "day", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
	]

	return columns, get_data(getdate(filters.from_date), getdate(filters.to_date))


def get_data(from_date, to_date):
	"""One row per day an employee's active shift assignment covers but no submitted attendance exists."""
	employee = frappe.qb.DocType("Employee")
	assignment = frappe.qb.DocType("Shift Assignment")
	assignments = (
		frappe.qb.from_(employee)
		.inner_join(assignment)
		.on(
			(employee.name == assignment.employee)
			& (assignment.docstatus == 1)
			& (assignment.status == "Active")
		)
		.select(
			employee.name.as_("employee"),
			employee.employee_name,
			employee.holiday_list,
			assignment.shift_type,
			assignment.start_date.as_("shift_start"),
			assignment.end_date.as_("shift_end"),
		)
		.where(
			assignment.start_date.isnotnull()
			& assignment.end_date.isnotnull()
			& (assignment.start_date <= to_date)
			& (assignment.end_date >= from_date)
		)
	).run(as_dict=True)
	if not assignments:
		return []

	employees = list({row.employee for row in assignments})
	attended = get_attended_days(employees, from_date, to_date)
	holidays = get_holidays({row.holiday_list for row in assignments if row.holiday_list}, from_date, to_date)

	data = []
	for row in assignments:
		day = max(from_date, getdate(row.shift_start))
		last_day = min(to_date, getdate(row.shift_end))
		while day <= last_day:
			if (row.employee, day) not in attended:
				day_name = day.strftime("%A")
				if day in holidays.get(row.holiday_list, ()):
					status = "Holiday"
				elif day_name == "Sunday":
					status = "Weekend"
				else:
					status = "Missing Attendance"
				data.append(
					frappe._dict(
						employee=row.employee,
						employee_name=row.employee_name,
						shift_type=row.shift_type,
						shift_start=row.shift_start,
						shift_end=row.shift_end,
						date=day,
						day=day_name,
						status=status,
					)
				)
			day = add_days(day, 1)

	data.sort(key=lambda d: (d.employee_name or "", d.date))
	return data


def get_attended_days(employees, from_date, to_date):
	attendance = frappe.qb.DocType("Attendance")
	rows = (
		frappe.qb.from_(attendance)
		.select(attendance.employee, attendance.attendance_date)
		.where(
			attendance.employee.isin(employees)
			& (attendance.docstatus == 1)
			& attendance.attendance_date.between(from_date, to_date)
		)
	).run()
	return {(employee, getdate(day)) for employee, day in rows}


def get_holidays(holiday_lists, from_date, to_date):
	if not holiday_lists:
		return {}

	holiday = frappe.qb.DocType("Holiday")
	rows = (
		frappe.qb.from_(holiday)
		.select(holiday.parent, holiday.holiday_date)
		.where(holiday.parent.isin(list(holiday_lists)) & holiday.holiday_date.between(from_date, to_date))
	).run()

	holidays = {}
	for holiday_list, day in rows:
		holidays.setdefault(holiday_list, set()).add(getdate(day))
	return holidays
