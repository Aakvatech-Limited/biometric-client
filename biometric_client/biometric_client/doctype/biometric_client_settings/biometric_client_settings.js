// // Copyright (c) 2025, Aakvatech and contributors
// // For license information, please see license.txt

frappe.ui.form.on('Biometric Client Settings', {
    get_token: function(frm) {
        frappe.call({
            method: 'biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.get_new_bio_token',
            callback: (r) => {
                cur_frm.set_value("bio_token", r.message);
            }
        });
    },

    get_transactions: function(frm) {
        frappe.call({
            method: 'biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.get_transactions',
            args: {
                "start_time": frm.doc.start_time,
                "end_time": frm.doc.end_time,
            },
            callback: (r) => {
                if (r.message && r.message.status === "Success") {
                    const transactions = r.message.transactions;
                    if (transactions.length > 0) {
                        let dialog = new frappe.ui.Dialog({
                            title: __("Fetched Transactions"),
                            fields: [
                                {
                                    fieldname: "transaction_table",
                                    fieldtype: "HTML",
                                    options: `<div style="overflow:auto; max-height:400px;">
                                                <table class="table table-bordered">
                                                    <thead>
                                                        <tr>
                                                            <th>ID</th>
                                                            <th>Employee</th>
                                                            <th>Punch Time</th>
                                                            <th>State</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        ${transactions.map(transaction => `
                                                        <tr>
                                                            <td>${transaction.id}</td>
                                                            <td>${transaction.emp || "N/A"}</td>
                                                            <td>${transaction.punch_time}</td>
                                                            <td>${transaction.punch_state}</td>
                                                        </tr>`).join('')}
                                                    </tbody>
                                                </table>
                                               </div>`
                                }
                            ]
                        });
                        dialog.show();
                    } else {
                        frappe.msgprint(__('No transactions found in the specified time range.'));
                    }
                } else {
                    frappe.msgprint(__('Error: ') + (r.message ? r.message.message : 'Unable to fetch transactions.'));
                }
            }
        });
    },

    make_employee_checkin: function(frm) {
        frappe.call({
            method: 'biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.make_employee_checkin',
            callback: (r) => {
                if (r.message) {
                    frappe.msgprint(r.message);
                }
            }
        });
    },

    // Consolidate custom buttons in refresh
    refresh: function(frm) {
        // Add dropdown for custom actions
        frm.add_custom_button(__('Biometric Actions'), function() {
            const actions = [
                {
                    label: __('Fetch Departments'),
                    action: () => fetch_departments()
                },
                {
                    label: __('Show Employees (WASCO ISOAF)'),
                    action: () => fetch_employees_wasco()
                },
                {
                    label: __('Start Attendance Sync'),
                    action: () => start_attendance_sync()
                },
                {
                    label: __('Transaction Report'),
                    action: () => show_transaction_report()
                }
            ];

            const dialog = new frappe.ui.Dialog({
                title: __('Custom Actions'),
                fields: [
                    {
                        fieldname: 'action',
                        fieldtype: 'Select',
                        label: __('Select Action'),
                        options: actions.map(a => a.label),
                        reqd: 1
                    }
                ],
                primary_action_label: __('Execute'),
                primary_action: function(values) {
                    const selected_action = actions.find(a => a.label === values.action);
                    if (selected_action) {
                        selected_action.action();
                    }
                    dialog.hide();
                }
            });

            dialog.show();
        }).addClass('btn-primary');
    }
});

// Helper functions for custom actions
function fetch_departments() {
    frappe.call({
        method: 'biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.fetch_departments',
        callback: function(r) {
            if (r.message) {
                let dialog = new frappe.ui.Dialog({
                    title: 'Departments List',
                    fields: [
                        {
                            fieldname: 'department_html',
                            fieldtype: 'HTML',
                            options: build_department_table(r.message)
                        }
                    ]
                });
                dialog.show();
            } else {
                frappe.msgprint(__('No departments found.'));
            }
        }
    });
}

function fetch_employees_wasco() {
    frappe.call({
        method: 'biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.fetch_employees_by_department',
        args: { department_name: "WASCO ISOAF Tanzania Limited" },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let dialog = new frappe.ui.Dialog({
                    title: 'Employees in WASCO ISOAF Tanzania Limited',
                    fields: [
                        {
                            fieldname: 'employee_html',
                            fieldtype: 'HTML',
                            options: build_employee_table(r.message)
                        }
                    ]
                });
                dialog.show();
            } else {
                frappe.msgprint(__('No employees found for the department.'));
            }
        }
    });
}

function start_attendance_sync() {
    frappe.call({
        method: 'biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.create_attendance_automated',
        callback: function(r) {
            frappe.show_alert({message: r.message, indicator: 'blue'});
        }
    });
}

function show_transaction_report() {
    let dialog = new frappe.ui.Dialog({
        title: 'Transaction Report',
        fields: [
            { fieldname: 'start_date', label: 'Start Date', fieldtype: 'Date' },
            { fieldname: 'end_date', label: 'End Date', fieldtype: 'Date' },
            { fieldname: 'page_size', label: 'Page Size', fieldtype: 'Int', default: 100 },
        ],
        primary_action_label: 'Fetch Report',
        primary_action: function(values) {
            frappe.call({
                method: 'biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.fetch_transaction_report',
                args: {
                    start_date: values.start_date,
                    end_date: values.end_date,
                    page_size: values.page_size
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let records = r.message;
                        let html_content = `
                            <table class="table table-bordered">
                                <thead>
                                    <tr>
                                        <th>Employee Code</th>
                                        <th>Employee Name</th>
                                        <th>Department</th>
                                        <th>Date</th>
                                        <th>In Time</th>
                                        <th>Out Time</th>
                                        <th>Total Worked Hours</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${records.map(record => `
                                        <tr>
                                            <td>${record.emp_code || '-'}</td>
                                            <td>${record.first_name || ''} ${record.last_name || ''}</td>
                                            <td>${record.dept_name || '-'}</td>
                                            <td>${record.att_date || '-'}</td>
                                            <td>${record.in_time || '-'}</td>
                                            <td>${record.out_time || '-'}</td>
                                            <td>${record.worked_hours || '0'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;

                        let report_dialog = new frappe.ui.Dialog({
                            title: 'Transaction Report',
                            fields: [
                                {
                                    fieldname: 'report_html',
                                    fieldtype: 'HTML',
                                    options: html_content
                                }
                            ]
                        });

                        report_dialog.show();
                    } else {
                        frappe.msgprint(__('No transactions found.'));
                    }
                }
            });
            dialog.hide();
        }
    });
    dialog.show();
}

// Helper functions for building tables
function build_department_table(departments) {
    return `<div style="max-height:400px; overflow:auto;">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Department ID</th>
                            <th>Department Code</th>
                            <th>Department Name</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${departments.map(dept => `
                            <tr>
                                <td>${dept.id}</td>
                                <td>${dept.dept_code}</td>
                                <td>${dept.dept_name}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`;
}

function build_employee_table(employees) {
    return `<div style="max-height:400px; overflow:auto;">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Employee ID</th>
                            <th>Employee Code</th>
                            <th>Name</th>
                            <th>Department</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${employees.map(emp => `
                            <tr>
                                <td>${emp.id}</td>
                                <td>${emp.emp_code || "N/A"}</td>
                                <td>${emp.first_name || "N/A"}</td>
                                <td>${emp.department || "N/A"}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`;
}