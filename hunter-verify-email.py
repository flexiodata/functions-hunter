
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
#     description: The properties to return (defaults to 'score'). See "Notes" for a listing of the available properties.
#     required: false
# examples:
#   - '"steli@close.io"'
#   - '"steli@close.io", "score, status, webmail"'
#   - '"steli@close.io", "score, status, autogen, disposable"'
# notes: |
#   The following properties are available:
#     * `score`: the deliverability score of the email address (default)
#     * `status`: "deliverable", "undeliverable", "risky"
#     * `regexp`: true if the email address passes a regular expression test
#     * `autogen`: true if this is an automatically generated email address
#     * `disposable`: true if this is an email address from a disposable email service
#     * `webmail`: true if we find this is an email from a webmail, for example Gmail
#     * `mx_records`: true if MX records exist on the domain of the given email address
#     * `smtp_server`: true if connecting to the SMTP server was successful
#     * `smtp_check`: true if the email address doesn't bounce
#     * `smtp_check_blocked`: true if the SMTP server prevented the STMP check
#     * `smtp_accept_all`: true if the SMTP server accepts all the email addresses; this can result in false positives on SMTP checks
# ---

import json
import requests
import itertools
import urllib
from datetime import *
from cerberus import Validator
from collections import OrderedDict

properties_map = OrderedDict()
properties_map['score'] = 'score'
properties_map['status'] = 'result'
properties_map['regexp'] = 'regexp'
properties_map['autogen'] = 'gibberish'
properties_map['disposable'] = 'disposable'
properties_map['webmail'] = 'webmail'
properties_map['mx_records'] = 'mx_records'
properties_map['smtp_server'] = 'smtp_server'
properties_map['smtp_check'] = 'smtp_check'
properties_map['smtp_check_blocked'] = 'block'
properties_map['smtp_accept_all'] = 'accept_all'

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
    params['properties'] = {'required': False, 'validator': validator_list, 'coerce': to_list, 'default': 'score'}
    input = dict(zip(params.keys(), input))

    # validate the mapped input against the validator
    # if the input is valid return an error
    v = Validator(params, allow_unknown = True)
    input = v.validated(input)
    if input is None:
        raise ValueError

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
        content = response.json()
        content = content.get('data', {})

        # map this function's property names to the API's property names
        properties_iter = map(lambda prop : properties_map.get(prop, ''), input['properties'])
        properties_list = list(properties_iter)

        # uncomment the following lines to debug the property name mapping
        # flex.output.content_type = "application/json"
        # flex.output.write(debug_properties_map())
        # return

        # limit the results to the requested properties
        properties = [c.lower().strip() for c in properties_list]
        result = [[content.get(c,'') for c in properties]]

        # return the results
        result = json.dumps(result, default=to_string)
        flex.output.content_type = "application/json"
        flex.output.write(result)

    except:
        raise RuntimeError

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
