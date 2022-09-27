from django.urls import path
from form_generator.views import FormGeneratorView, FormResponseView


urlpatterns = [
    path('form/<int:pk>/', FormGeneratorView.as_view(), name="form_detail"),
    path('form-response/<int:pk>/', FormResponseView.as_view(), name="form_response"),
]
