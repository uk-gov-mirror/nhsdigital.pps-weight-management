from django.urls import path
from . import views
urlpatterns = [
    path("item", views.items, name="items"),
    path("item/<int:item_id>", views.item_detail, name="item_detail"),
]
