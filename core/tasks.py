from __future__ import absolute_import, unicode_literals


import json
import logging
import subprocess
import icalendar
from icalevents.icalevents import events
from datetime import datetime, timezone, timedelta
from dateutil.tz import UTC, gettz
from smtplib import SMTPAuthenticationError
from django.core import mail
import jwt
import requests
from celery import shared_task
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail.backends.smtp import EmailBackend
from django.utils import timezone

from core.models import *
from schedule.models import *


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)

UserModel = get_user_model()

@shared_task
def add(x =2, y=3):
    return x + y


@shared_task(name='core.processPropertyEvents')
def processPropertyEvents(calendar_id = None, calendar_url = None):
    print('***********************************calendar_url :  ', calendar_url)
    LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
    NOW = datetime.now(LOCAL_TIMEZONE)
    MIDNIGHT = datetime(NOW.year, NOW.month, NOW.day, 0, 0, 0, 0, tzinfo=LOCAL_TIMEZONE)
    DATE_END = MIDNIGHT + timedelta(days=365)

    if calendar_id and calendar_url:
        calendar = Calendar.object.get(id=calendar_id)
        for e in events(url=calendar_url, end=DATE_END):
            event = Event()
            event.creator_id = settings.SYSTEM_USER_ID
            event.toSchedule(e)
            calendar.events.add(event)

@shared_task(name='core.sendMail')
def sendMail(subject, message, recipients, fail_silently=settings.DEBUG,
             connection=None, cc=None, bcc=None, files=None, use_signature=None, context_data=None):
    # send_gmail(user.cert, "Maintenance TS Account Activation", "body", to=user.email, cc=None, bcc=None, user=user)
        
        
    if isinstance(recipients, str):
        recipients = [recipients]

    log.info(f"To send mail to: {recipients}")
    log.info(f"Connection: {connection}\tContext Data: {context_data}")
    
    if connection is None:
        # log.warning(f"Try Again.... Result: {result}")
        connection = mail.get_connection()
        print("************************************************************************************")
        print(message)
        print("************************************************************************************")
        print(vars(connection))
        try:
            mail.send_mail(subject=subject, message=message, from_email=connection.username, connection=mail.get_connection(),
                    recipient_list=recipients, fail_silently=fail_silently, html_message=message)
            return {"msg": "Mail (%s) Sent to: [%s]" % (subject, ", ".join(recipients)), "id": ""}
        except SMTPAuthenticationError as err:
            log.error(f'Error Sending Email {subject} to: [{", ".join(recipients)}]')
            log.error(err)
            return {"msg": f'Error Sending Email {subject} to: [{", ".join(recipients)}]', "status": "error"}
    
    result = None
    if isinstance(connection, str):
        connection = UserModel.objects.filter((Q(email=connection) | Q(id=connection))).first()

    print('\n\n================ ************* ===================\n\n')
    print( message)
    if connection:
        from core.utils import send_gmail
        try:
            # send_gmail(cert, subject, body, to=None, cc=None, bcc=None, files=(), user=None, footer=None, context_data=None):
            result = send_gmail(connection.cert, subject, message, to=recipients, cc=cc, bcc=bcc, files=files)
            log.warning(f"********* Send Mail Result: {result}")
            if result and len(result.keys()) == 1 and len(result['msg']) > 1:
                result = None
        except Exception as e:
            result = None

