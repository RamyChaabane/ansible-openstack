#!/usr/bin/python

from ansible.module_utils.basic import *
import requests
import os_connect


class VolumeType:

    def __init__(self, token, keystone_url, cinder_url, volume_type_name, properties, target_project, check_mode):
        self.cinder_url = cinder_url
        self.keystone_url = keystone_url
        self.name = volume_type_name
        self.properties = properties
        self.target_project = target_project
        self.check_mode = check_mode
        self.headers = {
            'User-Agent': 'python-cinderclient',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Auth-Token': token,
        }

        self.params = (
            ('is_public', 'none'),
        )

        self.volume_type_id = ''

        check = requests.get(self.cinder_url + '/types', headers=self.headers, params=self.params).json()
        for volume in check['volume_types']:
            if volume['name'] == self.name:
                self.volume_type_id = volume['id']
                break

    def create(self):

        if not self.volume_type_id:

            if self.check_mode:
                return True

            data = '{"volume_type": {"name": "' + self.name + '", "os-volume-type-access:is_public": false, "extra_specs": ' + self.properties + '}}'
            try:
                create = requests.post(self.cinder_url + '/types', headers=self.headers, data=data)
            except Exception as error:
                return error

            self.volume_type_id = create.json()['volume_type']['id']
            return True

        else:
            return False

    def delete(self):

        if self.volume_type_id:

            if self.check_mode:
                return True

            try:
                requests.delete(self.cinder_url + '/types/' + self.volume_type_id, headers=self.headers)
                return True
            except Exception as error:
                return error

        else:
            return False

    def access(self):

        # retrieve target project id
        params = (
            ('name',  self.target_project),
        )

        try:
            target_project_id = requests.get(self.keystone_url + '/projects', headers=self.headers, params=params).json()['projects'][0]['id']
            if not requests.get(self.cinder_url + '/types/' + self.volume_type_id + '/os-volume-type-access', headers=self.headers).json()['volume_type_access']:
                data = '{"addProjectAccess": {"project": "' + target_project_id + '"}}'
                requests.post(self.cinder_url + '/types/' + self.volume_type_id + '/action', headers=self.headers, data=data)
                return True
            else:
                return False

        except Exception as error:
            return error


def main():

    fields = {
        "volume_type_name": {"required": True, "type": "str"},
        "extra_spec": {"required": False, "type": "str"},
        "project": {"default": "", "type": "str"},
        "state": {"default": "present", "choices": ['absent', 'present']},
        "cloud": {"required": True, "type": "str"}
    }

    module = AnsibleModule(argument_spec=fields, supports_check_mode=True)
    urls, token = os_connect.Connect.authenticate(module.params['cloud'])
    items = module.params['extra_spec'].split("=")
    extra_spec = '{"' + items[0] + '": "' + items[1] + '"}'
    volume_type = VolumeType(token, urls['keystone'], urls['cinderv3'], module.params['volume_type_name'], extra_spec, module.params['project'], module.check_mode)

    if module.params['state'] == "present":
        result = volume_type.create()
        if module.params['project'] != "" and not module.check_mode:
            result = volume_type.access()
    else:
        result = volume_type.delete()

    if result:
        module.exit_json(changed=True, action=result)
    elif not result:
        module.exit_json(changed=False, action=result)
    else:
        module.fail_json(msg=result)


if __name__ == '__main__':
    main()
