from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BlogApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog_api'
    verbose_name = _('blog_api')


