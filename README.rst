About
=======

We need to creat Kubernetes clusters based on VMware VMs frequently for test purpose. The work is easy, but the process is tedious.

This project will help:

- Clone VMs from the same VM template which works smoothly as a Kubernetes controller/node;
- Configure hostname, IP, /etc/hosts, IQN, etc. accordingly for the cloned VMs;
- Create a Rancher rke cluster.yml for Kubernetes deployment.

Usage
------

#. Prepare a base VM:

   - Make sure the VM configuration meets rke OS requirements https://rancher.com/docs/rke/latest/en/os/;
   - Configure NTP accordingly;
   - Prepare a user with sudo privilege;
   - Create credential for the root user;
   - Enable SSH and generate a SSH key;
   - Attach vNIC ports to necessary port groups;
   - Download and install the rke binary as /usr/local/bin/rke;

#. Download this application to a Linux:

   - Intall govc binary as /usr/local/bin/govc;
   - Make sure python 3.8+ is available;
#. Change config.json accordingly;
#. Change the cluster.yml.j2 accordingly;
#. Clone and configure VMs:

   ::

     python deploy.py

#. Create rke config:

   ::

     pip install -r requirements.txt
     python confgen.py

#. Create a Kubernetes cluster:

   ::

     scp cluster.yml <sudo user>@<Public IP of any VM>:rke/cluster.yml
     ssh <sudo user>@<Public IP of any VM>
     cd rke
     rke up

#. Verify:

   ::

     cp kube_config_cluster.yml ~/.kube/config
     kubectl get nodes -o wide

#. Done
