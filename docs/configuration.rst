Configuration
-------------
Flask-Ask exposes the following configuration variables:

============================ ============================================================================================
`ASK_APPLICATION_ID`         Turn on application ID verification by setting this variable to an application ID or a 
                             list of allowed application IDs. By default, application ID verification is disabled and a
                             warning is logged. This variable should be set in production to ensure
                             requests are being sent by the applications you specify. **Default:** ``None``
`ASK_VERIFY_TIMESTAMP_DEBUG` Turn on request timestamp verification while debugging by setting this to ``True``.
                             Timestamp verification helps mitigate against
                             `replay attacks <https://en.wikipedia.org/wiki/Replay_attack>`_. It
                             relies on the system clock being synchronized with an NTP server. This setting should not
                             be enabled in production. **Default:** ``False``
============================ ============================================================================================
