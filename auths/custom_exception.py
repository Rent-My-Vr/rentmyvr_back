

class PermissionRequired(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class CompanyRequired(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class ActivationRequired(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)