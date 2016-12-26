import os
import base64
import posixpath
from datetime import datetime
from six.moves.urllib.parse import urlparse
from six.moves.urllib.request import urlopen

from OpenSSL import crypto

from . import logger


class VerificationError(Exception): pass


def load_certificate(cert_url):
    if not _valid_certificate_url(cert_url):
        raise VerificationError("Certificate URL verification failed")
    cert_data = urlopen(cert_url).read()
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
    if not _valid_certificate(cert):
        raise VerificationError("Certificate verification failed")
    return cert


def verify_signature(cert, signature, signed_data):
    try:
        signature = base64.b64decode(signature)
        crypto.verify(cert, signature, signed_data, 'sha1')
    except crypto.Error as e:
        raise VerificationError(e)


def verify_timestamp(timestamp):
    dt = datetime.utcnow() - timestamp.replace(tzinfo=None)
    if abs(dt.total_seconds()) > 150:
        raise VerificationError("Timestamp verification failed")


def verify_application_id(candidate, records):
    if candidate not in records:
        raise VerificationError("Application ID verification failed")


def _valid_certificate_url(cert_url):
    parsed_url = urlparse(cert_url)
    if parsed_url.scheme == 'https':
        if parsed_url.hostname == "s3.amazonaws.com":
            if posixpath.normpath(parsed_url.path).startswith("/echo.api/"):
                return True
    return False


def _valid_certificate(cert):
    not_after = cert.get_notAfter().decode('utf-8')
    not_after = datetime.strptime(not_after, '%Y%m%d%H%M%SZ')
    if datetime.utcnow() >= not_after:
        return False
    found = False
    for i in range(0, cert.get_extension_count()):
        extension = cert.get_extension(i)
        short_name = extension.get_short_name().decode('utf-8')
        value = str(extension)
        if 'subjectAltName' == short_name and 'DNS:echo-api.amazon.com' == value:
                found = True
                break
    if not found:
        return False
    return True
