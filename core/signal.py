from pprint import pprint
from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django import forms
from django.dispatch import receiver
from core.models import *
from django.db.models import Q
from django.core.cache import cache
from notifications.signals import notify

# notify.send(actor, recipient, verb, action_object, target, level, description, public, timestamp, **kwargs)
# https://docs.djangoproject.com/en/4.0/ref/signals/#m2m-changed

UserModel = get_user_model()

@receiver(pre_save, sender=Company)
def pre_save_company(sender, instance, raw, **kwargs):
    print(">>>>>>>>> pre_save_company()")
    # print(' ---- Start: ', instance.start_date)
    # if instance.created is None: # new object will be created
    #     pass # write your code here
    # else:
    #     keys = cache.keys(f'project_{instance.id}_*')
    #     x = 1
    #     if len(keys) > 0:
    #         keys.sort()
    #         x = int(re.findall(r"(\d+$)", keys.pop())[0]) + 1
    #     old = Company.objects.get(id=instance.id)
    #     cache.set(f"project_{instance.id}_{x}", {"status": old.status, "start_date": old.start_date, "end_date": old.end_date}, timeout=30)

    
@receiver(post_save, sender=Company)
def post_save_company(sender, instance, created, **kwargs):
    print(">>>>>>>>> post_save_company()")
    
    if created:
        if instance.administrator is not None:
            if instance.administrator.company is None:
                instance.administrator.company = instance
                instance.administrator.save()
            elif instance.administrator.company.id != instance.id:
                raise forms.ValidationError(f'User {instance} is already an existing memeber of a different Company')

# @receiver(pre_save, sender=Profile)
# def pre_save_profile(sender, instance: Profile, raw, **kwargs):
#     print(">>>>>>>>> pre_save_profile()")


# @receiver(post_save, sender=Profile)
# def post_save_profile(sender, instance, created, **kwargs):
#     print(">>>>>>>>> post_save_profile()")


# @receiver(pre_save, sender=Project)
# def pre_save_project(sender, instance: Project, raw, **kwargs):
#     print(">>>>>>>>> pre_save_project()")
#     print(' ---- Start: ', instance.start_date)
#     if instance.created is None: # new object will be created
#         pass # write your code here
#     else:
#         keys = cache.keys(f'project_{instance.id}_*')
#         x = 1
#         if len(keys) > 0:
#             keys.sort()
#             x = int(re.findall(r"(\d+$)", keys.pop())[0]) + 1
#         old = Project.objects.get(id=instance.id)
#         cache.set(f"project_{instance.id}_{x}", {"status": old.status, "start_date": old.start_date, "end_date": old.end_date}, timeout=30)


