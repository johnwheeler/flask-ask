Porting payment integration code in Amazon Alexa cookbook written in node.js (https://github.com/alexa/alexa-cookbook/tree/master/feature-demos/skill-demo-amazon-pay) to python. Made changes to suit the flask-ask library and fixed a few bugs.

### Deployment Instruction
```bash
# From path_to/samples/payment_integration, run:
python index.py

# If you are testing locally, install ngrok and in a new terminal window, do:
ngrok http -bind-tls=true 5000
```
In Alexa developer console, paste en-US.json to the json editor. Paste the ngrok forwarding url, which looks like https://xxxxxxxx.ngrok.io, to Alexa Endpoint. Enable Amazon payment in skill permissions.

Then, you may ask alexa to "open payments demo" and say "yes" to the purchase confirmation.
