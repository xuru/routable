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
    state = models.CharField(default=STATE_PROCESSING, max_length=32, choices=STATE_CHOICES, help_text='The state of the payment')

    # There would also be originating bank ForeignKey, destination bank ForeignKey, etc...

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

    STATUS_CHOICES = (
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ERROR, 'Error')
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

    def get_next_transaction_from_state(self, default_to_success=True):
        """
        Return a new transaction in the next state and location.  If default_to_success is true, it will end in a completed
        status, or error if default_to_success is false.
        :param default_to_success: Whether or not to end in success or failure if at the end of the state chain.
        :return: Transaction
        """
        if self.status == self.STATUS_PROCESSING and self.location == self.LOCATION_ORIGIN:
            return Transaction(item=self.item, status=self.STATUS_PROCESSING, location=self.LOCATION_ROUTABLE)
        elif self.status == self.STATUS_PROCESSING and self.location == self.LOCATION_ROUTABLE:
            if default_to_success is True:
                return Transaction(item=self.item, status=self.STATUS_COMPLETED, location=self.LOCATION_DESTINATION)
            else:
                return Transaction(item=self.item, status=self.STATUS_ERROR, location=self.LOCATION_ROUTABLE)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        Saves the transaction, but also updates the associated item's state.

        :param force_insert:
        :param force_update:
        :param using:
        :param update_fields:
        :return:
        """
        if self.status == self.STATUS_COMPLETED:
            self.item.update_state(Item.STATE_RESOLVED)

        elif self.status == self.STATUS_ERROR:
            self.item.update_state(Item.STATE_ERROR)

        elif self.status == self.STATUS_PROCESSING:
            if self.item.state == Item.STATE_ERROR:
                self.item.update_state(Item.STATE_CORRECTING)

        super().save(force_insert, force_update, using, update_fields)

    def __unicode__(self):
        return u'{}: {} status: {}, location: {}'.format(self.id, self.item, self.status, self.location)
