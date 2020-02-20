
# ---
# name: hunter-enrich-people
# deployed: true
# title: Hunter People Enrichment
# description: Return the professional email of this person and a confidence score.
# params:
#   - name: domain
#     type: string
#     description: The domain name from which you want to find the email address. For example, "asana.com".
#     required: true
#   - name: first_name
#     type: string
#     description: The person's first name. It doesn't need to be in lowercase.
#     required: true
#   - name: last_name
#     type: string
#     description: The person's last name. It doesn't need to be in lowercase.
#     required: true
#   - name: properties
#     type: array
#     description: The properties to return (defaults to all properties). See "Returns" for a listing of the available properties.
#     required: false
# returns:
#   - name: organization
#     type: string
#     description: The name of the organization associated with the specifed domain
#   - name: domain
#     type: string
#     description: The domain name of the organization
#   - name: first_name
#     type: string
#     description: The first name of the person
#   - name: last_name
#     type: string
#     description: The last name of the person
#   - name: email
#     type: string
#     description: The email address of the person
#   - name: email_score
#     type: string
#     description: An estimation of the probability the email address returned is correct
#   - name: phone
#     type: string
#     description: The phone number of the person
#   - name: position
#     type: string
#     description: The position of the person in the organization
# examples:
#   - '"asana.com", "Dustin", "Moskovitz"'
#   - '"asana.com", "Dustin", "Moskovitz", "email, organization"'
# ---

import json
import requests
import urllib
import itertools
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
    params['domain'] = {'required': True, 'type': 'string'}
    params['first_name'] = {'required': True, 'type': 'string'}
    params['last_name'] = {'required': True, 'type': 'string'}
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
    property_map['organization'] = 'company'
    property_map['domain'] = 'domain'
    property_map['first_name'] = 'first_name'
    property_map['last_name'] = 'last_name'
    property_map['email'] = 'email'
    property_map['email_score'] = 'score'
    property_map['phone'] = 'phone_number'
    property_map['position'] = 'position'

    # get the properties to return and the property map
    properties = [p.lower().strip() for p in input['properties']]

    # if we have a wildcard, get all the properties
    if len(properties) == 1 and properties[0] == '*':
        properties = list(property_map.keys())

    try:

        # see here for more info:
        # https://hunter.io/api/docs#email-verifier
        url_query_params = {
            'domain': input['domain'],
            'first_name': input['first_name'],
            'last_name': input['last_name'],
            'api_key': auth_token
        }
        url_query_str = urllib.parse.urlencode(url_query_params)
        url = 'https://api.hunter.io/v2/email-finder?' + url_query_str

        # get the response data as a JSON object
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()
        content = content.get('data', {})

        # get the properties
        result = [content.get(property_map.get(p,''),'') or '' for p in properties]

        # return the results
        result = json.dumps(result, default=to_string)
        flex.output.content_type = "application/json"
        flex.output.write(result)

    except:
        flex.output.content_type = 'application/json'
        flex.output.write([['']])

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
