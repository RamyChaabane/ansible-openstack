# ansible-openstack-modules-API
With the latest version of ansible (2.7), not all OpenStack modules has been developed by the community.

I created the two following OpenStack custom modules:
  - __os_volume_type__: create/update/delete a volume type
  - __os_allocate_floatingip__: create/update/delete a number of floating ips associated to a given network. The server existence with this module is irrelevent

Those modules have been developped using:
  - python 2.7 (should work with 3.6)
  - OpenStack API (I didn't use openstacksdk library as the community would do)
  - only public endpoints are supported

Those modules are based on os_connect.py script that retrieves OpenStack endpoints with a token to authenticate to OpenStack services. This script should be placed under /usr/lib/python2.7/site_packages/
