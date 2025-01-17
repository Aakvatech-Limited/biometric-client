frappe.listview_settings['Biometric Data Staging'] = {
    add_fields: ["name", "status"],  

    onload: function(listview) {
        // Add Status Summary button
        listview.page.add_inner_button(__('View Summary'), () => {
            show_summary_dialog();
        });

        // Add Sync Logs button
        listview.page.add_inner_button('Sync Logs', function() {
            frappe.call({
                method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging.biometric_logs',
                callback: function(response) {
                    
                    frappe.msgprint(__('Logs validated successfully.'));
                }
            });
        });
    }
};

function show_summary_dialog() {
    frappe.call({
        method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging.get_sync_status_summary',
        callback: function(r) {
            if (r.message && !r.message.error) {
                const data = r.message;
                const dialog = new frappe.ui.Dialog({
                    title: __('Biometric Sync Status Summary'),
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

function get_summary_html(data) {
    let html = `
        <div class="sync-summary">
            <div class="row mt-4">
                <div class="col-md-12">
                    <h6 class="text-muted">${__('Last 7 Days Breakdown')}</h6>
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Logs Summary</th>
                            </tr>
                        </thead>
                        <tbody>
    `;

    // Group data by date
    const dateGroups = {};
    data.status_summary.forEach(row => {
        const date = row.date;
        if (!dateGroups[date]) {
            dateGroups[date] = {
                'Processed': 0,
                'Pending': 0,
                'Ignored': 0
            };
        }
        dateGroups[date][row.status] = row.count;
    });

    // Add rows for each date
    Object.entries(dateGroups).forEach(([date, counts]) => {
        html += `
            <tr>
                <td>${frappe.datetime.str_to_user(date)}</td>
                <td><span class="indicator green">${counts['Processed'] || 0}</span></td>
                <td><span class="indicator orange">${counts['Pending'] || 0}</span></td>
                <td><span class="indicator blue">${counts['Ignored'] || 0}</span></td>
            </tr>
        `;
    });

    html += `
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="row mt-4">
                <div class="col-md-12">
                    <h6 class="text-muted">${__('Device Statistics')}</h6>
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>${__('Device ID')}</th>
                                <th>${__('Total Records')}</th>
                                <th>${__('Last Sync')}</th>
                                <th class="text-center">${__('Processed')}</th>
                                <th class="text-center">${__('Pending')}</th>
                                <th class="text-center">${__('Ignored')}</th>
                            </tr>
                        </thead>
                        <tbody>
    `;

    data.device_stats.forEach(device => {
        const statusDetails = {
            'Processed': 0,
            'Pending': 0,
            'Ignored': 0
        };

        if (device.status_details) {
            device.status_details.forEach(status => {
                if (statusDetails.hasOwnProperty(status.status)) {
                    statusDetails[status.status] = status.status_count;
                }
            });
        }

        html += `
            <tr>
                <td>${device.device_id}</td>
                <td>${device.count}</td>
                <td>${frappe.datetime.str_to_user(device.last_sync)}</td>
                <td class="text-center">
                    <span class="indicator green">${statusDetails['Processed']}</span>
                </td>
                <td class="text-center">
                    <span class="indicator orange">${statusDetails['Pending']}</span>
                </td>
                <td class="text-center">
                    <span class="indicator blue">${statusDetails['Ignored']}</span>
                </td>
            </tr>
        `;
    });

    html += `
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    return html;
}

// Helper function for status indicators
function get_status_indicator(status) {
    const indicators = {
        'Pending': 'orange',
        'Processed': 'green',
        'Ignored': 'blue'
    };
    return indicators[status] || 'gray';
}
