// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.listview_settings['Biometric Data Staging'] = {
    onload: function(listview) {
        // Add Sync Now button
        listview.page.add_inner_button(__('Sync Now'), function() {
            show_sync_dialog(listview);
        });

        // Add View Summary button
        listview.page.add_inner_button(__('View Summary'), function() {
            show_summary_dialog();
        });
    },
};

// Sync Dialog
function show_sync_dialog(listview) {
    const dialog = new frappe.ui.Dialog({
        title: __('Synchronize Biometric Data'),
        fields: [
            {
                fieldname: 'status_html',
                fieldtype: 'HTML',
                options: `
                    <div class="sync-status">
                        <div class="alert alert-info">
                            This will synchronize biometric logs to Employee Checkin.
                        </div>
                    </div>
                `
            }
        ],
        primary_action_label: __('Start Sync'),
        primary_action: function() {
            // Show processing message
            frappe.show_alert({
                message: __('Synchronization started...'),
                indicator: 'blue'
            });

            // Call the Python function process_biometric_logs
            frappe.call({
                method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging.enqueue_process_biometric_logs',
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: r.message,
                            indicator: 'green'
                        });
                    } else {
                        frappe.show_alert({
                            message: __('Synchronization completed successfully'),
                            indicator: 'green'
                        });
                    }
                },
                error: function() {
                    frappe.show_alert({
                        message: __('Synchronization failed'),
                        indicator: 'red'
                    });
                }
            });

            dialog.hide();
        }
    });
    dialog.show();
}

// Summary Dialog
function show_summary_dialog() {
    frappe.call({
        method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging_list.get_sync_status_summary',
        callback: function(r) {
            if (r.message && !r.message.error) {
                const data = r.message;
                
                const dialog = new frappe.ui.Dialog({
                    title: __('Biometric Data Summary'),
                    fields: [
                        {
                            fieldname: 'summary_html',
                            fieldtype: 'HTML',
                            options: get_summary_html(data)
                        }
                    ],
                    size: 'large'
                });
                dialog.show();
            } else {
                frappe.show_alert({
                    message: r.message.error || __('Failed to fetch summary'),
                    indicator: 'red'
                });
            }
        }
    });
}

// Helper function to generate summary HTML
function get_summary_html(data) {
    let html = `
        <div class="sync-summary">
            <h6 class="text-muted">${__('Last 7 Days Status')}</h6>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Date')}</th>
                        <th>${__('Status')}</th>
                        <th>${__('Count')}</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.status_summary.forEach(row => {
        html += `
            <tr>
                <td>${frappe.datetime.str_to_user(row.date)}</td>
                <td>
                    <span class="indicator ${get_status_indicator(row.status)}">
                        ${row.status}
                    </span>
                </td>
                <td>${row.count}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
            
            <h6 class="text-muted mt-4">${__('Device Statistics')}</h6>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Device ID')}</th>
                        <th>${__('Total Records')}</th>
                        <th>${__('Last Sync')}</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.device_stats.forEach(device => {
        html += `
            <tr>
                <td>${device.device_id}</td>
                <td>${device.count}</td>
                <td>${frappe.datetime.str_to_user(device.last_sync)}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    return html;
}

// Helper function for status indicators
function get_status_indicator(status) {
    const indicators = {
        'Pending': 'orange',
        'Processed': 'green',
        'Failed': 'red',
        'Ignored': 'gray',
        'Duplicate': 'blue'
    };
    return indicators[status] || 'gray';
}