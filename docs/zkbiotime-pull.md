# Pull sync: ZKBioTime server (Biometric Client Settings)

Module: **Biometric Client** · Sidebar: **Setup → Biometric Client Settings**

> **Status: not usable as shipped.** This path reads and writes the **Transactions Log** and **Transaction Fetch Log** doctypes and the **Employee → biometric_id** field. This app doesn't ship any of them, and no other app on the v16 bench does either. `biometric_id` exists only as a csf_tz custom-field fixture. Use the [push sync](push-sync.md) unless a site provides those doctypes.

## Biometric Client Settings

Single · Permissions: System Manager

| Field | Purpose |
| --- | --- |
| Enable Biometric Attendance | Master switch. Most pull actions do nothing while it's off. |
| Server URL, User Name, Password | The ZKBioTime server and its API login |
| Get Token → Bio Token | Fetches and stores the API token |
| Default Department Code, Default Area Code | Used when creating employees on the device server |
| Default Shift Type | Shift used for auto shift assignments |
| Enable Auto Transactions / Auto Employee Checkin / Auto Shift Assignment | Toggles for the `auto_*` functions. None are scheduled in `hooks.py`, so something else has to call them. |
| Start Time, End Time → Get Transactions | Pulls `/iclock/api/transactions/` for the window into Transactions Log |
| Last Sync Time | Set after each pull. Also the default start for automated attendance. |
| Make Employee Checkin | Converts Waiting Transactions Log rows into Employee Checkins, and creates a Shift Assignment for the punch date if none starts that day |

The **Biometric Actions** button opens a dialog with: Fetch Departments, Show Employees, Start Attendance Sync and Transaction Report.

- **Show Employees** and **Start Attendance Sync** are hard-wired to the department *WASCO ISOAF Tanzania Limited*. They were written for one customer.
- **Start Attendance Sync** (`create_attendance_automated`) queues `process_attendance_in_background`, which creates **Attendance** records directly from the server's transaction report.

## Fixed in the v16 upgrade

- `creat_shift_assignment` searched and created Shift Assignments by a `date` field. Shift Assignment only has `start_date`/`end_date`, so it failed with "Unknown column". It now uses `start_date`.
- `get_shift_type` was defined twice. The second definition, which takes two arguments, replaced the first, so the one-argument calls in Make Employee Checkin and auto shift assignment raised `TypeError`. The second is now `get_shift_type_on_date`.

Neither fix could be tested on the bench, because of the missing doctypes above.
