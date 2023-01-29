import logging
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

UserModel = get_user_model()


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)


def test(request):
    for key, value in request.GET.items():
        log.warning('Key: {}  ::: Value: {}'.format(key, value))


# Create your views here.

def index(request):
    # template = "auths/user-form.html" 
    # return render(request, template, context={})


    return HttpResponse("This is Index") 


@login_required
def dashboard(request):
    # template = "auths/user-form.html" 
    # return render(request, template, context={})

    return HttpResponse("This is Dashboard") 

