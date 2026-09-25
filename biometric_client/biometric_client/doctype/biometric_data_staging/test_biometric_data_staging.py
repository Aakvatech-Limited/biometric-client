# Copyright (c) 2025, Asha Melius Kisonga and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging import (
    normalize_log_type,
)


class TestBiometricDataStaging(FrappeTestCase):
    def test_normalize_log_type_preserves_supported_values(self):
        self.assertEqual(normalize_log_type("IN"), "IN")
        self.assertEqual(normalize_log_type("OUT"), "OUT")

    def test_normalize_log_type_maps_auto_and_blank_to_blank(self):
        self.assertEqual(normalize_log_type("AUTO"), "")
        self.assertEqual(normalize_log_type(""), "")
