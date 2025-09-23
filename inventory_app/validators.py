from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class ComplexPasswordValidator:
    def validate(self, password, user=None):
        if not any(char.isdigit() for char in password):
            raise ValidationError(_('La contraseña debe contener al menos un número.'))
        if not any(char.isupper() for char in password):
            raise ValidationError(_('La contraseña debe contener al menos una letra mayúscula.'))
        if not any(char.islower() for char in password):
            raise ValidationError(_('La contraseña debe contener al menos una letra minúscula.'))
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for char in password):
            raise ValidationError(_('La contraseña debe contener al menos un carácter especial.'))

    def get_help_text(self):
        return _(
            "Tu contraseña debe contener al menos 12 caracteres, "
            "incluyendo mayúsculas, minúsculas, números y caracteres especiales."
        )
