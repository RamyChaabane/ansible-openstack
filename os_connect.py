import requests
import yaml
import sys
import os
import json


class Connect:

    def __init__(self, cloud_name):

        list_of_path = ['/etc/openstack/clouds', '{}/.config/openstack/clouds'.format(os.path.expanduser('~'))]
        for path in list_of_path:
            if not os.path.isfile(path + '.yaml'):
                if os.path.isfile(path + '.yml'):
                    clouds_path = path + '.yml'
                    break
            else:
                clouds_path = path + '.yaml'
                break
        else:
            sys.exit('Error: no clouds yaml file has been found')

        cloud_dict = yaml.load(open(clouds_path, 'r'))['clouds'][cloud_name]
        auth_dict = cloud_dict['auth']

        # analyzing clouds.yaml data
        if not cloud_dict.get('api_version'):
            api_version = auth_dict['auth_url'].split('/').pop()

            if api_version not in ['v2.0', 'v3']:
                sys.exit('Api version is not specified in the authentication URL')
        else:
            self._api_version = cloud_dict.get('identity_api_version')

        if self._api_version == 'v3':

            data_json = dict(auth=dict(
                identity=dict(
                    methods=["password"],
                    password=dict(
                        user=dict(
                            domain=dict(
                                name=auth_dict['user_domain_name']
                            ),
                            name=auth_dict['username'],
                            password=auth_dict['password']
                        )
                    )
                ),
                scope=dict(
                    project=dict(
                        domain=dict(
                            name=auth_dict['project_domain_name']
                        ),
                        name=auth_dict['project_name']
                    )
                )
            )
            )

            self._data = json.dumps(data_json)
            self._curl_url = '{}/auth/tokens'.format(auth_dict['auth_url'])
            self._cacert = cloud_dict.get('cacert')

        else:

            data_json = dict(
                auth=dict(
                    tenantName=auth_dict['project_name'],
                    passwordCredentials=dict(
                        username=auth_dict['username'],
                        password=auth_dict['password']
                    )
                )
            )

            self._data = json.dumps(data_json)
            self._curl_url = '{}/tokens'.format(auth_dict['auth_url'])

        self._headers = {'Content-Type': 'application/json'}

    def authenticate(self):

        urls = dict()
        try:
            response = requests.post(self._curl_url,
                                     headers=self._headers,
                                     data=self._data,
                                     verify=self._cacert)
            if '40' in str(response):
                verify = token = None
                return response.json(), token, verify
            else:
                if self._api_version == 'v2.0':
                    token = response.json()['access']['token']['id']
                    for service in response.json()['access']['serviceCatalog']:
                        for endpoint in service['endpoints']:
                            urls[service['name']] = dict(
                                adminURL=endpoint['adminURL'],
                                publicURL=endpoint['publicURL']
                            )
                            break
                else:
                    token = response.headers['X-Subject-Token']
                    for service in response.json()['token']['catalog']:
                        for endpoint in service['endpoints']:
                            if endpoint['interface'] == 'public':
                                urls[service['name']] = dict(publicURL=endpoint['url'])
                                break

        except requests.RequestException as error:
            sys.exit("Error: an Exception has occurred! {}".format(error))

        return urls, token, self._cacert
