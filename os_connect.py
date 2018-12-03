#!/usr/bin/python

import requests
import yaml


class Connect:

    def __init__(self):
        pass

    @staticmethod
    def authenticate(cloud_name):

        clouds_path = '/etc/openstack/clouds.yaml'
        auth_dict = dict()

        try:
            auth_dict = yaml.load(open(clouds_path, 'r'))['clouds'][cloud_name]['auth']

        except IOError:
            clouds_path_list = clouds_path.split('.')
            clouds_path = clouds_path_list[0] + '.' + clouds_path_list[1].replace('yaml', 'yml')
            try:
                auth_dict = auth_dict = yaml.load(open(clouds_path, 'r'))['clouds'][cloud_name]['auth']
            except IOError:
                clouds_path = '~/.config/openstack'
                try:
                    auth_dict = yaml.load(open(clouds_path, 'r'))['clouds'][cloud_name]['auth']
                except IOError:
                    print 'no clouds.yaml has been found'
                    exit(2)

        finally:
            urls = dict()
            headers = {'Content-Type': 'application/json'}
            data = '{ "auth": { "identity": { "methods": ["password"],"password": {"user": {"domain": {"name": "' + auth_dict['user_domain_name'] + '"},"name": "' + auth_dict['username'] + '", "password": "' + auth_dict['password'] + '"} } }, "scope": { "project": { "domain": { "name": "' + auth_dict['project_domain_name'] + '" }, "name":  "' + auth_dict['project_name'] + '" } } }}'

            response = requests.post(auth_dict['auth_url'] + '/auth/tokens', headers=headers, data=data)
            token = response.headers['X-Subject-Token']

            for service in response.json()['token']['catalog']:
                    for endpoint in service['endpoints']:
                        if endpoint['interface'] == 'public':
                            urls[service['name']] = endpoint['url']
                            break

            return urls, token
