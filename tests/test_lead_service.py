# Write Unittest for lead_service.py
import unittest
from unittest.mock import MagicMock
from lead_service import LeadService, ValidationException


class TestLeadService(unittest.TestCase):

    def setUp(self):
        self.lead_repo_mock = MagicMock()
        self.sales_agent_repo_mock = MagicMock()
        self.notification_service_mock = MagicMock()
        self.lead_service = LeadService(self.lead_repo_mock, self.sales_agent_repo_mock, self.notification_service_mock)

    def test_should_raise_exception_when_no_email_or_phone(self):
        lead_data = {'name': 'Test Lead'}
        with self.assertRaises(ValidationException) as context:
            self.lead_service.process_lead(lead_data)
        self.assertEqual(context.exception.messages, {'error': 'Lead must have email or phone number'})

    def test_should_raise_exception_when_invalid_email(self):
        lead_data = {'name': 'Test Lead', 'email': 'invalid-email', 'phone': '+1234567890'}
        with self.assertRaises(ValidationException) as context:
            self.lead_service.process_lead(lead_data)
        self.assertEqual(context.exception.messages, {'error': 'Invalid email or phone format'})

    def test_should_raise_exception_when_invalid_phone(self):
        lead_data = {'name': 'Test Lead', 'email': 'test@example.com', 'phone': 'invalid-phone'}
        with self.assertRaises(ValidationException) as context:
            self.lead_service.process_lead(lead_data)
        self.assertEqual(context.exception.messages, {'error': 'Invalid email or phone format'})

    def test_should_update_lead_when_existing_lead_found(self):
        lead_data = {'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890'}
        existing_lead = {'id': 1, 'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890'}
        self.lead_repo_mock.find_by_email_or_phone.return_value = existing_lead
        result = self.lead_service.process_lead(lead_data)
        self.assertEqual(result, {'message': 'Lead updated'})
        self.lead_repo_mock.update.assert_called_once_with(1, lead_data)

    def test_should_add_to_waiting_queue_when_no_available_agent(self):
        lead_data = {'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890', 'location': 'Test Location'}
        self.lead_repo_mock.find_by_email_or_phone.return_value = None
        self.sales_agent_repo_mock.get_best_available_agent.return_value = None
        result = self.lead_service.process_lead(lead_data)
        self.assertEqual(result, {'message': 'No available sales agents. Lead added to waiting queue.'})
        self.lead_repo_mock.save_to_waiting_queue.assert_called_once()

    def test_should_create_and_assign_new_lead_when_no_existing_lead(self):
        lead_data = {'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890', 'location': 'Test Location'}
        self.lead_repo_mock.find_by_email_or_phone.return_value = None
        sales_agent = {'id': 1, 'name': 'Test Agent'}
        self.sales_agent_repo_mock.get_best_available_agent.return_value = sales_agent
        new_lead = {'id': 2, 'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890', 'assigned_agent': 1}
        self.lead_repo_mock.create.return_value = new_lead
        result = self.lead_service.process_lead(lead_data)
        self.assertEqual(result, {'message': 'New lead created and assigned', 'assigned_to': 'Test Agent'})
        self.lead_repo_mock.create.assert_called_once()
        self.notification_service_mock.send.assert_called_once_with(1, "New lead assigned: Test Lead")
        self.lead_repo_mock.log_lead_process.assert_called_once_with(2, 1, 'Lead assigned successfully')

    def test_should_return_true_when_email_is_valid(self):
        self.assertTrue(LeadService.is_valid_email("test@example.com"))

    def test_should_return_false_when_email_is_invalid(self):
        self.assertFalse(LeadService.is_valid_email("invalid-email"))
        self.assertFalse(LeadService.is_valid_email(None))
        self.assertFalse(LeadService.is_valid_email(""))

    def test_should_return_true_when_phone_is_valid(self):
        self.assertTrue(LeadService.is_valid_phone("+1234567890"))
        self.assertTrue(LeadService.is_valid_phone("1234567"))
        self.assertTrue(LeadService.is_valid_phone("123456789012345"))

    def test_should_return_false_when_phone_is_invalid(self):
        self.assertFalse(LeadService.is_valid_phone("invalid-phone"))
        self.assertFalse(LeadService.is_valid_phone(None))
        self.assertFalse(LeadService.is_valid_phone(""))
        self.assertFalse(LeadService.is_valid_phone("+1234567890a"))

    def test_should_return_default_region_when_location_is_any(self):
        self.assertEqual(LeadService.determine_region("any location"), "default-region")

    def test_should_create_lead_with_region_when_location_is_provided(self):
        lead_data = {'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890', 'location': 'Test Location'}
        self.lead_repo_mock.find_by_email_or_phone.return_value = None
        sales_agent = {'id': 1, 'name': 'Test Agent'}
        self.sales_agent_repo_mock.get_best_available_agent.return_value = sales_agent
        new_lead = {'id': 2, 'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890', 'assigned_agent': 1, 'region': 'default-region'}
        self.lead_repo_mock.create.return_value = new_lead
        self.lead_service.process_lead(lead_data)
        self.lead_repo_mock.create.assert_called_once_with({'name': 'Test Lead', 'email': 'test@example.com', 'phone': '+1234567890', 'location': 'Test Location', 'region': 'default-region', 'assigned_agent': 1})

    def test_should_raise_exception_when_missing_contact_info(self):
        lead_data = {}
        with self.assertRaises(ValidationException) as context:
            self.lead_service.process_lead(lead_data)
        self.assertEqual(context.exception.messages, {'error': 'Lead must have email or phone number'})

    def test_should_raise_exception_when_email_and_phone_are_invalid(self):
        lead_data = {'email': 'invalid-email', 'phone': '123'}
        with self.assertRaises(ValidationException) as context:
            self.lead_service.process_lead(lead_data)
        self.assertEqual(context.exception.messages, {'error': 'Invalid email or phone format'})

    def test_should_create_and_assign_lead_when_no_location_provided(self):
        lead_data = {'email': 'test@example.com', 'phone': '+1234567890'}
        self.lead_repo_mock.find_by_email_or_phone.return_value = None
        self.sales_agent_repo_mock.get_best_available_agent.return_value = {'id': 2, 'name': 'Agent Smith'}
        self.lead_repo_mock.create.return_value = {'id': 3, 'name': 'Test Lead'}
        response = self.lead_service.process_lead(lead_data)
        self.lead_repo_mock.create.assert_called_once_with({
            'email': 'test@example.com',
            'phone': '+1234567890',
            'assigned_agent': 2
        })
        self.assertEqual(response, {'message': 'New lead created and assigned', 'assigned_to': 'Agent Smith'})

if __name__ == '__main__':
    unittest.main()