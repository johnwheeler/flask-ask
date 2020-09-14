import config

# Builds payload for Setup action
def buildSetup (consentToken):
    payload = {
        'consentToken':                             consentToken,
        'sellerId':                                 config.sellerId,
        'sandboxCustomerEmailId':                   config.sandboxCustomerEmailId,
        'sandboxMode':                              config.sandboxMode,
        'checkoutLanguage':                         config.checkoutLanguage,
        'countryOfEstablishment':                   config.countryOfEstablishment,
        'ledgerCurrency':                           config.ledgerCurrency,
        'billingAgreementAttributes': {
            'platformId': 							config.platformId,
            'sellerNote': 							config.sellerNote,
            'sellerBillingAgreementAttributes': {
                'sellerBillingAgreementId': 		config.sellerBillingAgreementId,
                'storeName': 						config.storeName,
                'customInformation': 				config.customInformation
            }
        },
        'needAmazonShippingAddress': 				config.needAmazonShippingAddress
    }

    return payload


# Builds payload for Charge action
def buildCharge (consentToken, billingAgreementId):
    payload = {
        'consentToken':                 consentToken,
        'sellerId':                     config.sellerId,
        'billingAgreementId':           billingAgreementId,
        'paymentAction':                config.paymentAction,
        'authorizeAttributes': {
            'authorizationReferenceId': config.authorizationReferenceId,
            'authorizationAmount': {
                'amount':               config.amount,
                'currencyCode':         config.currencyCode
            },
            'transactionTimeout':       config.transactionTimeout,
            'sellerAuthorizationNote':  config.sellerAuthorizationNote,
            'softDescriptor':           config.softDescriptor
        },
        'sellerOrderAttributes': {
            'sellerOrderId':            config.sellerOrderId,
            'storeName':                config.storeName,
            'customInformation':        config.customInformation,
            'sellerNote':               config.sellerNote
        }
    }

    return payload
