
# ---
# name: hunter-verify-email
# deployed: true
# title: Hunter Email Verification
# description: Return email delivery verification and confidence score.
# params:
#   - name: email
#     type: string
#     description: The email address you want to verify
#     required: true
#   - name: properties
#     type: array
#     description: The properties to return (defaults to all properties). See "Returns" for a listing of the available properties.
#     required: false
# returns:
#   - name: score
#     type: string
#     description: The deliverability score of the email address
#   - name: status
#     type: string
#     description: The status; one of **deliverable**, **undeliverable**, or **risky**
#   - name: regexp
#     type: string
#     description: True if the email address passes a regular expression test
#   - name: autogen
#     type: string
#     description: True if this is an automatically generated email address
#   - name: disposable
#     type: string
#     description: True if this is an email address from a disposable email service
#   - name: webmail
#     type: string
#     description: True if we find this is an email from a webmail, for example Gmail
#   - name: mx_records
#     type: string
#     description: True if MX records exist on the domain of the given email address
#   - name: smtp_server
#     type: string
#     description: True if connecting to the SMTP server was successful
#   - name: smtp_check
#     type: string
#     description: True if the email address doesn't bounce
#   - name: smtp_check_blocked
#     type: string
#     description: True if the SMTP server prevented the STMP check
#   - name: smtp_accept_all
#     type: string
#     description: True if the SMTP server accepts all the email addresses; this can result in false positives on SMTP checks
# examples:
#   - '"steli@close.io"'
#   - '"steli@close.io", "score, status, webmail"'
#   - '"steli@close.io", "score, status, autogen, disposable"'
# ---

import json
import requests
import itertools
import urllib
from datetime import *
from cerberus import Validator
from collections import OrderedDict

# main function entry point
def flexio_handler(flex):

    # get the api key from the variable input
    auth_token = dict(flex.vars).get('hunter_api_key')
    if auth_token is None:
        flex.output.content_type = "application/json"
        flex.output.write([[""]])
        return

    # get the input
    input = flex.input.read()
    try:
        input = json.loads(input)
        if not isinstance(input, list): raise ValueError
    except ValueError:
        raise ValueError

    # define the expected parameters and map the values to the parameter names
    # based on the positions of the keys/values
    params = OrderedDict()
    params['email'] = {'required': True, 'type': 'string'}
    params['properties'] = {'required': False, 'validator': validator_list, 'coerce': to_list, 'default': '*'}
    input = dict(zip(params.keys(), input))

    # validate the mapped input against the validator
    # if the input is valid return an error
    v = Validator(params, allow_unknown = True)
    input = v.validated(input)
    if input is None:
        raise ValueError

    # map this function's property names to the API's property names
    property_map = OrderedDict()
    property_map['score'] = 'score'
    property_map['status'] = 'result'
    property_map['regexp'] = 'regexp'
    property_map['autogen'] = 'gibberish'
    property_map['disposable'] = 'disposable'
    property_map['webmail'] = 'webmail'
    property_map['mx_records'] = 'mx_records'
    property_map['smtp_server'] = 'smtp_server'
    property_map['smtp_check'] = 'smtp_check'
    property_map['smtp_check_blocked'] = 'block'
    property_map['smtp_accept_all'] = 'accept_all'

    # get the properties to return and the property map
    properties = [p.lower().strip() for p in input['properties']]

    # if we have a wildcard, get all the properties
    if len(properties) == 1 and properties[0] == '*':
        properties = list(property_map.keys())

    try:

        # see here for more info:
        # https://hunter.io/api/docs#email-verifier
        url_query_params = {
            'email': input['email'],
            'api_key': auth_token
        }
        url_query_str = urllib.parse.urlencode(url_query_params)
        url = 'https://api.hunter.io/v2/email-verifier?' + url_query_str

        # get the response data as a JSON object
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()
        content = content.get('data', {})

        # get the properties
        result = [content.get(property_map.get(p,''),'') for p in properties] # don't use "or '' for p in properties" because result can be true/false

        # return the results
        result = json.dumps(result, default=to_string)
        flex.output.content_type = "application/json"
        flex.output.write(result)

    except:
        flex.output.content_type = 'application/json'
        flex.output.write([['']])

def debug_properties_map():
    properties_iter = map(lambda prop : prop + ' => ' + properties_map.get(prop, ''), properties_map)
    return list(properties_iter)

def validator_list(field, value, error):
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, str):
                error(field, 'Must be a list with only string values')
        return
    error(field, 'Must be a string or a list of strings')

def to_string(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Decimal)):
        return str(value)
    return value

def to_list(value):
    # if we have a list of strings, create a list from them; if we have
    # a list of lists, flatten it into a single list of strings
    if isinstance(value, str):
        return value.split(",")
    if isinstance(value, list):
        return list(itertools.chain.from_iterable(value))
    return None
