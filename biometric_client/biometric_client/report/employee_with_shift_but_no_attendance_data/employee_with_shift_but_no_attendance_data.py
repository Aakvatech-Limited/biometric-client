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
        {"label": "Shift Type", "fieldname": "shift_type", "fieldtype": "Data", "width": 100},
        {"label": "Shift Start Date", "fieldname": "shift_start", "fieldtype": "Date", "width": 130},
        {"label": "Shift End Date", "fieldname": "shift_end", "fieldtype": "Date", "width": 130},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 130},
        {"label": "Day", "fieldname": "day", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
    ]

    # Generate the query
    query = f"""
        WITH generated_dates AS (
            SELECT ADDDATE('{filters['from_date']}', INTERVAL t.n DAY) AS date
            FROM (
                SELECT a.N + b.N * 10 AS n
                FROM (
                    SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9
                ) a
                CROSS JOIN (
                    SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3
                ) b
            ) t
            WHERE ADDDATE('{filters['from_date']}', INTERVAL t.n DAY) <= '{filters['to_date']}'
        )
        SELECT 
            e.name AS employee,
            e.employee_name,
            sa.shift_type,
            sa.start_date AS shift_start,
            sa.end_date AS shift_end,
            d.date,
            DAYNAME(d.date) AS day,
            CASE 
                WHEN h.holiday_date IS NOT NULL THEN 'Holiday'
                WHEN DAYNAME(d.date) = 'Sunday' THEN 'Weekend'
                ELSE 'Missing Attendance'
            END AS status
        FROM `tabEmployee` e
        LEFT JOIN `tabShift Assignment` sa ON e.name = sa.employee
            AND sa.docstatus = 1
            AND sa.status = 'Active'
        LEFT JOIN generated_dates d ON d.date BETWEEN sa.start_date AND sa.end_date
        LEFT JOIN `tabHoliday` h ON h.holiday_date = d.date
            AND h.parent IN (
                SELECT holiday_list FROM `tabEmployee` WHERE name = e.name
            )
        LEFT JOIN `tabAttendance` a ON e.name = a.employee
            AND a.attendance_date = d.date
            AND a.docstatus = 1
        WHERE d.date BETWEEN '{filters['from_date']}' AND '{filters['to_date']}'
            AND a.name IS NULL
        ORDER BY e.employee_name, d.date
    """

    # Fetch data
    data = frappe.db.sql(query, as_dict=1)

    # Return results
    return columns, data