frappe.listview_settings['Biometric Data Staging'] = {
    add_fields: ["name", "status"],  

    onload: function(listview) {
    
        // Add Status Summary button
        listview.page.add_inner_button(__('View Summary'), () => {
            show_summary_dialog();
        });
    

        listview.page.add_inner_button('Sync Logs', function() {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Biometric Data Staging',
                    filters: { status: 'Pending' },
                    fields: ['name']  
                },
                callback: function(response) {
                    const pending_logs = response.message;

                    if (pending_logs.length > 0) {
                        pending_logs.forEach(function(item) {
                            frappe.call({
                                method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging.biometric_logs',
                                args: {
                                    'log_id': item.name
                                }
                            });
                        });
                        frappe.msgprint(__('Logs validated successfully.'));
                    } else {
                        frappe.msgprint(__('No logs with pending status found.'));
                    }
                }
            });
        });
    }
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
        'Ignored': 'blue',
        'Duplicate': 'gray'
    };
    return indicators[status] || 'gray';
}




