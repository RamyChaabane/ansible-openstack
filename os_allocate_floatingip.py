#!/usr/bin/python

from ansible.module_utils.basic import *
import requests
import os_connect

class FloatingIP:

    def __init__(self, token, keystone_url, neutron_url, target_network, target_project, check_mode):
        self.neutron_url = neutron_url
        self.target_network = target_network
        self.check_mode = check_mode
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Auth-Token': token,
        }
        params = (
            ('name',  target_project),
        )
        self.target_project_id = requests.get(keystone_url + '/projects', headers=self.headers, params=params).json()['projects'][0]['id']

        params_project = (
            ('project_id', self.target_project_id),
        )
        self.floating_ip_list = requests.get(self.neutron_url + '/v2.0/floatingips', headers=self.headers, params=params_project).json()['floatingips']

    def create(self, count):

        if not self.floating_ip_list or len(self.floating_ip_list) < int(count):
            if self.check_mode:
                return True
            count_ip = int(count) - len(self.floating_ip_list)
            params = (
                ('name', self.target_network),
            )

            network_id = requests.get(self.neutron_url + '/v2.0/networks', headers=self.headers, params=params).json()['networks'][0]['id']
            data = '{"floatingip": {"floating_network_id": "' + network_id + '", "project_id": "' + self.target_project_id + '"}}'
            while count_ip > 0:
                count_ip -= 1
                try:
                    requests.post(self.neutron_url + '/v2.0/floatingips', headers=self.headers, data=data)
                except requests.exceptions.RequestException as error:
                    return error

            return True

        else:
            return False

    def delete(self):

        if self.floating_ip_list:
            if self.check_mode:
                return True
            try:
                for floating_ip in self.floating_ip_list:
                    requests.delete(self.neutron_url + '/v2.0/floatingips/' + floating_ip['id'], headers=self.headers)

            except requests.exceptions.RequestException as error:
                return error

            return True

        else:
            return False


def main():

    fields = {
        "network": {"required": True, "type": "str"},
        "state": {"default": "present", "choices": ['absent', 'present']},
        "count": {"default": "1"},
        "project": {"required": False, "type": "str"},
        "cloud": {"required": True, "type": "str"}
    }

    module = AnsibleModule(argument_spec=fields, supports_check_mode=True)
    urls, token = os_connect.Connect.authenticate(module.params['cloud'])
    floating_ip = FloatingIP(token, urls['keystone'], urls['neutron'], module.params['network'], module.params['project'], module.check_mode)

    if module.params['state'] == "present":
        result = floating_ip.create(module.params['count'])
    else:
        result = floating_ip.delete()

    if result:
        module.exit_json(changed=True, action=result)
    elif not result:
        module.exit_json(changed=False, action=result)
    else:
        module.fail_json(msg=result)


if __name__ == '__main__':
    main()
