from django.contrib.auth import get_user_model
from django.test import TestCase

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
