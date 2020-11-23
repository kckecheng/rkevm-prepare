import subprocess
import os
import logging
import json
import tempfile
import time


GOVC_EXE = "/usr/local/bin/govc"

# Run govc command
def run(command=[], capture_output=True):
    logging.info(f"Run command {command}")
    ret = subprocess.run(command, capture_output=capture_output)
    msg = f"Fail to execute {command}"
    if capture_output:
        if ret.returncode != 0:
            stderr = ret.stderr.decode()
            if stderr != "":
                return stderr
            else:
                return msg
    else:
        if ret.returncode != 0:
            return msg
    return None


# Create num. of VM names with the same prefix, such as ["abc1", "abc2", ...]
def create_names(prefix, num=8):
    names = []
    for i in range(num):
        names.append(f"{prefix}{i+1}")
    return names


# Create len(names) x VMs by clone the base VM
def clone_vm(base, name):
    command = [GOVC_EXE, "vm.clone", "-vm", base, name]
    logging.info(f"Clone VM {name} based on {base}")
    ret = run(command, True)
    if ret:
        logging.error(f"Fail to clone vm {name} due to {ret}")
    else:
        logging.info(f"Successfully clone VM {name}")


# Poweron VM
def poweron_vm(name):
    # Linux pipe cannot be used with subprocess.run
    command = [GOVC_EXE, "vm.info", "-g", "-json", name]
    ret = subprocess.run(command, capture_output=True)
    if ret.returncode != 0:
        msg = ret.stderr.decode()
        logging.error(f"Fail to check the power status of {name} due to {msg}")
    else:
        try:
            info = json.loads(ret.stdout.decode())
            msg = info["VirtualMachines"][0]["Runtime"]["PowerState"]
        except:
            msg = None

        if msg and msg == "poweredOn":
            logging.info(f"VM {name} is already powered on")
        else:
            ret = subprocess.run(
                [GOVC_EXE, "vm.power", "-on", name], capture_output=True
            )
            if ret.returncode != 0:
                logging.error(
                    f"Fail to power on VM {name}, please check the VM manually"
                )
            else:
                logging.info(f"VM {name} is successfully powered on")


# Reboot VM
def poweroff_vm(name):
    command = [GOVC_EXE, "vm.power", "-off", "-force", name]
    logging.info(f"Poweroff VM {name}")
    ret = run(command, False)
    if ret:
        logging.error(f"Fail to power off VM {name}")


# Configure hostname
def configure_hostname(name):
    command = [GOVC_EXE, "guest.run", "-vm", name, "hostnamectl", "set-hostname", name]
    logging.info(f"Configure {name} with hostname {name}")
    ret = run(command, False)
    if ret:
        logging.error(f"Fail to set hostname for VM {name}")


# create hosts file
def create_hosts(names, ips):
    hosts = []
    for ip, name in zip(ips, names):
        address = ip.split("/")[0]
        hosts.append(f"{address} {name}")

    hosts.append(
        "127.0.0.1 localhost localhost.localdomain localhost4 localhost4.localdomain4"
    )

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.writelines([(x + "\n").encode() for x in hosts])
    f.close()
    return f.name


# Upload file to a VM
def upload_file(name, srcpath, dstpath):
    command = [GOVC_EXE, "guest.upload", "-f", f"-vm={name}", srcpath, dstpath]
    logging.info(f"Upload file {dstpath} onto VM {name}")
    ret = run(command, False)
    if ret:
        logging.error(f"Fail to upload {dstpath} onto VM {name}")


# Update IQN
def update_iqn(name):
    iqn = "InitiatorName=iqn.1994-05.com.redhat:" + name

    logging.info(f"Create IQN {iqn}")
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(iqn.encode())
    f.close()
    upload_file(name, f.name, "/etc/iscsi/initiatorname.iscsi")

    logging.info(f"Restart iscsid on {name} to make changes take effect")
    command = [GOVC_EXE, "guest.run", "-vm", name, "systemctl", "restart", "iscsid"]
    ret = run(command, False)
    if ret:
        logging.error(f"Fail to restart iscsid on {name}, please restart it manually")


# Configure network
def configure_ip(name, nic, ip, gateway, public=False):
    command = [
        GOVC_EXE,
        "guest.run",
        "-vm",
        name,
    ]

    if public:
        ndefault = "false"
    else:
        ndefault = "true"
    command_nmcli = f"nmcli con mod {nic} ipv4.method static ipv4.addresses {ip} ipv4.gateway {gateway} ipv4.never-default {ndefault}"
    command.extend(command_nmcli.split())

    logging.info(f"Run command on VM {name}: {command_nmcli}")
    ret = run(command)
    if ret:
        logging.error(
            f"Fail to configure VM {name} on NIC {nic} with IP {ip} and gateway {gateway} due to {ret}"
        )

    logging.info(f"Reconnect NIC {nic} on VM {name} to activate the configured IP {ip}")
    ret = run([GOVC_EXE, "guest.run", "-vm", name, "nmcli", "con", "up", nic])
    if ret:
        logging.error(f"Fail to reconnect NIC {nic} on VM {name} due to {ret}")


if __name__ == "__main__":
    # Gloabl logging level
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )

    with open("config.json") as f:
        contents = f.read()
        config = json.loads(contents)

    # govc env vars
    os.environ["GOVC_URL"] = config["vsphere"]["vcenter"]
    os.environ["GOVC_USERNAME"] = config["vsphere"]["user"]
    os.environ["GOVC_PASSWORD"] = config["vsphere"]["password"]
    os.environ["GOVC_INSECURE"] = config["vsphere"]["insecure"]
    os.environ["GOVC_DATACENTER"] = config["vsphere"]["datacenter"]
    os.environ["GOVC_DATASTORE"] = config["vsphere"]["datastore"]
    os.environ["GOVC_RESOURCE_POOL"] = config["vsphere"]["respool"]
    os.environ["GOVC_GUEST_LOGIN"] = config["vsphere"]["guestcredential"]

    # Generate VM names
    names = create_names(config["vm"]["nameprefix"], config["vm"]["num"])
    logging.info(f"Generate VM names: {names}")

    # Clone and power on VM
    for name in names:
        clone_vm(config["vm"]["base"], name)
        poweron_vm(name)

    logging.info("Sleep for 3 minutes to make sure all VMs are up online")
    time.sleep(180)

    # Create hosts file
    ips = None
    for _, conf in config["ip"].items():
        if conf["usage"] == "public":
            ips = conf["pool"]

    hosts = create_hosts(names, ips)

    # Configure hostname, iqn, /etc/hosts, ip addresses
    for index, name in enumerate(names):
        configure_hostname(name)
        update_iqn(name)
        upload_file(name, hosts, "/etc/hosts")

        for nic, conf in config["ip"].items():
            if conf["usage"] == "public":
                public = True
            else:
                public = False
            configure_ip(name, nic, conf["pool"][index], conf["gateway"], public=public)

    for name in names:
        poweroff_vm(name)
        poweron_vm(name)

    logging.info(
        "Please wait until all VMs come back online before the next step (create rke cluster.yml)"
    )
