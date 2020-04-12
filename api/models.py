import uuid

from django.db import models
from django.utils.timezone import now


class BaseModel(models.Model):
    """
    Base model that adds an id in UUID form, and a created and updated timestamp on the model
    """
    class Meta:
        abstract = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField('Created at', default=now)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields:
            update_fields = set(update_fields)
            update_fields.add('updated_at')
            kwargs['update_fields'] = update_fields
        super().save(*args, **kwargs)


class Item(BaseModel):
    """
    Store a payment
    """
    STATE_PROCESSING = "processing"
    STATE_CORRECTING = "correcting"
    STATE_ERROR = "error"
    STATE_RESOLVED = "resolved"

    STATE_CHOICES = (
        (STATE_PROCESSING, "First time processing"),
        (STATE_CORRECTING, "Unfinished correction"),
        (STATE_ERROR, "In error"),
        (STATE_RESOLVED, "Processing resolved"),
    )

    amount = models.DecimalField(max_digits=8, decimal_places=2)
    state = models.CharField(default=STATE_PROCESSING, max_length=32, choices=STATE_CHOICES,
                             help_text='The state of the payment')

    def refund(self):
        trans = Transaction(item=self, status=Transaction.STATUS_REFUNDING, location=Transaction.LOCATION_ROUTABLE)
        trans.save()
        return trans

    def fix(self):
        trans = Transaction(item=self, status=Transaction.STATUS_FIXING, location=Transaction.LOCATION_ROUTABLE)
        trans.save()
        return trans

    def error(self):
        trans = Transaction(item=self, status=Transaction.STATUS_ERROR, location=Transaction.LOCATION_ROUTABLE)
        trans.save()
        return trans

    def update_state(self, state):
        self.state = state
        self.save()

    def __unicode__(self):
        return u'{}: {}'.format(self.id, self.state)


class Transaction(BaseModel):
    """
    Store a transaction of an associated Item (payment)
    """
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_ERROR = 'error'
    STATUS_REFUNDING = 'refunding'
    STATUS_REFUNDED = 'refunded'
    STATUS_FIXING = 'fixing'

    STATUS_CHOICES = (
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ERROR, 'Error'),
        (STATUS_REFUNDING, 'Refunding'),
        (STATUS_REFUNDED, 'Refunded'),
        (STATUS_FIXING, 'Fixing')
    )

    LOCATION_ORIGIN = "origination_bank"
    LOCATION_ROUTABLE = "routable"
    LOCATION_DESTINATION = "destination_bank"

    LOCATION_CHOICES = (
        (LOCATION_ORIGIN, 'Origination Bank'),
        (LOCATION_ROUTABLE, 'Routable'),
        (LOCATION_DESTINATION, 'Destination Bank')
    )

    item = models.ForeignKey(Item, on_delete=models.CASCADE, verbose_name="The transactions payment")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, help_text='The status of the transaction')
    location = models.CharField(max_length=32, choices=LOCATION_CHOICES, help_text='The location of the transaction')

    @staticmethod
    def get_active_transaction(pk):
        return Transaction.objects.select_related().filter(item__id=pk).order_by('-updated_at')[0]

    def get_next_transaction_from_state(self, save_transaction=True):
        """
        Return a new transaction in the next automatic state and location. Please note that 'refund',
        'fix' and 'error' states are user initiated states and handled separately.

        :param save_transaction: Whether or not to save the transaction before returning it. Defaults to true.
        :return: Transaction
        """
        trans = None
        # The starting state of our transaction
        if self.status == self.STATUS_PROCESSING and self.location == self.LOCATION_ORIGIN:
            trans = Transaction(item=self.item, status=self.STATUS_PROCESSING, location=self.LOCATION_ROUTABLE)

        # If we are successful with the destination, put it in to a success status, else, error
        elif self.status == self.STATUS_PROCESSING and self.location == self.LOCATION_ROUTABLE:
            trans = Transaction(item=self.item, status=self.STATUS_COMPLETED, location=self.LOCATION_DESTINATION)

        # We are fixing this transaction, so move it back into processing so we can try again
        elif self.status == self.STATUS_FIXING and self.location == self.LOCATION_ROUTABLE:
            trans = Transaction(item=self.item, status=self.STATUS_PROCESSING, location=self.LOCATION_ROUTABLE)

        # We are refunding this transaction, so move it back to origin and mark it refunded
        elif self.status == self.STATUS_REFUNDING and self.location == self.LOCATION_ROUTABLE:
            trans = Transaction(item_id=self.item.id, status=self.STATUS_REFUNDED, location=self.LOCATION_ORIGIN)

        if trans and save_transaction is True:
            trans.save()
        return trans

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        Saves the transaction, but also updates the associated item's state.

        :param force_insert:
        :param force_update:
        :param using:
        :param update_fields:
        :return:
        """
        # transition item to resolved state
        if self.status in [self.STATUS_COMPLETED, self.STATUS_REFUNDED]:
            self.item.update_state(Item.STATE_RESOLVED)

        # transition item to error state
        elif self.status == self.STATUS_ERROR:
            self.item.update_state(Item.STATE_ERROR)

        # transition item from ERROR to CORRECTING
        elif self.status in [self.STATUS_PROCESSING, self.STATUS_REFUNDING, self.STATUS_FIXING] and \
                self.item.state == Item.STATE_ERROR:
            self.item.update_state(Item.STATE_CORRECTING)

        super().save(force_insert, force_update, using, update_fields)

    def __unicode__(self):
        return u'{}: {} status: {}, location: {}'.format(self.id, self.item, self.status, self.location)
