from django.contrib import admin

from api.models import Transaction, Item


class TransactionsInline(admin.TabularInline):
    model = Transaction
    fields = ('id', 'status', 'location')
    readonly_fields = ('id',)
    verbose_name_plural = 'Transactions'
    extra = 0


class ItemAdmin(admin.ModelAdmin):
    ordering = ['-updated_at']
    date_hierarchy = 'updated_at'
    object_update_readonly_fields = ('id', )
    inlines = [TransactionsInline]
    list_display = ('id', 'updated_at', 'amount', 'state')
    list_filter = ('state',)


class TransactionAdmin(admin.ModelAdmin):
    ordering = ['-updated_at']
    date_hierarchy = 'item__updated_at'
    list_display = ('id', 'updated_at', 'item', 'status', 'location')
    list_editable = ('item',)
    list_select_related = ('item', )
    list_filter = ('status', 'location', 'item__state')


admin.site.register(Item, ItemAdmin)
admin.site.register(Transaction, TransactionAdmin)
