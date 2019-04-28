from django.conf.urls import url
from apps.order.views import OrderPlaceView

urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'),
]
