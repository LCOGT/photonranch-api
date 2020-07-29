# Photon Ranch API

This is the api used to talk with photon ranch services running in AWS. All communication between observatory sites and the web interface take place here, including sending/receiving commands, status, and handling data.

This is a serverless api, deployed with the Serverless framework which creates python functions running in AWS Lambda behind endpoints in an API Gateway.

Dependencies for the python lambda functions are zipped with the serverless-python-requirements plugin. Special note for psycopg2 (python postgres library): make sure `requirements.txt` lists 'psycopg2-binary', and not 'psycopg2'. This is required for the dependency to run in the lambda environment.


## Site Events

