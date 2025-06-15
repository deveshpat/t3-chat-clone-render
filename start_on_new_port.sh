#!/bin/bash
# start_on_new_port.sh

# Set a secret key for Chainlit's authentication
export CHAINLIT_AUTH_SECRET="t3-clonethon-secret-key"
 
# Run the Chainlit app on port 8001
python3 -m chainlit run app.py -w --port 8001 