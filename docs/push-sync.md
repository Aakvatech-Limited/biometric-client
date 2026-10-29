# Push sync: devices → Biometric Data Staging → Employee Checkin

Module: **Biometric Client** · Sidebar: **Biometric Data Staging** (top of the sidebar)

This is the main path. Attendance devices, or a middleware that reads them, post punches to ERPNext. The punches land in a staging table, and a scheduled job turns them into **Employee Checkin** records.

## 1. Upload endpoint

```
POST /api/method/biometric_client.biometric_client.api.upload_bulk_biometric_data
Content-Type: application/json

[
  {"attendance_device_id": "1042", "timestamp": "2026-10-23 07:58:12", "punch_type": "IN", "device_id": "GATE-1"},
  ...
]
```

| Field | Required | Rules |
| --- | --- | --- |
| `attendance_device_id` | yes | Non-empty. Matched to **Employee → Attendance Device ID**. |
| `timestamp` | yes | Must parse as a date-time. |
| `punch_type` | yes | `IN`, `OUT`, `AUTO` or empty. |
| `device_id` | no | Up to 100 characters. |
| `status` | no | `Pending` (default), `Processed`, `Ignored`, `Duplicate`. |

- **Duplicates:** a record is skipped as a duplicate when another record with the same `(attendance_device_id, timestamp, device_id)` exists, either in the same batch or already in staging.
- **Response:** lists `success`, `failed` and `duplicates` under `details`. The HTTP status is 400 only when every record failed, or the body wasn't a JSON list.
- **Methods:** anything other than POST gets 405.

> **Security:** the endpoint is `allow_guest=True` with no token check. Anyone who can reach the site can insert staging rows. They only become check-ins if the `attendance_device_id` matches a real employee, but restrict access at the network or proxy level until the app adds authentication.

## 2. Biometric Data Staging

Autonamed · Permissions: System Manager

One row per received punch: **Attendance ID**, **Timestamp**, **Punch Type**, **Device ID** and **Status**.

| Status | Meaning |
| --- | --- |
| Pending | Received, not yet processed |
| Processed | An Employee Checkin was created |
| Ignored | No employee has this Attendance Device ID |
| Duplicate | The employee already has a check-in at exactly this time |

The list view has a **Sync** dialog that shows the status counts, and a **Start Sync** button that queues processing immediately instead of waiting for the schedule.

## 3. Processing (scheduler)

| Schedule | Job | What it does |
| --- | --- | --- |
| Every 20 minutes | `process_biometric_logs` | For every Pending row, oldest first: finds the employee by `attendance_device_id`. With no match, marks the row Ignored. If a check-in already exists at that time, marks it Duplicate. Otherwise creates an Employee Checkin (`log_type` IN/OUT; AUTO becomes blank) and marks the row Processed. |
| Daily | `send_exceptional_report` | Emails users with System Manager or HR Manager a table of today's Pending / Ignored / Processed counts, from the default outgoing email account. |

Errors on single rows are logged under **Biometric Log Processing Error** and leave the row Pending, so the next run retries it.

## Setup checklist

1. Fill **Attendance Device ID** on every Employee with the ID their fingerprint/face enrolment uses on the device.
2. Point the device middleware at the endpoint above.
3. Check that the scheduler is enabled (`bench --site <site> scheduler status`) and a default outgoing Email Account exists, for the daily report.
