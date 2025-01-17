# Copyright (c) 2025, elius mgani and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # Ensure filters are a dictionary
    filters = frappe.parse_json(filters) if isinstance(filters, str) else filters or {}

    # Validate mandatory filters
    mandatory_fields = ["from_date", "to_date"]
    for field in mandatory_fields:
        if not filters.get(field):
            frappe.throw(f"{field} is mandatory")

    # Define columns
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Data", "width": 150},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 220},
        {"label": "Attendance Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Data", "width": 100},
        {"label": "Attendance Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 130},
    ]

    # Generate the query
    query = f"""
        SELECT DISTINCT
            a.employee,
            a.employee_name,
            a.status,
            a.shift,
            a.attendance_date
        FROM `tabAttendance` a
        INNER JOIN `tabShift Assignment` sa ON a.employee = sa.employee
            AND sa.docstatus = 1
            AND sa.status = 'Active'
            AND sa.start_date <= a.attendance_date
            AND sa.end_date >= a.attendance_date
        WHERE a.attendance_date BETWEEN '{filters['from_date']}' AND '{filters['to_date']}'
            AND a.docstatus = 1
        ORDER BY a.employee_name, a.attendance_date
    """

    # Fetch data
    data = frappe.db.sql(query, as_dict=1)

    # Return results
    return columns, data
