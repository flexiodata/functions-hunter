
# ---
# name: hunter-enrich-org
# deployed: true
# title: Hunter Organization Enrichment
# description: Returns a set of data about the organization, the email addresses found and additional information about the people owning those email addresses.
# params:
#   - name: domain
#     type: string
#     description: The domain name from which you want to find the domain addresses. For example, "stripe.com".
#     required: true
#   - name: properties
#     type: array
#     description: The properties to return (defaults to all properties). See "Notes" for a listing of the available properties.
#     required: false
# examples:
#   - '"intercom.io"'
#   - '"intercom.io", "organization, first_name, last_name, email"'
#   - '"intercom.io", "first_name, last_name, email, linkedin, twitter"'
# notes: |
#   The following properties are allowed:
#     * `organization`: name of the organization associated with the specifed domain
#     * `domain`: domain name of the organization
#     * `first_name`: first name of the person
#     * `last_name`: last name of the person
#     * `email`: email address of the person
#     * `email_disposable`: true if this is an domain address from a disposable domain service
#     * `email_webmail`: true if we find this is an domain from a webmail, for example Gmail
#     * `email_score`: estimation of the probability the email address returned is correct
#     * `phone`: phone number of the person
#     * `position`: position of the person in the organization
#     * `seniority`: seniority level of the person in the organization
#     * `department`: department of the person in the organization
#     * `linkedin`: username of the person on LinkedIn
#     * `twitter`: username of the person on Twitter
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
    property_map['organization'] = 'organization'
    property_map['domain'] = 'domain'
    property_map['email_disposable'] = 'disposable'
    property_map['email_webmail'] = 'webmail'
    property_map['first_name'] = 'first_name'
    property_map['last_name'] = 'last_name'
    property_map['email'] = 'value'
    property_map['email_type'] = 'type'
    property_map['email_score'] = 'confidence'
    property_map['phone'] = 'phone_number'
    property_map['position'] = 'position'
    property_map['seniority'] = 'seniority'
    property_map['department'] = 'department'
    property_map['linkedin'] = 'linkedin'
    property_map['twitter'] = 'twitter'

    # get the properties to return and the property map
    properties = [p.lower().strip() for p in input['properties']]

    # if we have a wildcard, get all the properties
    if len(properties) == 1 and properties[0] == '*':
        properties = list(property_map.keys())

    try:

        # see here for more info:
        # https://hunter.io/api/docs#domain-verifier
        url_query_params = {
            'domain': input['domain'],
            'api_key': auth_token
        }
        url_query_str = urllib.parse.urlencode(url_query_params)
        url = 'https://api.hunter.io/v2/domain-search?' + url_query_str

        # get the response data as a JSON object
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()
        content = content.get('data', {})

        header_info = {}
        header_info['domain'] = content.get('domain','')
        header_info['disposable'] = content.get('disposable','')
        header_info['webmail'] = content.get('webmail','')
        header_info['pattern'] = content.get('pattern','')
        header_info['organization'] = content.get('organization','')

        # build up the result
        result = []
        result.append(properties)
        emails = content.get('emails',[])
        for detail_info in emails:
            item = {**header_info, **detail_info}
            row = [item.get(property_map.get(p,''),'') or '' for p in properties]
            result.append(row)

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
