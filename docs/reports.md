# Reports

Module: **Biometric Client** · Sidebar: **Attendance Reports**

Both reports need **From Date** and **To Date**. They only consider **submitted, Active** Shift Assignments and **submitted** Attendance.

## Employee with Shift but No Attendance Data

Reference doctype: Employee · Roles: HR Manager, HR User, Employee, System Manager, All, Employee Self Service, Supervisor

One row per employee per day that one of the employee's active shift assignments covers inside the date range, but has no submitted Attendance.

| Column | Value |
| --- | --- |
| Employee, Employee Name | The employee |
| Shift Type, Shift Start Date, Shift End Date | The covering shift assignment |
| Date, Day | The day with no attendance |
| Status | **Holiday** if the date is in the employee's Holiday List, **Weekend** if it's a Sunday, otherwise **Missing Attendance** |

- Assignments without an end date are skipped.
- Rows are sorted by employee name, then date.
- The role list includes **All** and **Employee**, so any logged-in user can see every employee's gaps. Narrow the roles on the Report if that's not intended.

## Employee with Shift Assignment and Attendance Record

Reference doctype: Attendance · Roles: System Manager, HR User, HR Manager, Employee Self Service

Distinct submitted Attendance records in the range that fall inside one of the employee's active shift assignments: Employee, Employee Name, Attendance Status, Shift and Attendance Date. Sorted by employee name, then date.

## Changed in the v16 upgrade

- Both reports used to paste the dates straight into SQL (an injection risk). They now use frappe.qb with parameters.
- The no-attendance report used to generate at most **40 days** of dates, so longer ranges silently lost their later days. It now covers the full range.
