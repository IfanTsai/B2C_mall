from django.conf.urls import url
from apps.cart.views import (
    CartAddView, CartInfoView, CartUpdateView, CartDeleteView,
)

urlpatterns = [
    url('^add$', CartAddView.as_view(), name='add'),
    url('^$', CartInfoView.as_view(), name='show'),
    url('^update$', CartUpdateView.as_view(), name='update'),
    url('^delete$', CartDeleteView.as_view(), name='delete'),
]
