from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_food_nutrition, name='get_food_nutrition'),
]
