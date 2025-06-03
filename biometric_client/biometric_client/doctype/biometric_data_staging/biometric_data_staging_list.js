// Copyright (c) 2025, Joshua Joseph Michael and contributors
// For license information, please see license.txt

frappe.listview_settings['Biometric Data Staging'] = {
    refresh: function(listview) {
        // Clear existing buttons
        listview.page.clear_inner_toolbar();
        
        // Add Sync Now button
        listview.page.add_inner_button(__('Sync Now'), () => {
            show_sync_dialog(listview);
        }, 'Action');
        
        // Add Export button
        listview.page.add_inner_button(__('Export Data'), () => {
            show_export_dialog(listview);
        });
        
        // Add Bulk Actions button
        listview.page.add_inner_button(__('Bulk Actions'), () => {
            show_bulk_action_dialog(listview);
        });
        
        // Add Status Summary button
        listview.page.add_inner_button(__('View Summary'), () => {
            show_summary_dialog();
        });
    },

    // Add indicators for different statuses
    get_indicator: function(doc) {
        return [
            {
                'Pending': ['orange', 'status,=,Pending'],
                'Processed': ['green', 'status,=,Processed'],
                'Failed': ['red', 'status,=,Failed'],
                'Ignored': ['gray', 'status,=,Ignored'],
                'Duplicate': ['blue', 'status,=,Duplicate']
            }[doc.status],
            'status,=,' + doc.status
        ];
    }
};

function process_records(records, dialog, listview) {
    if (!records.length) {
        frappe.show_alert({
            message: __('No records to process'),
            indicator: 'orange'
        });
        dialog.hide();
        return;
    }

    frappe.call({
        method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging_list.bulk_process_records',
        args: {
            records: records,
            action: 'retry_sync'
        },
        callback: function(r) {
            if (r.message && !r.message.error) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                listview.refresh();
            } else {
                frappe.show_alert({
                    message: r.message.error || __('Sync failed'),
                    indicator: 'red'
                });
            }
            dialog.hide();
        }
    });
}
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
            },
            {
                label: __('Sync Options'),
                fieldname: 'sync_type',
                fieldtype: 'Select',
                options: [
                    { label: __('Selected Entries'), value: 'selected' },
                    { label: __('All Pending Entries'), value: 'pending' },
                    { label: __('Retry Failed Entries'), value: 'failed' }
                ],
                default: 'selected'
            }
        ],
        primary_action_label: __('Start Sync'),
        primary_action: function(values) {
            let records_to_sync = [];
            
            if (values.sync_type === 'selected') {
                records_to_sync = listview.get_checked_items().map(d => d.name);
                if (!records_to_sync.length) {
                    frappe.show_alert({
                        message: __('Please select records to sync'),
                        indicator: 'orange'
                    });
                    return;
                }
                process_records(records_to_sync, dialog, listview);
            } else {
                // Show processing message
                frappe.show_alert({
                    message: __('Fetching records...'),
                    indicator: 'blue'
                });

                // Get all records of the specified status
                frappe.call({
                    method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging_list.get_list_data',
                    args: {
                        filters: {
                            status: values.sync_type === 'pending' ? 'Pending' : 'Failed'
                        },
                        limit: 500  // Reduced to a safer number
                    },
                    callback: function(r) {
                        if (r.message && r.message.data && r.message.data.length > 0) {
                            records_to_sync = r.message.data.map(d => d.name);
                            frappe.show_alert({
                                message: __(`Processing ${records_to_sync.length} records...`),
                                indicator: 'blue'
                            });
                            process_records(records_to_sync, dialog, listview);
                        } else {
                            frappe.show_alert({
                                message: __('No records found to sync'),
                                indicator: 'orange'
                            });
                            dialog.hide();
                        }
                    }
                });
            }
        }
    });
    dialog.show();
}

// Helper function to process records in batches
function process_records(records, dialog, listview) {
    if (!records.length) {
        frappe.show_alert({
            message: __('No records to process'),
            indicator: 'orange'
        });
        dialog.hide();
        return;
    }

    // Process in smaller batches if needed
    const BATCH_SIZE = 100;
    let processed = 0;
    
    function process_batch() {
        const batch = records.slice(processed, processed + BATCH_SIZE);
        if (batch.length === 0) {
            listview.refresh();
            dialog.hide();
            return;
        }

        frappe.call({
            method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging_list.bulk_process_records',
            args: {
                records: batch,
                action: 'retry_sync'
            },
            callback: function(r) {
                if (r.message && !r.message.error) {
                    processed += batch.length;
                    const progress = Math.round((processed / records.length) * 100);
                    
                    frappe.show_alert({
                        message: __(`Processed ${processed} of ${records.length} records (${progress}%)`),
                        indicator: 'blue'
                    });

                    if (processed < records.length) {
                        process_batch(); // Process next batch
                    } else {
                        frappe.show_alert({
                            message: __('Processing completed successfully'),
                            indicator: 'green'
                        });
                        listview.refresh();
                        dialog.hide();
                    }
                } else {
                    frappe.show_alert({
                        message: r.message.error || __('Sync failed'),
                        indicator: 'red'
                    });
                    dialog.hide();
                }
            }
        });
    }

    // Start processing
    process_batch();
}

// Export Dialog
function show_export_dialog(listview) {
    const dialog = new frappe.ui.Dialog({
        title: __('Export Biometric Data'),
        fields: [
            {
                label: __('Date Range'),
                fieldname: 'date_range',
                fieldtype: 'DateRange',
                reqd: 1
            },
            {
                label: __('Status'),
                fieldname: 'status',
                fieldtype: 'MultiSelect',
                options: ['Pending', 'Processed', 'Failed', 'Ignored', 'Duplicate']
            },
            {
                label: __('Device ID'),
                fieldname: 'device_id',
                fieldtype: 'Data'
            }
        ],
        primary_action_label: __('Export'),
        primary_action: function(values) {
            frappe.call({
                method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging_list.export_data',
                args: {
                    filters: values
                },
                callback: function(r) {
                    if (r.message && r.message.file_url) {
                        window.open(r.message.file_url, '_blank');
                        dialog.hide();
                    } else {
                        frappe.show_alert({
                            message: r.message.error || __('Export failed'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    });
    dialog.show();
}

// Bulk Action Dialog
function show_bulk_action_dialog(listview) {
    const selected_docs = listview.get_checked_items();
    
    if (!selected_docs.length) {
        frappe.show_alert({
            message: __('Please select records to process'),
            indicator: 'orange'
        });
        return;
    }

    const dialog = new frappe.ui.Dialog({
        title: __('Bulk Process Records'),
        fields: [
            {
                fieldname: 'selected_html',
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-info">
                        Selected Records: ${selected_docs.length}
                    </div>
                `
            },
            {
                label: __('Action'),
                fieldname: 'action',
                fieldtype: 'Select',
                options: [
                    { label: __('Mark as Processed'), value: 'mark_processed' },
                    { label: __('Mark as Ignored'), value: 'mark_ignored' },
                    { label: __('Retry Sync'), value: 'retry_sync' }
                ],
                reqd: 1
            }
        ],
        primary_action_label: __('Process'),
        primary_action: function(values) {
            frappe.call({
                method: 'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging_list.bulk_process_records',
                args: {
                    records: selected_docs.map(d => d.name),
                    action: values.action
                },
                callback: function(r) {
                    if (r.message && !r.message.error) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        });
                        listview.refresh();
                    } else {
                        frappe.show_alert({
                            message: r.message.error || __('Process failed'),
                            indicator: 'red'
                        });
                    }
                    dialog.hide();
                }
            });
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