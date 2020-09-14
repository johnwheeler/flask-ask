import logging
import os

from flask import Flask
from flask_ask import Ask, request, context, session, question, statement, setup_payment, charge_payment

import utilities
import config
import payload
import error_handler


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def launch():
    return question(config.launchRequestWelcomeResponse + config.launchRequestQuestionResponse).reprompt(config.launchRequestQuestionResponse)


# No, I do not want to buy something
@ask.intent('AMAZON.NoIntent')
def no():
    return question(config.noIntentResponse).simple_card(config.noIntentMessage, config.storeURL)


#Yes, I do want to buy something
@ask.intent('AMAZON.YesIntent')
def yes():
    # If you have a valid billing agreement from a previous session, skip the Setup action and call the Charge action instead 
    consentToken    = utilities.getConsentToken(context)
    token           = utilities.generateRandomString(12)

    # If you do not have a billing agreement set the Setup payload in Skill Connections and send the request directive
    setupPayload    = payload.buildSetup(consentToken);
    return setup_payment(setupPayload)


# You requested the Setup or Charge directive and are now receiving the Connections.Response
@ask.on_purchase_completed()
def connectionResponse():
    consentToken = utilities.getConsentToken(context)
    connectionName = request['name']
    connectionResponsePayload = request['payload']
    connectionResponseStatusCode = request['status']['code']

    if connectionResponseStatusCode != '200':
        return error_handler.handleErrors(request)
    else:
        #Receiving Setup Connections.Response
        if connectionName == config.connectionSetup:
            token = utilities.generateRandomString( 12 )

            # Get the billingAgreementId and billingAgreementStatus from the Setup Connections.Response
            billingAgreementId = connectionResponsePayload['billingAgreementDetails']['billingAgreementId']
            billingAgreementStatus = connectionResponsePayload['billingAgreementDetails']['billingAgreementStatus']

            # If billingAgreementStatus is valid, Charge the payment method    
            if billingAgreementStatus == 'OPEN':
                # Set the Charge payload in Skill Connections and send the request directive
                chargePayload = payload.buildCharge(consentToken, billingAgreementId)
                return charge_payment(chargePayload)

            # If billingAgreementStatus is not valid, do not Charge the payment method 
            else:
                return error.handleBillingAgreementState(billingAgreementStatus, request)

        # Receiving Charge Connections.Response
        elif connectionName == config.connectionCharge:
            authorizationStatusState = connectionResponsePayload['authorizationDetails']['authorizationStatus']['state']
            
            # Authorization is declined, tell the user their order was not placed
            if authorizationStatusState == 'Declined':
                authorizationStatusReasonCode = connectionResponsePayload['authorizationDetails']['authorizationStatus']['reasonCode']
                return error.handleAuthorizationDeclines(authorizationStatusReasonCode, request)

            # Authorization is approved, tell the user their order was placed
            else:
                return statement(config.orderConfirmationResponse)


@ask.session_ended
def session_ended():
    return request, 200


if __name__ == '__main__':
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
        if verify == 'false':
            app.config.ASK_VERIFY_REQUESTS = False
    app.run(debug=True)
