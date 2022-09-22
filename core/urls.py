from django.urls import path
from core.views import FormGeneratorView, home_page


urlpatterns = [
    path('form/<int:pk>/', FormGeneratorView.as_view(), name="form_detail"),
    path('home/', home_page, name="home_page")
]
