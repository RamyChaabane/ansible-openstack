# ansible-openstack
With the latest version of ansible (2.9), not all OpenStack modules have been developed by the community.

I created the two following OpenStack custom modules:
  - __os_volume_type__: manage a volume type: create update, delete, encrypt and decrypt a volume type
  - __os_allocate_floatingip__: create/update/delete a number of floating ips associated to a given network. The server existence with this module is irrelevent

Those modules have been developed using:
  - Python 2.7
  - OpenStack APIv3

Those modules are based on os_connect.py script that retrieves:
  - OpenStack endpoints
  - Token to authenticate to OpenStack services.
  - Whether we need to verify SSL communication

This script should be added to Python path

__Examples__:

Module os_volume_type:
```
- name: Create a volume Type
  os_volume_type:
    cloud: overcloud
    volume_type_name: volumetype01
    state: present
    project: demo
    extra_spec: volume_backend_name='backend01'
    
- name: Delete a volume Type
  os_volume_type:
    cloud: overcloud
    volume_type_name: volumetype02
    state: absent
```
Module os_allocate_floatingip:
```
- name: Create 10 floating ip addresses
  os_allocate_floatingip:
    cloud: overcloud
    project: demo
    state: present
    count:  10
    network: privatenet
    
- name: Delete floating ip address
  os_allocate_floatingip:
    cloud: overcloud
    project: demo
    state: present
    network: privatenet
```
