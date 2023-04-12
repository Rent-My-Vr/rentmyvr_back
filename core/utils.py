import email
import math
from email.message import Message
import logging
from base64 import urlsafe_b64encode
# from datetime import timedelta, datetime
# from email.mime.audio import MIMEAudio
# from email.mime.base import MIMEBase
# from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, datetime
# from email.mime.application import MIMEApplication

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError as GoogleHttpError

from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.template import Template, Context
from django.contrib.auth.tokens import PasswordResetTokenGenerator


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

SCOPES = ['https://www.googleapis.com/auth/gmail.compose', 
            'https://www.googleapis.com/auth/gmail.insert', 
            'https://www.googleapis.com/auth/gmail.readonly', 
            'https://www.googleapis.com/auth/gmail.send']
            

def distance_to_decimal_degrees(distance, latitude):
    """
    Source of formulae information:
        1. https://en.wikipedia.org/wiki/Decimal_degrees
        2. http://www.movable-type.co.uk/scripts/latlong.html
    :param distance: an instance of `from django.contrib.gis.measure.Distance`
    :param latitude: y - coordinate of a point/location
    """
    lat_radians = latitude * (math.pi / 180)
    # 1 longitudinal degree at the equator equal 111,319.5m equiv to 111.32km
    return distance.m / (111_319.5 * math.cos(lat_radians))


def date_to_json(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")


def credentials_to_dict(gmail, credentials):
    print(credentials.refresh_token)
    return {'email': gmail,
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': date_to_json(credentials.expiry)}


# From: https://github.com/googleapis/google-api-python-client/issues/325
class DiscoveryCache:

    def filename(self, url):
        return f'google_api_discovery_{url}'

    def get(self, url):
        cache.get(self.filename(url), None)

    def set(self, url, content):
        cache.set(self.filename(url), content, timeout=60*60*24)


def google_build_():
    flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES)
    flow.redirect_uri = 'https://softdongle.info:8002/accounts/social/google/login/callback/'
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    

def get_email(gmail):
    # what email did they use? (this is just an example of how to use the api - you can skip this part if you want)
    profile = gmail.users().getProfile(userId="me").execute()
    return profile['emailAddress']


def build_gmail(c):
    return build('gmail', 'v1', credentials=c, cache=DiscoveryCache())

   


def create_message(sender, subject, body, to=None, cc=None, bcc=None, files=()):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      message_text: The text of the email message.
      file: The directory containing the file to be attached.
      filename: The name of the file to be attached.

    Returns:
      An object containing a base64url encoded email object.
    """

    raw = {}
    message = MIMEMultipart()
    message['to'] = ', '.join(to) if isinstance(to, list) else to
    message['from'] = sender
    message['subject'] = subject

    message.attach(MIMEText(body, 'html'))
    if cc:
        message['cc'] = ', '.join(cc) if isinstance(cc, list) else cc
    if bcc:
        message['bcc'] = ', '.join(bcc) if isinstance(bcc, list) else bcc

    """
    for filename, file in files:

        image_url = file.url

        with open(filename, "wb") as fr:
            fr.write(requests.get(image_url).content)
        
        with open(filename, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            
            # Encode file in ASCII characters to send by email    
            email.encoders.encode_base64(part)

            # Add header as key/value pair to attachment part
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")

            # Add attachment to message and convert message to string
            message.attach(part)

        os.remove(filename)
    # message.replace_header("From", "aquari666@gmail.com")
    # message.replace_header("To", 'whitebirdinbluesky1990@gmail.com')
    """
    raw['raw'] = urlsafe_b64encode(message.as_bytes()).decode()

    return raw


def send_message(service, user_id, message):
    """Send an email message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      message: Message to be sent.

    Returns:
      Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        log.warning(f'Sent Message: {message}')
        return message
    except GoogleHttpError as err:
        log.error(f'An error occurred while sending GMail: {err}')


def send_gmail(cert, subject, body, to=None, cc=None, bcc=None, files=(), user=None, footer=None, context_data=None):
    """
    This function sends mail from ONLY Gmail 
    :param queue: Instance of  Queue
    :param subject:
    :param body:
    :param sender:
    :param to:
    :param cc:
    :param bcc:
    :param files:
    :param incident:
    :return:
    """
    if not context_data:
        context_data = {}

    try:
        # print(body)

        # body = render_to_string('auths/mail_templates/base.html', {'footer': footer, 'signature': "Signature Here", 'body': body})
        # body = Template(body).render(Context(context_data))
        
        print(2)
        body = Template(body).render(Context(context_data))
        print(3)
        # body = merge_message(queue, body, to)
        gmail = build_gmail(cert)
        print(4)
        sender = get_email(gmail)
        
        print(5)
        message = create_message(sender, subject, body, to, cc, bcc, files)
        print(6)
        log.warning(f"Sender: {sender}\nSubject: {subject}\nTo: {to}\nCC: {cc}\nBCC: {bcc}\nFiles: {files}")
        # print(f"=======Message=======: {message}")
        # log.warning(f"Sender: {sender}\nSubject: {subject}\nTo: {to}\nCC: {cc}\nBCC: {bcc}\nFiles: {files}")
        print(7)
        result = send_message(gmail, "me", message)
        
        print(8)
        return result
    except Exception as e:
        return {"msg": str(e)}


class TokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        # Ensure results are consistent across DB backends
        # login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
        return (str(user.pk) + str(timestamp) + str(user.is_active))


account_activation_token = TokenGenerator()
