from django.contrib import admin, messages
from django_object_actions import DjangoObjectActions

from api.models import Transaction, Item


class TransactionsInline(admin.TabularInline):
    model = Transaction
    ordering = ['-updated_at']
    date_hierarchy = 'updated_at'
    fields = ('updated_at', 'id', 'status', 'location')
    readonly_fields = ('updated_at', 'id',)
    verbose_name_plural = 'Transactions'
    extra = 0


class ItemAdmin(DjangoObjectActions, admin.ModelAdmin):
    ordering = ['-updated_at']
    date_hierarchy = 'updated_at'
    object_update_readonly_fields = ('id', )
    inlines = [TransactionsInline]
    list_display = ('id', 'updated_at', 'amount', 'state')
    list_filter = ('state',)

    def refund(self, request, obj):
        """
        Refund a payment that is in error

        :param request: The request
        :param obj: The Item in question
        :return: None
        """
        trans = Transaction.get_active_transaction(obj.id)
        if trans.status != Transaction.STATUS_ERROR:
            self.message_user(
                request,
                "The active transaction for item {} is not in an error state and cannot be refunded".format(obj.id),
                level=messages.ERROR)
        else:
            obj.refund()

    def refund_many(self, request, queryset):
        """
        Refund payments from the list field of payments (Items)
        :param request: The request
        :param queryset: The queryset
        :return: None
        """
        for item in queryset.all():
            self.refund(request, item)

    refund.label = "Refund"  # optional
    refund.short_description = "Refund item"  # optional

    change_actions = ('refund', )
    changelist_actions = ('refund_many', )


class TransactionAdmin(admin.ModelAdmin):
    ordering = ['-updated_at']
    date_hierarchy = 'item__updated_at'
    list_display = ('id', 'updated_at', 'item', 'status', 'location')
    list_editable = ('item',)
    list_select_related = ('item', )
    list_filter = ('status', 'location', 'item__state')


admin.site.register(Item, ItemAdmin)
admin.site.register(Transaction, TransactionAdmin)
