import requests
from flask import  json
from flask_ask import logger

class Product():
    '''
    Object model for inSkillProducts and methods to access products.
    
    {"inSkillProducts":[
    {"productId":"amzn1.adg.product.your_product_id",
    "referenceName":"product_name",
    "type":"ENTITLEMENT",
    "name":"product name",
    "summary":"This product has helped many people.",
    "entitled":"NOT_ENTITLED",
    "purchasable":"NOT_PURCHASABLE"}],
    "nextToken":null,
    "truncated":false}

    '''

    def __init__(self, apiAccessToken):
        self.token = apiAccessToken
        self.product_list = self.query()


    def query(self):
        # Information required to invoke the API is available in the session
        apiEndpoint = "https://api.amazonalexa.com"
        apiPath     = "/v1/users/~current/skills/~current/inSkillProducts"
        token       = "bearer " + self.token
        language    = "en-US" #self.event.request.locale

        url = apiEndpoint + apiPath
        headers = {
                "Content-Type"      : 'application/json',
                "Accept-Language"   : language,
                "Authorization"     : token
            }
        #Call the API
        res = requests.get(url, headers=headers)
        logger.info('PRODUCTS:' + '*' * 80)
        logger.info(res.status_code)
        logger.info(res.text)
        if res.status_code == 200:
            data = json.loads(res.text)
            return data['inSkillProducts']
        else:
            return None        

    def list(self):
        """ return list of purchasable and not entitled products"""
        mylist = []
        for prod in self.product_list:
            if self.purchasable(prod) and not self.entitled(prod):
                mylist.append(prod)
        return mylist

    def purchasable(self, product):
        """ return True if purchasable product"""
        return 'PURCHASABLE' == product['purchasable']
    
    def entitled(self, product):
        """ return True if entitled product"""
        return 'ENTITLED' == product['entitled']
        

    def productId(self, name):
        print(self.product_list)
        for prod in self.product_list:
            if name == prod['name'].lower():
                return prod['productId']
        return None

    def productName(self, id):
        for prod in self.product_list:
            if id == prod['productId']:
                return prod['name']
        return None
