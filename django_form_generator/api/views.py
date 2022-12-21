from rest_framework.response import Response
from rest_framework import status

from django_form_generator.common.utils import get_client_ip
from django_form_generator.common.views import BaseAPIView
from django_form_generator.api.serializers import FormGeneratorResponseSerializer, FormGeneratorSerializer, FormSerializer, FormFullSerializer
from django_form_generator.models import Form
from django_form_generator.settings import form_generator_settings as fg_settings



class FormAPIView(BaseAPIView):
    serializer_class = FormSerializer
    queryset = Form.objects.filter_valid()
    model = Form

    def get(self, request, format=None):
        serializer_class = self.get_serializer_class(request)
        instance = self.get_queryset(request)
        serializer = serializer_class(instance, many=True)
        return Response(serializer.data)


class FormGeneratorAPIView(BaseAPIView):
    serializer_class = FormGeneratorSerializer
    queryset = Form.objects.filter_valid()
    model = Form
    lookup_field = 'pk'

    def get_serializer_class(self, request):
        return fg_settings.FORM_GENERATOR_SERIALIZER

    def get(self, request, pk, format=None):
        instance = self.get_object(pk)
        instance.call_pre_apis({"request": request})
        serializer = FormFullSerializer(instance=instance)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class(request)
        instance = self.get_object(kwargs['pk'])
        serializer = serializer_class(data=request.data, context={'request': request, 'form': instance, 'user_ip': get_client_ip(request)})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FormGeneratorResponseAPIView(BaseAPIView):
    serializer_class = FormGeneratorResponseSerializer
    queryset = fg_settings.FORM_GENERATOR_RESPONSE_MODEL.objects.all() #type: ignore
    model = fg_settings.FORM_GENERATOR_RESPONSE_MODEL
    lookup_field = 'unique_id'

    def get_serializer_class(self, request):
        return fg_settings.FORM_RESPONSE_SERIALIZER

    def get(self, request, unique_id, format=None):
        serializer_class = self.get_serializer_class(request)
        instance = self.get_object(unique_id)
        serializer = serializer_class(instance, context={'request': request, 'form': instance.form, 'form_response': instance})
        return Response(serializer.output_data)

    def patch(self, request, unique_id, format=None):
        serializer_class = self.get_serializer_class(request)
        instance = self.get_object(unique_id)
        serializer = serializer_class(instance.pure_data, data=request.data, partial=True, 
                context={'request': request, 'form': instance.form, 'form_response': instance})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
