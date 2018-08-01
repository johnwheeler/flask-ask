import logging
import json
import os
import pytz
import base64
from datetime import datetime
from urlparse import urlparse

from google.appengine.api import urlfetch
from StringIO import StringIO
from pyasn1_modules import pem, rfc2459, rfc5280
from pyasn1.codec.der import decoder

class VerificationError(Exception): pass

def _check_signature_cert_url(cert_url):
    url = urlparse(cert_url)
    host = url.netloc.lower()
    path = os.path.normpath(url.path)

    # Sanity check location so we don't get some random person's cert.
    if url.scheme != 'https' or \
       host not in ['s3.amazonaws.com', 's3.amazonaws.com:443'] or \
       not path.startswith('/echo.api/'):
        logging.error('Invalid cert location: %s', cert_url)
        return False
    return True

def _get_signature(signature):
    if not signature:
        return None
    return base64.b64decode(signature)

def _verify_payload(pub_key,cert_start,cert_end,data,signature):
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Hash import SHA


    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    if now < cert_start or now >= cert_end:
        logging.warning('certificate is not valid right now')
        return False

    rsa_key = RSA.importKey(pub_key)
    verifier = PKCS1_v1_5.new(rsa_key)
    h = SHA.new(data)
    if verifier.verify(h, signature):
        return True

    return False

def _get_signature_cert(cert_url):
    resp = urlfetch.fetch(cert_url)
    if resp.status_code != 200:
        logging.error('failed to download certificate')
        return None,None,None

    #https://github.com/etingof/pyasn1
    #http://pyasn1.sourceforge.net/docs/tutorial.html#decoders
    certs_as_file = StringIO(resp.content)

    # To test:
    # certs_as_file = open('certs.pem')
    certs = []
    while True:
        try:
            substrate = pem.readPemFromFile(certs_as_file)
            # logging.info('Substrate: %s', substrate)
            certs.append( decoder.decode(substrate, asn1Spec=rfc2459.Certificate())[0] )
        except Exception as ex:
            logging.info('Searching for certificates has stopped because:')
            logging.info(ex)
            break

    if len(certs) == 0:
        logging.error('No certificates were able to be decoded')
        return None,None,None

    logging.info('%s Certificates at %s', len(certs), cert_url)
    for cert in certs:
        logging.info('Cert serial # %s', cert['tbsCertificate']['serialNumber'])
        logging.info('Not valid before %s', cert['tbsCertificate']['validity']['notBefore']['utcTime'].asDateTime)
        logging.info('Not valid after %s', cert['tbsCertificate']['validity']['notAfter']['utcTime'].asDateTime)
        logging.info('Public Key Info: %s', cert['tbsCertificate']['subjectPublicKeyInfo'])
        break

    #TODO We're verifying a single Certificate, but the Alexa docs talk of
    #verifying the "certifacte chain". May have to revisit this
    return certs[0]['tbsCertificate']['subjectPublicKeyInfo']['subjectPublicKey'],\
           certs[0]['tbsCertificate']['validity']['notBefore']['utcTime'].asDateTime,\
           certs[0]['tbsCertificate']['validity']['notAfter']['utcTime'].asDateTime

def _check_timestamp(body_json,max_diff=150):

    try:
        time_str = body_json['request']['timestamp']
        if not time_str:
            logging.error('Timestamp not present %s', body_json)
            return False

        req_ts = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
        diff = (datetime.utcnow() - req_ts).total_seconds()

        if abs(diff) > max_diff:
            logging.error('Timestamp difference too high: %d sec', diff)
            return False
    except:
        return False

    return True


def isValidAlexaRequest(r):
    """Validate the Alexa request using info in request headers and body
    Returns boolean
    """

    logging.info('verifier.isValidAlexaRequest()')
    logging.info('Alexa Req Headers: %s', r.headers)

    signature = _get_signature(r.headers.get('Signature',None))
    cert_url = r.headers.get('SignatureCertChainUrl','No CertChainUrl in Header')
    logging.info('Signature: %s \n Cert URL: %s', signature, cert_url)

    sig_cert_url_is_valid = _check_signature_cert_url(cert_url)
    timestamp_is_valid = _check_timestamp( json.loads(r.body) )

    if sig_cert_url_is_valid and timestamp_is_valid:
        logging.info('Signature URL and timestamp are valid')
        pub_key,cert_start,cert_end =  _get_signature_cert(cert_url)
        if not pub_key:
            logging.warning('no pub_key in certificate')
            return False
        if not _verify_payload(pub_key.asOctets(), cert_start, cert_end, r.body, signature):
            logging.warning('Payload did not verify')
            return False
    else:
        return False
    logging.info('Alexa request is valid')
    return True
