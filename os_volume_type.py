from ansible.module_utils.basic import *
import requests
import os_connect
import json

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['stableinterface'],
                    'supported_by': 'ATOS'}

DOCUMENTATION = '''
---
module: os_volume_type
short_description: create a volume type
author: Rami CHAABANE
description:
    - create a volume type. 
      Volumes type can only be created using this module.
      Volumes types by default are non-encrypted
options:
   cloud:
     description:
       - Named cloud or cloud config to operate against.
         It references a named cloud config as defined in an OpenStack clouds.yaml file.
         Provides default values for auth and auth_type.
     required: true
   volume_type_name:
     description:
       - Volume type name that will be created
     required: true
   project:
     description:
       - Project that will gain access to this volume type
     required: true
   extra_spec:
     description:
       - The definition of a volume type. This is a group of policies
     required: false
   state:
     description:
       - Volume type can only be create
     default: present
   encrypted:
     description:
       - Whether the volume will be encrypted or decrypted
     default: False
     choices:
       - True
       - False
requirements:
    - "python >= 2.7"
'''

EXAMPLES = '''
# create volume type demo_type for project demo  
- os_volume_type:
    cloud:  overcloud
    volume_type_name: demo_type
    project: demo
    encrypted: false

# create an encrypted volume type demo_type_encrypted for project demo  
- os_volume_type:
    cloud:  overcloud
    volume_type_name: demo_type_encrypted
    project: demo
    encrypted: true
'''

RETURN = '''
  True if volume type has been created
'''


class VolumeType:

    def __init__(self,
                 token,
                 keystone_url,
                 cinder_url,
                 volume_type_name,
                 properties,
                 target_project,
                 check_mode,
                 verify):

        """
        :param token: token to connect to openstack services
        :param keystone_url: keystone endpoint v3
        :param cinder_url: cinder endpoint v3
        :param volume_type_name: volume type name to be deployed
        :param properties: properties of the volume type
        :param target_project: project that will have access to the volume type
        :param check_mode: ansible check mode
        :param verify: whether to verify SSL certificates
        """

        self.cinder_url = cinder_url
        self.keystone_url = keystone_url
        self.name = volume_type_name
        self.target_project = target_project
        self.check_mode = check_mode
        self.verify = verify

        self.properties = dict()
        if properties:
            for item in properties.split(","):
                key_value = item.split("=")
                self.properties[key_value[0]] = key_value[1]

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
        extra_spec = dict()

        # retrieve volume_type id if it has been already deployed
        # noinspection PyTypeChecker
        check = requests.get(self.cinder_url + '/types', headers=self.headers,
                             params=self.params, verify=self.verify).json()
        for volume in check['volume_types']:
            if volume['name'] == self.name:
                self.volume_type_id = volume['id']
                for key, value in volume['extra_specs'].iteritems():
                    extra_spec[key] = value
                break

        self.extra_spec_changed = False
        if cmp(self.properties, extra_spec) != 0:
            self.extra_spec_changed = True

    def create(self):

        """
        :return: return True when volume type is created/ will be created (check_mode) else False
        """

        if not self.volume_type_id:

            if self.check_mode:
                return True

            data = '{"volume_type": {"name": "' + self.name + \
                   '", "os-volume-type-access:is_public": false, "extra_specs": ' + \
                   json.dumps(self.properties) + '}}'
            try:
                create_api = '{}/types'.format(self.cinder_url)
                create = requests.post(create_api,
                                       headers=self.headers,
                                       data=data,
                                       verify=self.verify)

            except Exception as error:
                sys.exit(error)

            self.volume_type_id = create.json()['volume_type']['id']
            return True

        elif self.extra_spec_changed:

            try:
                volumes_api = "{}/volumes?all_tenants=True".format(self.cinder_url)
                volumes = requests.get(volumes_api,
                                       headers=self.headers,
                                       verify=self.verify).json()["volumes"]

                for volume in volumes:
                    volume_id = volume["id"]
                    volume_details_api = "{}/volumes/{}".format(self.cinder_url, volume_id)
                    volume_details = requests.get(volume_details_api,
                                                  headers=self.headers,
                                                  verify=self.verify).json()["volume"]

                    if volume_details["volume_type"] == self.name:
                        return "busy"

                if self.check_mode:
                    return True

                data = '{"extra_specs": ' + json.dumps(self.properties) + '}'
                extra_specs_api = '{}/types/{}/extra_specs'.format(self.cinder_url, self.volume_type_id)
                requests.post(extra_specs_api,
                              headers=self.headers,
                              data=data,
                              verify=self.verify)

            except Exception as error:
                sys.exit(error)
            return True

        else:
            return False

    def delete(self):

        """
        :return: return True when the volume is deleted/will be deleted (check_mode) else False
        """

        if self.volume_type_id:

            if self.check_mode:
                return True

            try:
                delete_api = '{}/types/{}'.format(self.cinder_url, self.volume_type_id)
                requests.delete(delete_api,
                                headers=self.headers,
                                verify=self.verify)
                return True

            except Exception as error:
                sys.exit(error)

        else:
            return False

    def access(self):

        """
        :return: return True when the target project gain/will gain (check_module) access to the volume type else False
        """

        if not self.volume_type_id and self.check_mode:
            return True

        # retrieve target project id
        params = (
            ('name', self.target_project),
        )

        try:

            # retrieve target project id
            projects_api = '{}/v3/projects'.format(self.keystone_url)
            target_project_id = requests.get(projects_api,
                                             headers=self.headers,
                                             params=params,
                                             verify=self.verify).json()['projects'][0]['id']

            # check if the volume type is accessible from a project,
            # if not give the target project access to this volume type else do nothing

            access_api = '{}/types/{}/os-volume-type-access'.format(self.cinder_url, self.volume_type_id)
            volume_type_access = requests.get(access_api,
                                              headers=self.headers,
                                              verify=self.verify).json()['volume_type_access']

            give_access_api = '{}/types/{}/action'.format(self.cinder_url, self.volume_type_id)
            if volume_type_access:
                if volume_type_access[0]['project_id'] != target_project_id:
                    if self.check_mode:
                        return True

                    data_json = dict(
                        removeProjectAccess=dict(
                            project=volume_type_access[0]['project_id']
                        )
                    )
                    data = json.dumps(data_json)

                    requests.post(give_access_api,
                                  headers=self.headers,
                                  data=data,
                                  verify=self.verify)

                    volume_type_access = dict()

            if not volume_type_access:
                if self.check_mode:
                    return True

                data_json = dict(
                    addProjectAccess=dict(
                        project=target_project_id
                    )
                )

                data = json.dumps(data_json)

                requests.post(give_access_api,
                              headers=self.headers,
                              data=data,
                              verify=self.verify)
                return True

            else:
                return False

        except Exception as error:
            sys.exit(error)

    def encrypt(self):

        """
        :return: return True when the volume type is encrypted/will be encrypted (check_mode) else False
        """

        try:
            # check if the volume type is already encrypted, if not, encrypt it else do nothing
            encryption_api = '{}/types/{}/encryption'.format(self.cinder_url, self.volume_type_id)
            volume_encryption = requests.get(encryption_api,
                                             headers=self.headers,
                                             verify=self.verify).json().get('volume_type_id')

            if volume_encryption is None:
                if self.check_mode:
                    return True

                data_json = dict(
                    encryption=dict(
                        control_location="front-end",
                        cipher="aes-xts-plain64",
                        key_size=512,
                        provider="nova.volume.encryptors.luks.LuksEncryptor"
                    )
                )

                data = json.dumps(data_json)
                requests.post(encryption_api,
                              headers=self.headers,
                              data=data,
                              verify=self.verify)
                return True
            else:
                return False

        except Exception as error:
            sys.exit(error)

    def decrypt(self):

        encryption_api = '{}/types/{}/encryption'.format(self.cinder_url, self.volume_type_id)
        volume_encryption = requests.get(encryption_api,
                                         headers=self.headers,
                                         verify=self.verify).json().get('encryption_id')

        if volume_encryption:
            if self.check_mode:
                return True

            encryption_api_del = '{}/{}'.format(encryption_api, volume_encryption)
            requests.delete(encryption_api_del,
                            headers=self.headers,
                            verify=self.verify)
            return True

        return False


