from django.urls import include, path, reverse
from rest_framework import status as rest_status
from rest_framework.test import APITestCase, URLPatternsTestCase

from api.models import Item, Transaction


class APIBaseTestCase(APITestCase, URLPatternsTestCase):
    """Test the Routable API

    Could be improved to be a generic test for all APIs
    """
    urlpatterns = [
        path('api/', include('api.urls')),
    ]

    def setUp(self) -> None:
        self.amount = 12000.0
        self.item = Item(amount=self.amount)
        self.item.save()

    def new_transaction(self, status=Transaction.STATUS_PROCESSING, location=Transaction.LOCATION_ORIGIN):
        """
        Create and save a new transaction with the class's item instance.
        :param status: The Desired status
        :param location: The Desired location
        :return: The new instance of Transaction
        """
        trans = Transaction(
            item=self.item,
            status=status,
            location=location
        )
        trans.save()
        return trans

    def get_latest_transaction(self):
        """
        Retrieves the latest transaction for the item.
        :return: Transaction
        """
        return Transaction.objects.select_related().filter(
            item__id=self.item.id).order_by('-updated_at')[0]

    def assertTransaction(self, transaction, status, location, msg=None):
        """
        Helper assertion method to check a transaction's status and location
        :param transaction: The transaction
        :param status: Expected status
        :param location: Expected location
        :param msg: Any message you would like to add
        :return: None
        """
        if transaction.status != status or transaction.location != location:
            msg = self._formatMessage(msg, 'Transaction in wrong status or location: {} {}, expected: {} {}'.format(
                transaction.status, transaction.location, status, location
            ))
            raise self.failureException(msg)

    def call_item_endpoint(self, name, response_code_expected=rest_status.HTTP_200_OK):
        """
        Call an endpoint by it's name, then assert the expected response code.
        :param name: Name of the endpoint
        :param response_code_expected: The expected response code
        :return: The response data
        """
        url = reverse(name, args=[self.item.id])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, response_code_expected)
        return response.data

    def call_move_endpoint(self, expected_state=Item.STATE_PROCESSING):
        """
        Calls the move endpoint and than asserts that the state is what was expected
        :param expected_state: The expected state of the Item
        :return: The response data
        """
        data = self.call_item_endpoint('item-move')
        self.assertEqual(float(data['amount']), self.item.amount)
        self.assertEqual(data['state'], expected_state)
        return data

    def call_error_endpoint(self, expected_state=Item.STATE_ERROR):
        """
        Calls the error endpoint and than asserts that the state is what was expected
        :param expected_state: The expected state of the Item
        :return: The response data
        """
        data = self.call_item_endpoint('item-error')
        self.assertEqual(float(data['amount']), self.item.amount)
        self.assertEqual(data['state'], expected_state)
        return data

    def call_fix_endpoint(self, expected_state=Item.STATE_CORRECTING):
        """
        Calls the fix endpoint and than asserts that the state is what was expected
        :param expected_state: The expected state of the Item
        :return: The response data
        """
        data = self.call_item_endpoint('item-fix')
        self.assertEqual(float(data['amount']), self.item.amount)
        self.assertEqual(data['state'], expected_state)
        return data


