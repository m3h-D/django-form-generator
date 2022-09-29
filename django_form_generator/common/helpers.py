import os
import pathlib
from typing import Any
from django.conf import settings
from django_form_generator.common.utils import upload_file_handler

class FileFieldHelper:

    def __init__(self, url_path, directory_path):
        self.url_path = url_path
        self.directory_path = directory_path

    @property
    def url(self):
        return self.url_path

    @property
    def name(self):
        name = os.path.basename(self.directory_path)
        return name

    @classmethod
    def upload_file(cls, host: str, data: bool|Any, instance_directory: str|None=None):
        if isinstance(data, bool) and not data:
            if instance_directory is not None:
                pathlib.Path(instance_directory).unlink()
            return None
        directory = upload_file_handler(data)
        parts = pathlib.Path(directory).parts
        return {
            "directory": directory,
            "url": host + settings.MEDIA_URL + "/".join(parts[-2:]),
        }