def main():

    # module parameters
    fields = {
        "volume_type_name": {"required": True, "type": "str"},
        "cloud": {"required": True, "type": "str"},
        "project": {"required": True, "type": "str"},
        "extra_spec": {"default": "", "type": "str"},
        "state": {"default": "present", "choices": ['absent', 'present']},
        "encrypted": {"default": False, "choices": [True, False], "type": "bool"}
    }

    module = AnsibleModule(argument_spec=fields, supports_check_mode=True)

    # retrieve all openstack endpoints,
    # a token to connect to openstack services,
    # and whether we need to verify SSL certificates

    cloud_name = module.params['cloud']
    volume_type_name = module.params['volume_type_name']
    project = module.params['project']
    check_mode = module.check_mode
    is_encrypted = module.params['encrypted']
    state = module.params['state']

    urls, token, verify = os_connect.Connect(cloud_name).authenticate()

    keystone_endpoint = urls['keystone']['publicURL']
    cinder_v3_endpoint = urls['cinderv3']['publicURL']

    extra_spec = module.params['extra_spec']

    volume_type = VolumeType(token,
                             keystone_endpoint,
                             cinder_v3_endpoint,
                             volume_type_name,
                             extra_spec,
                             project,
                             check_mode,
                             verify)

    created = False
    project_access = False
    encrypted = False
    decrypted = False

    # if state is present, create the volume type, else delete it
    if state == "present":
        created = volume_type.create()
        if created == "busy":
            module.fail_json(msg="Failed to set volume type extra_specs: Volume Type is currently in use")

        if project is not None:
            project_access = volume_type.access()

        encrypted = volume_type.encrypt() if is_encrypted else volume_type.decrypt()

    else:
        deleted = volume_type.delete()
        module.exit_json(changed=deleted)

    # changed if result is True
    if created or project_access or encrypted or decrypted:
        module.exit_json(changed=True)
    else:
        module.exit_json(changed=False)


if __name__ == '__main__':
    main()
