from auths.models import Permission


def default_perms():
    perms = Permission.objects.all()
    filters = [
        {
            "app_label": "communication",
            "model": "attachment"
        },
        {
            "app_label": "core",
            "model": "country"
        },
        {
            "app_label": "core",
            "model": "state"
        },
        {
            "app_label": "core",
            "model": "track"
        },
        {
            "app_label": "notifications",
            "model": "notification"
        },
        {
            "app_label": "process",
            "model": "templateconfig"
        },
        {
            "app_label": "recurrence",
            "model": "date"
        },
        {
            "app_label": "recurrence",
            "model": "param"
        },
        {
            "app_label": "recurrence",
            "model": "recurrence"
        },
        {
            "app_label": "recurrence",
            "model": "rule"
        },
        {
            "app_label": "reversion",
            "model": "revision"
        },
        {
            "app_label": "reversion",
            "model": "version"
        },
        {
            "app_label": "timer_api",
            "model": "calendar"
        },
        {
            "app_label": "timer_api",
            "model": "calendarapi"
        },
        {
            "app_label": "timer_api",
            "model": "calendarcredentials"
        },
        {
            "app_label": "timer_api",
            "model": "calendarrelation"
        },
        {
            "app_label": "timer_api",
            "model": "eventrelation"
        },
        {
            "app_label": "timer_api",
            "model": "category"
        },
        {
            "app_label": "timer_api",
            "model": "event"
        },
        {
            "app_label": "timer_api",
            "model": "occurrence"
        },
        {
            "app_label": "timer_api",
            "model": "rule"
        }
    ]
    output = []

    for perm in perms:
        for item in filters:
            if perm.content_type.app_label == item['app_label'] and perm.content_type.model == item['model']:
                output.append(perm)
                break

    return output
