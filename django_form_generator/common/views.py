from rest_framework.views import APIView
from django.http import Http404


class BaseAPIView(APIView):
    serializer_class = ...
    queryset = ...
    model = ...
    lookup_field = ...

    def get_queryset(self, request=None):
        return self.queryset.all()
    
    def get_serializer_class(self, request):
        return self.serializer_class
    
    def get_object(self, arg):
        try:
            return self.get_queryset().get(**{self.lookup_field: arg})
        except self.model.DoesNotExist:
            raise Http404