
# Django Form Generator

django form generator will help you create forms very easily.
you can use it any where in your html files.

there is an API-manager tool for you to call some APIs on loading form or after submit.

---
## Installation
---
- install it via pip:
  
  ```bash
  pip install django-form-generator
  ```

- add (`'django_form_generator'`, `'django_htmx'`, `'crispy_forms'`, `'crispy_bootstrap5'`, `'captcha'`, `'tempus_dominus', 'rest_framework', 'drf_recaptcha'`) to your `INSTALLED_APPS`:
  ```python
  INSTALLED_APPS = [
      ...
      'django_htmx',
      'crispy_forms',
      'crispy_bootstrap5',
      'captcha',
      'tempus_dominus',
      'rest_framework',
      'drf_recaptcha',
      'django_form_generator',
  ]
  ```

- do a `migrate`:
  
  ```bash
  python manage.py migrate
  ```

- do a `collectstatic`:
  
  ```bash
  python manage.py collectstatic
  ```

- finally include django_form_generator urls to your `urls.py`
  ```python

  from django.contrib import admin
  from django.urls import path, include

  urlpatterns = [
    path('admin/', admin.site.urls),
    ...
    path('form-generator/', include(('django_form_generator.urls', 'django_form_generator'), namespace='django_form_generator')),
    ...
  ]
  ```
  

---
## Requirements
---
* Python >= 3.10
* Django >= 4.0


---
## Form Usage
---

- ### regular html usage:
  ```html
  <!doctype html>
  <html lang="en">
  <head>
  ...
  </head>

  <body>
      {% load django_form_generator %}

      {% render_form 1 %} {# it will render the form that has id of 1 #}

  </body>

  </html>
  ```


