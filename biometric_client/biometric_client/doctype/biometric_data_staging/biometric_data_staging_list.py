# Copyright (c) 2025, Joshua Joseph Michael and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta


@frappe.whitelist()
def get_sync_status_summary():
    """
    Get summary of sync status for dashboard
    """
    try:
        # Get status summary for the last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        summary = frappe.get_all(
            "Biometric Data Staging",
            filters={"timestamp": [">=", seven_days_ago]},
            fields=["status", "COUNT(name) as count", "DATE(timestamp) as date"],
            group_by="status, DATE(timestamp)",
            order_by="DATE(timestamp) DESC"
        )

        # Get device stats
        device_stats = frappe.get_all(
            "Biometric Data Staging",
            fields=["device_id", "COUNT(name) as count", "MAX(timestamp) as last_sync"],
            group_by="device_id"
        )

        return {
            'status_summary': summary,
            'device_stats': device_stats
        }

    except Exception as e:
        frappe.log_error(f"Error getting sync summary: {str(e)}", "Biometric List View Error")
        return {'error': str(e)}