import utilities

# TODO:
# 1. Fill in appID and sellerId
# 2. Fill in sandboxCustomerEmailId and set sandboxMode as True
#    OR
#    provide an empty string to sandboxCustomerEmailId and set sandboxMode as False


# GLOBAL
appID = 'amzn1.ask.skill.xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'   # Required; Alexa Skill ID
sellerId = ''                                      				# Required; Amazon Pay seller ID; Used for both Setup and Process Payment

# DIRECTIVE CONFIG
connectionCharge = 'Charge'                                     # Required;
connectionSetup = 'Setup'                                       # Required;
directiveCharge = 'ChargeAmazonPay'                             # Required;
directiveSetup = 'SetupAmazonPay'                               # Required;
directiveType = 'Connections.SendRequest'                       # Required;
version = '1.0'                                                 # Required;

# SETUP    
checkoutLanguage= 'en_US'                                       # Optional; US must be en_US
countryOfEstablishment= 'US'                                    # Required;
ledgerCurrency= 'USD'                                           # Required; This doesn't exist in web SDK; GBP and EUR
needAmazonShippingAddress= True                                 # Optional; Must be boolean;
sandboxCustomerEmailId= 'test@example.com'   					# Optional; Required if sandboxMode equals true; Must setup Amazon Pay test account first;
sandboxMode= True                                               # Optional; Must be false for certification; Must be boolean;

# PROCESS PAYMENT
paymentAction= 'AuthorizeAndCapture'                          # Required; Authorize or AuthorizeAndCapture
providerAttributes= ''                                        # Optional; Required if Solution Provider.
sellerOrderAttributes= ''                                     # Optional;

# AUTHORIZE ATTRIBUTES
authorizationReferenceId      = utilities.generateRandomString( 32 )    # Required; Must be unique, max 32 chars
sellerAuthorizationNote       = utilities.getSimulationString( '' )     # Optional; Max 255 chars
softDescriptor                = '16charSoftDesc'                        # Optional; Max 16 chars
transactionTimeout      	  = 0                                 		# Optional; The default value for Alexa transactions is 0.
    
# AUTHORIZE AMOUNT
amount                      = '0.99'                              # Required; Max $150,000
currencyCode                = 'USD'                               # Required;

# SELLER ORDER ATTRIBUTES
customInformation           = 'customInformation max 1024 chars'              # Optional; Max 1024 chars
sellerNote                  = 'sellerNote max 1024 chars'                     # Optional; Max 1024 chars
sellerOrderId               = 'Alexa unique sellerOrderId'                    # Optional; Merchant specific order ID
sellerStoreName             = 'Blitz and Chips'                               # Optional; Documentation calls this out as storeName not sellerStoreName

# ADDITIONAL ATTRIBUTES
platformId          		= ''                                  # Optional; Used for Solution Providers
sellerBillingAgreementId    = ''                                  # Optional; The merchant-specified identifier of this billing agreement
storeName           		= sellerStoreName                     # Optional; Why is there 2 store names?


#  The following strings DO NOT interact with Amazon Pay
#  They are only here to augment the skill

# INTENT RESPONSE STRINGS
launchRequestWelcomeResponse  	= 'Welcome to ' + sellerStoreName + '. '                  			# Optional; Used for demo only
launchRequestQuestionResponse 	= 'Would you like to buy one Plumbus for $'+ amount +'?'      		# Optional; Used for demo only
noIntentResponse        		= 'There is nothing else for sale. Goodbye.'            			# Optional; Used for demo only
noIntentMessage         		= 'Please visit us again'                       					# Optional; Used for demo only
orderConfirmationResponse   	= 'Thank you for ordering from ' + sellerStoreName + '. Goodbye.'   # Optional; Used for demo only
orderConfirmationTitle    		= 'Order Details for Testing'                     					# Optional; Used for demo only
storeURL            			= 'blitzandchips.com'                             					# Optional; Used for demo only

# ERROR RESPONSE STRINGS
enablePermission        	= 'Please enable permission for Amazon Pay in your Alexa app.'    	# Optional; Used for demo only
scope             			= 'payments:autopay_consent'                      					# Optional; Used for demo only
errorMessage          		= 'Merchant error occurred. '                     					# Optional; Used for demo only
errorUnknown          		= 'Unknown error occurred. ' 
errorStatusCode 			= 'Status code: '                          							# Optional; Used for demo only
errorStatusMessage      	= ' Status message: '                        						# Optional; Used for demo only
errorPayloadMessage      	= ' Payload message: '                        						# Optional; Used for demo only
errorBillingAgreement    	= 'Billing agreement state is ' 
errorBillingAgreementMessage= '. Reach out to the user to resolve this issue.'         			# Optional; Used for demo only
authorizationDeclineMessage = 'Your order was not placed and you have not been charged.'      	# Optional; Used for demo only
debug 						= 'debug'                                                           # Optional; Used for demo only