class RoutableAPITestCase(APIBaseTestCase):

    def test_item_create(self):
        """
        Ensure we can create a new item object.
        """
        Item.objects.all().delete()

        url = reverse('item-list')
        data = {'amount': 12100.0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_201_CREATED)
        self.assertEqual(Item.objects.count(), 1)
        self.assertEqual(Item.objects.get().amount, 12100.0)

    def test_item_list(self):
        url = reverse('item-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['amount'], '12000.00')
        self.assertEqual(response.data[0]['state'], 'processing')

    def test_item_get(self):
        url = reverse('item-detail', args=[self.item.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '12000.00')
        self.assertEqual(response.data['state'], 'processing')

    def test_item_state_change(self):
        self.new_transaction(
            status=Transaction.STATUS_COMPLETED,
            location=Transaction.LOCATION_DESTINATION
        )
        item = Item.objects.get(id=self.item.id)
        self.assertEqual(item.state, Item.STATE_RESOLVED)

    def test_item_move(self):
        self.new_transaction()

        # first move, moves it from originator to routable
        self.call_move_endpoint(expected_state=Item.STATE_PROCESSING)

        # make sure the transaction is correct
        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_PROCESSING, Transaction.LOCATION_ROUTABLE)

        # second move, moves it from routable to destination
        self.call_move_endpoint(expected_state=Item.STATE_RESOLVED)

        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_COMPLETED, Transaction.LOCATION_DESTINATION)

    def test_item_move_completed(self):
        self.new_transaction(
            status=Transaction.STATUS_COMPLETED,
            location=Transaction.LOCATION_DESTINATION
        )

        item_dict = self.call_item_endpoint('item-move', response_code_expected=rest_status.HTTP_400_BAD_REQUEST)
        self.assertEqual(item_dict['status'], 'error')
        self.assertEqual(item_dict['details'], "Transactions already in finished state")

    def test_item_error(self):
        self.new_transaction()

        self.call_move_endpoint(expected_state=Item.STATE_PROCESSING)
        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_PROCESSING, Transaction.LOCATION_ROUTABLE)

        # now move it to error
        self.call_error_endpoint(expected_state=Item.STATE_ERROR)
        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_ERROR, Transaction.LOCATION_ROUTABLE)

    def test_item_error_completed(self):
        self.new_transaction(
            status=Transaction.STATUS_ERROR,
            location=Transaction.LOCATION_ROUTABLE
        )

        item_dict = self.call_item_endpoint('item-move', response_code_expected=rest_status.HTTP_400_BAD_REQUEST)
        self.assertEqual(item_dict['status'], 'error')
        self.assertEqual(item_dict['details'], "Transactions already in finished state")

    def test_item_fix(self):
        self.new_transaction(status=Transaction.STATUS_ERROR, location=Transaction.LOCATION_ROUTABLE)

        # Item is in error, so calling fix endpoint, should put it in to "correcting" status
        self.call_fix_endpoint(expected_state=Item.STATE_CORRECTING)
        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_FIXING, Transaction.LOCATION_ROUTABLE)

        # calling move item now should re-submit it
        self.call_move_endpoint(expected_state=Item.STATE_CORRECTING)
        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_PROCESSING, Transaction.LOCATION_ROUTABLE)

    def test_item_refund(self):
        trans = self.new_transaction(status=Transaction.STATUS_ERROR, location=Transaction.LOCATION_ROUTABLE)

        # Item is in error, so calling refund on the item, should put it in to "refunding" status
        trans.item.refund()
        self.assertEqual(trans.item.state, Item.STATE_CORRECTING)

        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_REFUNDING, Transaction.LOCATION_ROUTABLE)

        # calling move item now should refund it to the originator
        self.call_move_endpoint(expected_state=Item.STATE_RESOLVED)

        trans = self.get_latest_transaction()
        self.assertTransaction(trans, Transaction.STATUS_REFUNDED, Transaction.LOCATION_ORIGIN)

    def test_item_refunded_completed(self):
        self.new_transaction(
            status=Transaction.STATUS_REFUNDED,
            location=Transaction.LOCATION_ORIGIN
        )

        item_dict = self.call_item_endpoint('item-move', response_code_expected=rest_status.HTTP_400_BAD_REQUEST)
        self.assertEqual(item_dict['status'], 'error')
        self.assertEqual(item_dict['details'], "Transactions already in finished state")


class TransactionTestCase(APIBaseTestCase):

    def test_transaction_create(self):
        """
        Ensure we can create a new item object.
        """
        url = reverse('transaction-list')
        data = {
            'item': self.item.id,
            'status': Transaction.STATUS_PROCESSING,
            'location': Transaction.LOCATION_ORIGIN
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_201_CREATED)
        self.assertEqual(Transaction.objects.count(), 1)
        trans = Transaction.objects.get()
        self.assertEqual(trans.status, Transaction.STATUS_PROCESSING)
        self.assertEqual(trans.location, Transaction.LOCATION_ORIGIN)
        self.assertEqual(trans.item.id, self.item.id)

    def test_transaction_list(self):
        self.new_transaction()

        url = reverse('transaction-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], Transaction.STATUS_PROCESSING)
        self.assertEqual(response.data[0]['location'], Transaction.LOCATION_ORIGIN)

    def test_transaction_get(self):
        trans = self.new_transaction()

        url = reverse('transaction-detail', args=[trans.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Transaction.STATUS_PROCESSING)
        self.assertEqual(response.data['location'], Transaction.LOCATION_ORIGIN)
