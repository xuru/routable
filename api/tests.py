from django.urls import reverse, path, include
from rest_framework import status as rest_status
from rest_framework.test import APITestCase, URLPatternsTestCase

from api.models import Item, Transaction


class RoutableAPITestCase(APITestCase, URLPatternsTestCase):
    """Test the Routable API

    Could be improved to be a generic test for all APIs
    """
    urlpatterns = [
        path('api/', include('api.urls')),
    ]

    def setUp(self) -> None:
        #     Item.objects.all().delete()
        #     Transaction.objects.all().delete()
        self.item = Item(amount=12000.0)
        self.item.save()

    def new_transaction(self, status=Transaction.STATUS_PROCESSING, location=Transaction.LOCATION_ORIGIN):
        trans = Transaction(
            item=self.item,
            status=status,
            location=location
        )
        trans.save()
        return trans

    def get_latest_transaction(self):
        return Transaction.objects.select_related().filter(
            item__id=self.item.id).order_by('-updated_at')[0]

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

        url = reverse('item-move', args=[self.item.id])

        # first move, moves it from originator to routable
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '12000.00')
        self.assertEqual(response.data['state'], Item.STATE_PROCESSING)

        trans = self.get_latest_transaction()
        self.assertEqual(trans.status, Transaction.STATUS_PROCESSING)
        self.assertEqual(trans.location, Transaction.LOCATION_ROUTABLE)

        # second move, moves it from routable to destination
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '12000.00')
        self.assertEqual(response.data['state'], Item.STATE_RESOLVED)

        trans = self.get_latest_transaction()
        self.assertEqual(trans.status, Transaction.STATUS_COMPLETED)
        self.assertEqual(trans.location, Transaction.LOCATION_DESTINATION)

    def test_item_move_completed(self):
        self.new_transaction(
            status=Transaction.STATUS_COMPLETED,
            location=Transaction.LOCATION_DESTINATION
        )

        url = reverse('item-move', args=[self.item.id])

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
        self.assertEqual(response.data['details'], "Transactions already in finished state")

    def test_item_error(self):
        self.new_transaction()

        url = reverse('item-move', args=[self.item.id])

        # first move, moves it from originator to routable
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '12000.00')
        self.assertEqual(response.data['state'], Item.STATE_PROCESSING)

        trans = self.get_latest_transaction()
        self.assertEqual(trans.status, Transaction.STATUS_PROCESSING)
        self.assertEqual(trans.location, Transaction.LOCATION_ROUTABLE)

        # now move it to error
        url = reverse('item-error', args=[self.item.id])

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '12000.00')
        self.assertEqual(response.data['state'], Item.STATE_ERROR)

        trans = self.get_latest_transaction()
        self.assertEqual(trans.status, Transaction.STATUS_ERROR)
        self.assertEqual(trans.location, Transaction.LOCATION_ROUTABLE)


class TransactionTestCase(APITestCase, URLPatternsTestCase):
    """Test the Routable API

    Could be improved to be a generic test for all APIs
    """
    urlpatterns = [
        path('api/', include('api.urls')),
    ]

    def setUp(self) -> None:
        #     Item.objects.all().delete()
        #     Transaction.objects.all().delete()
        self.item = Item(amount=12000.0)
        self.item.save()

    def new_transaction(self, status=Transaction.STATUS_PROCESSING, location=Transaction.LOCATION_ORIGIN):
        trans = Transaction(
            item=self.item,
            status=status,
            location=location
        )
        trans.save()
        return trans

    def get_latest_transaction(self):
        return Transaction.objects.select_related().filter(
            item__id=self.item.id).order_by('-updated_at')[0]

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
