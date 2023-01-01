from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from django_form_generator.api import views

urlpatterns = [
    path('forms/', views.FormAPIView.as_view(), name="api_forms"),
    path('forms/<int:pk>/', views.FormGeneratorAPIView.as_view(), name="api_form_detail"),
    path('form-response/<uuid:unique_id>/', views.FormGeneratorResponseAPIView.as_view(), name="api_form_response"),
]

urlpatterns=format_suffix_patterns(urlpatterns)