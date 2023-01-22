from django import forms


class MultiInputWidgetField(forms.widgets.TextInput):
    allow_multiple_selected = True

    def format_value(self, value):
        if not value:
            return None
        if isinstance(value, (list, tuple)):
            return value

    def value_from_datadict(self, data, files, name):
        getter = data.get
        if self.allow_multiple_selected:
            try:
                getter = data.getlist
            except AttributeError:
                pass
        return getter(name)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.allow_multiple_selected:
            context["widget"]["attrs"]["multiple"] = True
        return context

class MultiInputField(forms.CharField):

    def to_python(self, value):
        if not value:
            return []
        elif not isinstance(value, (list, tuple)):
            raise forms.ValidationError(
                self.error_messages["invalid_list"], code="invalid_list"
            )
        return [str(val) for val in value if val]


class CustomeSelectFormField(forms.Select):
    option_inherits_attrs = True