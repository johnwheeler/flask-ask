from random import randint

# Used for testing simulation strings in sandbox mode
def getSimulationString( simuType ):
	simulationString = ''

	if simuType == 'InvalidPaymentMethod':
		# PaymentMethodUpdateTimeInMins only works with Async authorizations to change BA back to OPEN; Sync authorizations will not revert
		simulationString = '{ "SandboxSimulation": { "State":"Declined", "ReasonCode":"InvalidPaymentMethod", "PaymentMethodUpdateTimeInMins":1, "SoftDecline":"true" } }'
	elif simuType == 'AmazonRejected':
		simulationString = '{ "SandboxSimulation": { "State":"Declined", "ReasonCode":"AmazonRejected" } }'

	elif simuType == 'TransactionTimedOut':
		simulationString = '{ "SandboxSimulation": { "State":"Declined", "ReasonCode":"TransactionTimedOut" } }'
	else:
		simulationString = ''

	return simulationString


# Sometimes you just need a random string right?
def generateRandomString( length ):
    randomString 	= ''
    stringValues 	= 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

    for i in range(length):
        randomString += stringValues[ randint(0, len(stringValues)-1) ]

    return randomString


def getConsentToken( context ):
	return context['System']['apiAccessToken']

