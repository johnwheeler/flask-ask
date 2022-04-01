import config

from flask_ask import statement


# These are errors that will not be handled by Amazon Pay; Merchant must handle
def handleErrors(request):
	errorMessage 					= ''
	permissionsError 				= False
	actionResponseStatusCode 		= request['status']['code']
	actionResponseStatusMessage 	= request['status']['message']
	actionResponsePayloadMessage	= ''
	if 'errorMessage' in request['payload']:
		actionResponsePayloadMessage = request['payload']['errorMessage']

	knownPermissionError = {
		# Permissions errors - These must be resolved before a user can use Amazon Pay
		'ACCESS_DENIED',
		'ACCESS_NOT_REQUESTED',
		'FORBIDDEN'
	}
	knownIntegrationOrRuntimeError = {
		# Integration errors - These must be resolved before Amazon Pay can run
		'BuyerEqualsSeller',
		'InvalidParameterValue',
		'InvalidSandboxCustomerEmail',
		'InvalidSellerId',
		'UnauthorizedAccess',
		'UnsupportedCountryOfEstablishment',
		'UnsupportedCurrency',

		# Runtime errors - These must be resolved before a charge action can occur
		'DuplicateRequest',
		'InternalServerError',
		'InvalidAuthorizationAmount',
		'InvalidBillingAgreementId',
		'InvalidBillingAgreementStatus',
		'InvalidPaymentAction',
		'PeriodicAmountExceeded',
		'ProviderNotAuthorized',
		'ServiceUnavailable'
	}
	if actionResponseStatusMessage in knownPermissionError:
		permissionsError = True
		errorMessage = config.enablePermission
	elif actionResponseStatusMessage in knownIntegrationOrRuntimeError:
		errorMessage = config.errorMessage + config.errorStatusCode + actionResponseStatusCode + '.' + config.errorStatusMessage + actionResponseStatusMessage + '.' + config.errorPayloadMessage + actionResponsePayloadMessage
	else:	
		errorMessage = config.errorUnknown

	debug('handleErrors', request)

	# If it is a permissions error send a permission consent card to the user, otherwise .speak() error to resolve during testing
	if permissionsError:
	    return statement(errorMessage).consent_card(config.scope)
	else:
	    return statement(errorMessage)


# If billing agreement equals any of these states, you need to get the user to update their payment method
# Once payment method is updated, billing agreement state will go back to OPEN and you can charge the payment method
def handleBillingAgreementState( billingAgreementStatus, request):
	errorMessage = ''

	knownStatus = {
		'CANCELED',
		'CLOSED',
		'SUSPENDED'
	}
	if billingAgreementStatus in knownStatus:
		errorMessage = config.errorBillingAgreement +  billingAgreementStatus + config.errorBillingAgreementMessage
	else:
		errorMessage = config.errorUnknown

	debug('handleBillingAgreementState', request)

	return statement(errorMessage)


# Ideal scenario in authorization decline is that you save the session, allow the customer to fix their payment method, 
# and allow customer to resume session. This is just a simple message to tell the user their order was not placed.
def handleAuthorizationDeclines( authorizationStatusReasonCode, request):
	errorMessage = ''
	
	knownReasonCode = {
		'AmazonRejected',
		'InvalidPaymentMethod',
		'ProcessingFailure',
		'TransactionTimedOut'
	} 
	if authorizationStatusReasonCode in knownReasonCode:
	 	errorMessage = config.authorizationDeclineMessage
	else:
		errorMessage = config.errorUnknown

	debug('handleAuthorizationDeclines', request)

	return statement(errorMessage)


# Output object to console for debugging purposes
def debug(funcName, request ):
	print('ERROR in %s  ---  %s\n' % (funcName, str(request)))

