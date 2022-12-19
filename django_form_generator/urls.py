from django.urls import path, include
from django_form_generator.views import FormGeneratorView, FormResponseView


urlpatterns = [
    path('form/<int:pk>/', FormGeneratorView.as_view(), name="form_detail"),
    path('form-response/<uuid:unique_id>/', FormResponseView.as_view(), name="form_response"),
    path('api/', include(('django_form_generator.api.urls', 'django_form_generator'), 'api'))
]
