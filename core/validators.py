import os
from django.core.exceptions import ValidationError
MB = 1024 * 1024
def file_validator(exts, max_mb):
    def v(f):
        ext = os.path.splitext(f.name)[1].lower().lstrip(".")
        if ext not in exts:
            raise ValidationError(f"Ruxsat etilgan formatlar: {', '.join(exts)}.")
        if f.size > max_mb * MB:
            raise ValidationError(f"Fayl hajmi {max_mb} MB dan oshmasligi kerak.")
    return v
