from django.apps import AppConfig


class AuthsConfig(AppConfig):
    name = 'auths'

    verbose_name = "Auths & Security"


    def ready(self):
        import auths.signal # noqa