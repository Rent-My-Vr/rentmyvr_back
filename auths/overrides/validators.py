from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class AvoidPreviousPasswords(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def validate(self, username, password):
        user = User.objects.get(username=username)
        if self.word_1 in password or self.word_2 in password:
            raise ValidationError(
                _(f"You cannot include '{self.word_1}' or '{self.word_2}' in your password."),
                code='Invalid password',
            )

    def get_help_text(self):
        return _(f"You cannot include '{self.word_1}' or '{self.word_2}' in your password.")