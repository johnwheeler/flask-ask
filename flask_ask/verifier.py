import os
import urllib2
import base64
from urlparse import urlparse
from datetime import datetime

from OpenSSL import crypto


class VerificationError(Exception): pass


def load_certificate(cert_url):
    if not _valid_certificate_url(cert_url):
        raise VerificationError("Certificate URL verification failed")
    cert_data = urllib2.urlopen(cert_url).read()
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
    if not _valid_certificate(cert):
        raise VerificationError("Certificate verification failed")
    return cert


def verify_signature(cert, signature, signed_data):
    try:
        signature = base64.b64decode(signature)
        crypto.verify(cert, signature, signed_data, 'sha1')
    except crypto.Error, e:
        raise VerificationError(e)


def verify_timestamp(timestamp):
    dt = datetime.utcnow() - timestamp.replace(tzinfo=None)
    if dt.seconds > 150:
        raise VerificationError("Timestamp verification failed")


def verify_application_id(test_id, application_id, application_ids):
    if test_id != application_id and test_id not in application_ids:
        raise VerificationError("Application ID verification failed")


def _valid_certificate_url(cert_url):
    parsed_url = urlparse(cert_url)
    if parsed_url.scheme == 'https':
        if parsed_url.hostname == "s3.amazonaws.com":
            if os.path.normpath(parsed_url.path).startswith("/echo.api/"):
                return True
    return False


def _valid_certificate(cert):
    not_after = datetime.strptime(cert.get_notAfter(), '%Y%m%d%H%M%SZ')
    if datetime.utcnow() >= not_after:
        return False
    found = False
    for i in range(0, cert.get_extension_count()):
        extension = cert.get_extension(i)
        short_name = extension.get_short_name()
        value = str(extension)
        if 'subjectAltName' == short_name and 'DNS:echo-api.amazon.com' == value:
                found = True
                break
    if not found:
        return False
    return True
