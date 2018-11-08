Porting payment integration code in Amazon Alexa node.js cookbook to python using the flask-ask package.

### Deployment Instruction
```bash
git clone https://github.com/Relishly/python-flask-ask-amazon-pay.git
cd python-flask-ask-amazon-pay

# Install my forked version of the flask-ask library. The original library does not support payment integration 
cd forked-flask-ask && python setup.py install && cd .. # May be prompted to sudo

# Open a new terminal window
ngrok http -bind-tls=true 5000
```
Copy the ngrok forwarding url, which looks like https://5f271086.ngrok.io, to Alexa Endpoint
