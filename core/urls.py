from django.urls import path
from core.views import FormGeneratorView, home_page, FormResponseView


urlpatterns = [
    path('form/<int:pk>/', FormGeneratorView.as_view(), name="form_detail"),
    path('form-response/<int:pk>/', FormResponseView.as_view(), name="form_response"),
    path('home/', home_page, name="home_page")
]
