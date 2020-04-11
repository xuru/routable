from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import ItemView, TransactionView

# Create a router and register our viewsets with it.
router = DefaultRouter(trailing_slash=False)
router.register(r'items', ItemView, 'item')
router.register(r'transactions', TransactionView, 'transaction')


urlpatterns = [
    path('', include(router.urls)),
]
