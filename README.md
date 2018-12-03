# ansible-openstack-modules-API
Even with the latest version of ansible (2.7), not all openstack modules has been devoplopped by the community.

For this reason, I created two openstack custom modules:
  - os_volume_type: create/update/delete a volume type
  - os_allocate_floatingip: create/update/delete a number of floating ips associated to a given network. The server existance with this module is irrelevent

Those modules have been developped using:
  - python 2.7 (should work with 3.6)
  - OpenStack API (I didn't use openstacksdk library as the community do)
  - only public endpoints are supported
