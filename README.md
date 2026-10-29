<img src="biometric_client/public/images/biometric_client-logo.svg" alt="Biometric Client" width="64" height="64">

# Biometric Client

Syncs biometric attendance-device punches into Frappe HR **Employee Checkin**, and reports on shift coverage against attendance.

**App version:** `16.0.0` · **Frappe / ERPNext / HRMS:** `>=16.0.0,<17.0.0`

## How it works

| Path | Flow | Docs |
| --- | --- | --- |
| **Push** (main) | Device → `upload_bulk_biometric_data` API → Biometric Data Staging → Employee Checkin (every 20 min) | [Push sync](docs/push-sync.md) |
| **Pull** (legacy) | ZKBioTime server → Transactions Log → Employee Checkin / Attendance | [ZKBioTime pull](docs/zkbiotime-pull.md) |
| **Reports** | Shift assignments with and without attendance | [Reports](docs/reports.md) |

## Doctypes

| Doctype | Purpose |
| --- | --- |
| Biometric Data Staging | One received punch, with its processing status |
| Biometric Client Settings | ZKBioTime connection and pull-path switches (Single) |

## Navigation

- **Apps screen:** a **Biometric Client** tile with the teal BC logo opens the first sidebar item (Biometric Data Staging).
- **Sidebar:** Biometric Data Staging, then *Attendance Reports* (2 reports) and *Setup* (Biometric Client Settings).

These ship as standard records and are imported on `bench migrate`:

| What | File |
| --- | --- |
| Sidebar | `biometric_client/biometric_client/sidebar/biometric_client/biometric_client.json` |
| Dock | `biometric_client/dock/biometric_client/biometric_client.json` |
| Desktop icon | `biometric_client/desktop_icon/biometric_client.json` |
| Logo | `biometric_client/public/images/biometric_client-logo.svg` |

## Installation

```bash
bench get-app biometric_client <repository-url>
bench --site <site> install-app biometric_client
bench --site <site> migrate
```

**Required apps:** `erpnext`, `hrms`.

## Development

```bash
pre-commit install
pre-commit run --all-files
```

Pre-commit runs ruff, prettier and eslint. Pull requests also run Semgrep with Frappe's rules, pip-audit, and commitlint, so commit messages must follow Conventional Commits (`feat:`, `fix:`, `refactor:` and so on). Database access uses `frappe.qb`, not raw SQL.

## License

MIT. See [license.txt](license.txt).