- ### RichText fields:
  ***To use this tags on a Richtext field like `CKeditor` or `tinymce`.***

  >Note: In some richtext packages some elements (specialy jinja elements) will be removed from the field
  there are some tweaks to solve this problems on the packages documentations.

  - #### Admin panel:
    *CK-Editor example*
     ![Shows an example usage on ck-editor](https://raw.githubusercontent.com/m3h-D/Form-Generator/release/django_form_generator/docs/images/ckEditor.png)


  - ```./app_name/templates/index.html ```

    ```html
    <!doctype html>
    <html lang="en">
    <head>
    ...
    </head>

    <body>
        {% load django_form_generator %}

        {{ object.rich_text_field|eval_data }}

    </body>

    </html>
    ```

---
## API manager Usage
---
**There is also an API manager for the forms**

- ### Admin panel:

  - **example:**
    >Note: `first_name`, `last_name` and `job` are the name of the fields that are defined in a form which this api is assigned to.

    ![create a body with the fields name of a form](https://raw.githubusercontent.com/m3h-D/Form-Generator/release/django_form_generator/docs/images/apiManagerCreateUser.png)


---

>***Note: assigend apis will be called automatically.
the ones with execution_time of `PRE` will be called when form renders.
and the ones with execution_time of `POST` will be called after form submition.***


>***Note: in the response field you can write HTML tags 
>it will be rendrend as `safe`***.

>***Note: You have access to `request` globaly in api manager***

***Also you have access to the response of the api. so you can use `Jinja` syntax to access data.
You can use this feature on the (`url`, `body`, `response`) fields of `APIManager` model***

- ### Creating API
    - **example:**
  
    
    ![get response of an API](https://raw.githubusercontent.com/m3h-D/Form-Generator/release/django_form_generator/docs/images/apiManagerGetUser.png)
    
    >Note: To show the response use the template tag of `{% render_pre_api form_id api_id %}` inside your html file that the `form` is there.


- ### Response
  example:
  - output of the api:
    ```json
    {
      "result": [
        {
        "first_name": "john",
        "last_name": "doe",
        "avatar": "https://www.example.com/img/john-doe.png",
        },
        {
        "first_name": "mary",
        "last_name": "doe",
        "avatar": "https://www.example.com/img/mary-doe.png",
        }
      ]
    }
    ```

  - in the response field you can do:
    ```html
    <h1> Response of the API: </h1>
    {% for item in result %}

      <p>{{item.first_name}}</p>
      <p>{{item.last_name}}</p>
      <img src="{{item.avatar}}">

    {% endfor %}

    ```

- ### html usage:
  ```html
  <!doctype html>
  <html lang="en">
  <head>
  ...
  </head>

  <body>
      {% load django_form_generator %}

      {% render_pre_api 1 %} {# it will render all pre apis that are assigned to a form with id of 1 #}

      {% render_pre_api 1 6 %} {# it will render the pre api with id of 6 which is assigned to a form with id of 1 #}


      {% render_post_api 1 %} {# it will render all pre apis that are assigned to a form with id of 1 #}

      {% render_post_api 1 7 %} {# it will render the post api with id of 7 which is assigned to a form with id of 1 #}

  </body>

  </html>
  ```


---
## Extra
---
- ### API Manager:
  
  you can access the whole submited data by adding `{{ form_data }}` to your api `body`.


- ### Form Style:
  to have multiple styles the html of `template_name_p` (attribute of django.forms.Form) will be replace by our html file. (`{{form.as_p}}`)

  there are 3 styles(or actualy styel of rendering fields) for the forms:
    1. In-line Style[^1].

    2. In-order Style[^2].

    3. Dynamic Style[^3].
   
    [^1]: In every line two fields will be rendered.

    [^2]: In every line one field will be rendered.

    [^3]: this style will render fields respect to the field position (`inline`, `inorder`, `break`)
  

  >Note: If you want to render two fields `inline` and one field `inorder` you should use `break` for the second field 

    - example:
        - field1 inline
        - field2 break
        - field3 inorder 

  
  >Note: You can add your custom styles by create new TextChoices object and add it to `settings.py`
  
    - example:
      1. *myapp/const.py*
          ```python
          from django.db.models import TextChoices

          class CustomFormGeneratorStyle(TextChoices):
            MY_STYLE = "myapp/templates/my_style.html", 'My Custom Style'
            ...

          ```
      2. *myproject/settings.py*
          ```python
            DJANGO_FORM_GENERATOR = {
              "FORM_STYLE_CHOICES": "myapp.const.CustomFormGeneratorStyle"
            }
          ```

        

- ### URLS:
  ```python
  # to access the form you can call this url:
  """GET: http://127.0.0.1:8000/form-generator/form/1/"""
  #or 
  reverse('django_form_generator:form_detail', kwargs={'pk': 1})
  #api:
  reverse('django_form_generator:api_form_detail', kwargs={'pk': 1})


  # to access the response of the form you can call this url the kwarg_lookup is UUID field
  """GET: http://127.0.0.1:8000/form-generator/form-response/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/"""
  #or
  reverse('django_form_generator:form_response', kwargs={'unique_id': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'})
  #api:
  reverse('django_form_generator:api_form_response', kwargs={'unique_id': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'})

  ```

- ### Settings:
  **below is the default settings for django_form_generator. you can change them by adding it to your `settings.py`**
  ```python
      DJANGO_FORM_GENERATOR = {
        'FORM_RESPONSE_SAVE': 'django_form_generator.models.save_form_response',
        'FORM_EVALUATIONS': {'form_data': '{{form_data}}'},
        'FORM_GENERATOR_FORM': 'django_form_generator.forms.FormGeneratorForm',
        'FORM_RESPONSE_FORM': 'django_form_generator.forms.FormGeneratorResponseForm',
        'FORM_STYLE_CHOICES': 'django_form_generator.const.FormStyle',
        'FORM_MANAGER': 'django_form_generator.managers.FormManager',
        'FORM_GENERATOR_SERIALIZER': 'django_form_generator.api.serializers.FormGeneratorSerializer',
        'FORM_RESPONSE_SERIALIZER': 'django_form_generator.api.serializers.FormGeneratorResponseSerializer',
      }
  ```

---
## Attention
---
**To have nice styled fields you can add crispy-form to your `settings.py`**

  ```python
    CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
    CRISPY_TEMPLATE_PACK = 'bootstrap5'
  ```

**To access google recaptcha you should add these to your `settings.py`**

>Note: you can have public & private keys by registring your domain on [Google recaptcha admin console](https://www.google.com/recaptcha/admin/create)

  ```python
    RECAPTCHA_PUBLIC_KEY = 'public_key'
    RECAPTCHA_PRIVATE_KEY = 'private_key'
    # ===== FOR DRF =========
    DRF_RECAPTCHA_SECRET_KEY = "YOUR SECRET KEY"
  ```


>Note: If you don't want to use google-recaptcha(`django-recaptcah`)
you should add below code to your `settings.py`

  ```python
  SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
  ```

---
## Dependency Packages
---
1. [HTMX](https://htmx.org/docs/)
2. [CRISPY-FORMS (crispy-bootstrap5)](https://github.com/django-crispy-forms/crispy-bootstrap5)
3. [REQUESTS](https://requests.readthedocs.io/en/latest/)
4. [DJANGO-RECAPTCHA](https://pypi.org/project/django-recaptcha/)
5. [DJANGO-TEMPUS-DOMINUS](https://github.com/FlipperPA/django-tempus-dominus)
6. [DJANGO-REST-FRAMEWORK](https://www.django-rest-framework.org/)

---
## License
---
[MIT](https://choosealicense.com/licenses/mit/)
