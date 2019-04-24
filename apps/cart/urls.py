from django.conf.urls import url
from apps.cart.views import CartAddView, CartInfoView

urlpatterns = [
    url('^add$', CartAddView.as_view(), name='add'),
    url('^$', CartInfoView.as_view(), name='show'),
]
