# ViewSets define the view behavior.
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import Item, Transaction


class ItemSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.UUIDField(required=False, read_only=True)

    class Meta:
        model = Item
        fields = ['id', 'created_at', 'updated_at', 'amount', 'state']
        read_only_fields = ['id', 'created_at', 'updated_at', 'state']


class TransactionSerializer(serializers.HyperlinkedModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())

    class Meta:
        model = Transaction
        fields = ['id', 'created_at', 'updated_at', 'item', 'status', 'location']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItemView(viewsets.ModelViewSet):
    lookup_field = 'id'
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    @action(methods=['post'], detail=True)
    def move(self, request, *args, **kwargs):
        """
        Given the primary key of the item, we query the latest transaction, than create a new transaction
        based on it's next state.  Note: by saving the transaction, the item state will be updated as well.
        :param request: The Request object
        :param args: Arguments
        :param kwargs: Key word arguments
        :return: Response
        """
        trans = Transaction.get_active_transaction(kwargs['id'])
        return self.move_transaction(trans)

    @action(methods=['post'], detail=True)
    def error(self, request, *args, **kwargs):
        """
        Create an error transaction if the latest transaction is being processed and it's location is 'routable'
        :param request: The Request object
        :param args: Arguments
        :param kwargs: Key word arguments
        :return: Response
        """
        trans = Transaction.get_active_transaction(kwargs['id'])
        if trans.status != Transaction.STATUS_PROCESSING or trans.location != Transaction.LOCATION_ROUTABLE:
            return Response(data={
                "status": "error",
                "details": "Transactions not in correct state: [{}, {}]".format(trans.status, trans.location)
            }, status=status.HTTP_400_BAD_REQUEST)
        trans.item.error()
        return Response(self.get_serializer(trans.item).data)

    @action(methods=['post'], detail=True)
    def fix(self, request, *args, **kwargs):
        """
        Create an 'fix' transaction if the latest transaction is an error and it's location is 'routable'
        :param request: The Request object
        :param args: Arguments
        :param kwargs: Key word arguments
        :return: Response
        """
        trans: Transaction = Transaction.get_active_transaction(kwargs['id'])
        if trans.status != Transaction.STATUS_ERROR or trans.location != Transaction.LOCATION_ROUTABLE:
            return Response(data={
                "status": "error",
                "details": "Transactions not in correct state: [{}, {}]".format(trans.status, trans.location)
            }, status=status.HTTP_400_BAD_REQUEST)

        trans.item.fix()
        return Response(self.get_serializer(trans.item).data)

    def move_transaction(self, trans: Transaction) -> Response:
        """
        Gets the next transaction in the state chain, and saves it.  Returns an error response object if not
        in the correct status or locations (see status chart)
        :param trans: Transaction
        :return: Response
        """
        next_trans = trans.get_next_transaction_from_state()
        if next_trans:
            return Response(self.get_serializer(next_trans.item).data)
        else:
            return Response(data={
                "status": "error",
                "details": "Transactions already in finished state"
            }, status=status.HTTP_400_BAD_REQUEST)


class TransactionView(viewsets.ModelViewSet):
    lookup_field = u'id'
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
