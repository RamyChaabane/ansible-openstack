from ansible.module_utils.basic import *
import requests
import os_connect

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': ''
}

DOCUMENTATION = '''
---
module: os_allocate_floatingip
short_description: Manage OpenStack floating ip
version_added: "2.7"
description:
    - "Create, update and delete floating ips"
    - "A server is not required to create floating ips"
options:
    cloud:
        description:
            - OpenStack authentication parameters
        required: true
    network:
        description:
            - name of the network where the floating ip will be created/deleted
        required: true
    state:
        description:
            - state of the floating ip: present=created|absent=deleted
        default: present
        choices:
            - present
            - absent
    project:
        description:
            - name of the project that the floating ip will belongs to (default to admin project) 
        required: False
    count:
        description:
            - set the number of floating ips that will be created/deleted (default = 1)
        required: False
author:
    - Ramy CHAABANE
'''

EXAMPLES = '''
- name: Create 10 floating ip addresses
  os_allocate_floatingip:
    cloud: overcloud
    project: demo
    state: present
    count:  10
    network: privnet

- name: Delete floating ip address
  os_allocate_floatingip:
    cloud: overcloud
    project: demo
    state: present
    network: privnet
'''


class FloatingIP:

    def __init__(self,
                 token,
                 keystone_url,
                 neutron_url,
                 target_network,
                 target_project,
                 check_mode,
                 verify):

        self.neutron_url = neutron_url
        self.target_network = target_network
        self.check_mode = check_mode
        self.verify = verify

        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Auth-Token': token,
        }
        params = (
            ('name', target_project),
        )

        projects_api = '{}/v3/projects'.format(keystone_url)
        self.target_project_id = requests.get(projects_api,
                                              headers=self.headers,
                                              params=params,
                                              verify=self.verify).json()['projects'][0]['id']

        params_project = (
            ('project_id', self.target_project_id),
        )

        self.floating_api = '{}/v2.0/floatingips'.format(self.neutron_url)
        self.floating_ip_list = requests.get(self.floating_api,
                                             headers=self.headers,
                                             params=params_project,
                                             verify=self.verify).json()['floatingips']

    def create(self, count):

        if not self.floating_ip_list or len(self.floating_ip_list) < int(count):
            if self.check_mode:
                return True
            count_ip = int(count) - len(self.floating_ip_list)

            params = (
                ('name', self.target_network),
            )

            networks_api = '{}/v2.0/networks'.format(self.neutron_url)
            network_id = requests.get(networks_api,
                                      headers=self.headers,
                                      params=params,
                                      verify=self.verify).json()['networks'][0]['id']

            data_json = dict(
                floatingip=dict(
                    floating_network_id=network_id,
                    project_id=self.target_project_id
                )
            )

            data = json.dumps(data_json)

            while count_ip > 0:
                count_ip -= 1
                try:
                    requests.post(self.floating_api,
                                  headers=self.headers,
                                  data=data,
                                  verify=self.verify)

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
                    floating_api_del = '{}/{}'.format(self.floating_api, floating_ip['id'])
                    requests.delete(floating_api_del,
                                    headers=self.headers,
                                    verify=self.verify)

            except requests.exceptions.RequestException as error:
                return error

            return True

        else:
            return False


def main():
    fields = {
        "network": {"required": True, "type": "str"},
        "state": {"default": "present", "choices": ['absent', 'present']},
        "count": {"default": "1", "type": "str"},
        "project": {"required": False, "type": "str"},
        "cloud": {"required": True, "type": "str"}
    }

    module = AnsibleModule(argument_spec=fields, supports_check_mode=True)

    network_name = module.params['network']
    cloud_name = module.params['cloud']
    state = module.params['state']
    project_name = module.params['project']
    count = int(module.params['count'])
    check_mode = module.check_mode

    urls, token, verify = os_connect.Connect(cloud_name).authenticate()

    keystone_endpoint = urls['keystone']['publicURL']
    neutron_endpoint = urls['neutron']['publicURL']

    floating_ip = FloatingIP(token,
                             keystone_endpoint,
                             neutron_endpoint,
                             network_name,
                             project_name,
                             check_mode,
                             verify)

    if state == "present":
        result = floating_ip.create(count)
    else:
        if count != 1:
            module.fail_json(msq="count parameter should be excluded")
        result = floating_ip.delete()

    if isinstance(result, bool):
        module.exit_json(changed=result)
    else:
        module.fail_json(msg=result)


if __name__ == '__main__':
    main()
