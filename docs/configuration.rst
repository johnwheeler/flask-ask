Configuration
-------------
Flask-Ask exposes the following configuration variables:

============================ ============================================================================================
`ASK_APPLICATION_ID`         Turn on application ID verification by setting this variable to the application ID Amazon
                             assigned your application. By default, application ID verification is disabled and a
                             warning is logged. This variable or the one below should be set in production to ensure
                             requests are being sent by the application you specify. This variable is for convenience
                             if you're only accepting requests from one application. Otherwise, use the variable
                             below. **Default:** None
`ASK_APPLICATION_IDS`        Turn on application ID verification by setting this variable to a list of allowed
                             application IDs. By default, application ID verification is disabled and a
                             warning is logged. This variable or the one above should be set in production to ensure
                             requests are being sent by the applications you specify. This is same as the variable above
                             but allows a single skill to respond to multiple applications. **Default:** ``[]``
`ASK_VERIFY_TIMESTAMP_DEBUG` Turn on request timestamp verification while debugging by setting this to ``True``.
                             Timestamp verification helps mitigate against
                             `replay attacks <https://en.wikipedia.org/wiki/Replay_attack>`_. It
                             relies on the system clock being synchronized with an NTP server. This setting should not
                             be enabled in production. **Default:** ``False``
============================ ============================================================================================
