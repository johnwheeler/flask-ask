import logging
import os
import requests

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, buy, upsell, refund, logger
from model import Product

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


PRODUCT_KEY = "PRODUCT"



@ask.on_purchase_completed( mapping={'payload': 'payload','name':'name','status':'status','token':'token'})
def completed(payload, name, status, token):
    products = Product(context.System.apiAccessToken)
    logger.info('on-purchase-completed {}'.format( request))
    logger.info('payload: {} {}'.format(payload.purchaseResult, payload.productId))
    logger.info('name: {}'.format(name))
    logger.info('token: {}'.format(token))
    logger.info('status: {}'.format( status.code == 200))
    product_name = products.productName(payload.productId)
    logger.info('Product name'.format(product_name))
    if status.code == '200' and ('ACCEPTED' in payload.purchaseResult):
        return question('To listen it just say - play {} '.format(product_name))
    else:      
        return question('Do you want to buy another product?')

@ask.launch
def launch():
    products = Product(context.System.apiAccessToken)
    question_text = render_template('welcome', products=products.list())
    reprompt_text = render_template('welcome_reprompt')
    return question(question_text).reprompt(reprompt_text).simple_card('Welcome', question_text)


@ask.intent('BuySkillItemIntent', mapping={'product_name': 'ProductName'})
def buy_intent(product_name):
    products = Product(context.System.apiAccessToken)
    logger.info("PRODUCT: {}".format(product_name))
    buy_card = render_template('buy_card', product=product_name)
    productId = products.productId(product_name)
    if productId is not None:
        session.attributes[PRODUCT_KEY] = productId
    else:
        return statement("I didn't find a product {}".format(product_name))
        raise NotImplementedError()
    return buy(productId).simple_card('Welcome', question_text)

    #return upsell(product,'get this great product')


@ask.intent('RefundSkillItemIntent', mapping={'product_name': 'ProductName'})
def refund_intent(product_name):
    refund_card = render_template('refund_card')
    logger.info("PRODUCT: {}".format(product_name))

    products = Product(context.System.apiAccessToken)
    productId = products.productId(product_name)

    if productId is not None:
        session.attributes[PRODUCT_KEY] = productId
    else:
        raise NotImplementedError()
    return refund(productId)


@ask.intent('AMAZON.FallbackIntent')
def fallback_intent():
    return statement("FallbackIntent")


@ask.session_ended
def session_ended():
    return "{}", 200


if __name__ == '__main__':
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
        if verify == 'false':
            app.config['ASK_VERIFY_REQUESTS'] = False
    app.run(debug=True)

