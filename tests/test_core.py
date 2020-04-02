from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase, RequestFactory, SimpleTestCase
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from unittest.mock import patch

from core import clone_instance


class CoreTest(TestCase):

    def test_clone_instance(self):
        # import locally because core app should not depend on other apps
        from document.models import Document
        from document.tests.factories import DocumentFactory
        from policy.models import Policyholder
        from policy.tests.factories import PolicyholderFactory

        User = get_user_model()

        # use policyholder as an example and we know the follow related
        # instances will be cloned as well
        doc = DocumentFactory.create()
        ph = PolicyholderFactory.create(identification_document=doc)

        self.assertEqual(Policyholder.objects.count(), 1)
        self.assertEqual(Identity.objects.count(), 1)
        self.assertEqual(Address.objects.count(), 2)  # residential & mailing
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)

        cloned_ph = clone_instance(ph)

        self.assertNotEqual(cloned_ph, ph)
        self.assertNotEqual(cloned_ph.identity, ph.identity)
        self.assertNotEqual(
            cloned_ph.residential_address,
            ph.residential_address,
        )
        self.assertNotEqual(
            cloned_ph.mailing_address,
            ph.mailing_address,
        )
        self.assertNotEqual(
            cloned_ph.identification_document,
            ph.identification_document,
        )
        self.assertEqual(
            cloned_ph.identification_document.user,
            ph.identification_document.user,
        )

        self.assertEqual(Policyholder.objects.count(), 2)
        self.assertEqual(Identity.objects.count(), 2)
        self.assertEqual(Address.objects.count(), 4)
        self.assertEqual(Document.objects.count(), 2)
        self.assertEqual(User.objects.count(), 1)  # never clone user


class TestCustomExceptionHandler(SimpleTestCase):
    def setUp(self):
        factory = RequestFactory()
        self.request = factory.get('/')

    @patch('core.logger', autospec=True)
    def test_normal_view(self, mock_logger):
        @api_view()
        @permission_classes([])
        def view(request):
            return Response('normal')

        response = view(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'normal')
        mock_logger.info.assert_not_called()

    @patch('core.logger', autospec=True)
    def test_known_exceptions(self, mock_logger):
        @api_view()
        @permission_classes([])
        def view(request):
            raise ValidationError('validation error')

        response = view(self.request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, ['validation error'])
        mock_logger.warning.assert_called_once()

    @patch('core.logger', autospec=True)
    def test_uncaught_does_not_exist(self, mock_logger):
        @api_view()
        @permission_classes([])
        def view(request):
            raise ObjectDoesNotExist('object does not exist')

        response = view(self.request)

        # should translate to 404 NotFound error
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {'detail': 'object does not exist'})
        mock_logger.error.assert_called_once()
