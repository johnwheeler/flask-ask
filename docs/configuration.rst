Configuration
=============

Configuration
-------------

Flask-Ask exposes the following configuration variables:

============================ ============================================================================================
`ASK_APPLICATION_ID`         Turn on application ID verification by setting this variable to an application ID or a
                             list of allowed application IDs. By default, application ID verification is disabled and a
                             warning is logged. This variable should be set in production to ensure
                             requests are being sent by the applications you specify. **Default:** ``None``
`ASK_VERIFY_REQUESTS`        Enables or disables 
                             `Alexa request verification <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/developing-an-alexa-skill-as-a-web-service#checking-the-signature-of-the-request>`_, 
                             which ensures requests sent to your skill are 
                             from Amazon's Alexa service. This setting should not be disabled in production. It is 
                             useful for mocking JSON requests in automated tests. **Default:** ``True``
`ASK_VERIFY_TIMESTAMP_DEBUG` Turn on request timestamp verification while debugging by setting this to ``True``.
                             Timestamp verification helps mitigate against
                             `replay attacks <https://en.wikipedia.org/wiki/Replay_attack>`_. It
                             relies on the system clock being synchronized with an NTP server. This setting should not
                             be enabled in production. **Default:** ``False``
============================ ============================================================================================

Logging
-------

To see the JSON request / response structures pretty printed in the logs, turn on ``DEBUG``-level logging::

    import logging

    logging.getLogger('flask_ask').setLevel(logging.DEBUG)
