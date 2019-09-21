import logging
import os
import json

from flask import Flask
from flask_ask import Ask, request, session, question, statement, can_handle


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def launch():
    speech_text = 'Welcome to the Alexa Skills Kit, you can say hello'
    return question(speech_text).reprompt(speech_text).simple_card('HelloWorld', speech_text)


@ask.intent('HelloWorldIntent')
def hello_world():
    speech_text = 'Hello world'
    return statement(speech_text).simple_card('HelloWorld', speech_text)


@ask.intent('AMAZON.HelpIntent')
def help():
    speech_text = 'You can say hello to me!'
    return question(speech_text).reprompt(speech_text).simple_card('HelloWorld', speech_text)


@ask.session_ended
def session_ended():
    return "{}", 200

@ask.can_handle("HelloWorldIntent")
def hello_world_canhandle(slotName):
    canFufill = "YES"
    slots = {}
    if slotName == "test":
        slots.update({
            "slotName": ["YES", "YES"]
        })
    else:
        slots.update({
            "slotName": ["YES", "NO"]
        })

    

    return can_handle(canFufill, slots)



if __name__ == '__main__':

    event = {
      "session":{
        "new": True,
        "sessionId":"SessionId.[unique-value-here]",
        "application":{
          "applicationId":"amzn1.ask.skill.[unique-value-here]"
        },
        "user":{
          "userId":"amzn1.ask.account.[unique-value-here]"
        }
      },
      "request":{
        "type":"CanFulfillIntentRequest",
        "requestId":"EdwRequestId.[unique-value-here]",
        "intent":{
          "name":"HelloWorldIntent",
          "slots":{
            "name":{
              "name":"slotName",
              "value":"boop"
            }
          }
        },
        "locale":"en-US",
        "timestamp":"2017-10-03T22:02:29Z"
      },
      "context":{
        "AudioPlayer":{
          "playerActivity":"IDLE"
        },
        "System":{
          "application":{
            "applicationId":"amzn1.ask.skill.[unique-value-here]"
          },
          "user":{
            "userId":"amzn1.ask.account.[unique-value-here]"
          },
          "device":{
            "supportedInterfaces":{

            }
          }
        }
      },
      "version":"1.0"
    }
    print(ask.run_aws_lambda(event))
