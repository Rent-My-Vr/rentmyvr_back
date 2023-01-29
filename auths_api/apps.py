from django.apps import AppConfig


class AuthsApiConfig(AppConfig):
    name = 'auths_api'

    verbose_name = "Auths API"


    def ready(self):
        import auths_api.signal # noqa
