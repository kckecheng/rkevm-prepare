import json
import jinja2

TEMPLATE = "cluster.yml.j2"
CONFIG = "config.json"

if __name__ == "__main__":
    # Load configuration
    with open(CONFIG) as cfg:
        config = json.loads(cfg.read())

    user = config["vm"]["user"]

    # Create nodes to be used by template
    names = []
    for i in range(config["vm"]["num"]):
        names.append(f"{config['vm']['nameprefix']}{i+1}")

    pubips = None
    intips = None
    for _, v in config["ip"].items():
        if v["usage"] == "public":
            pubips = v["pool"]
        elif v["usage"] == "internal":
            intips = v["pool"]
        else:
            continue

    nodes = []
    for i, name in enumerate(names):
        # Default config
        node = {
            "name": name,
            "public": "",
            "internal": "",
            "user": user,
            "iscontroller": False,
            "isworker": False,
            "isetcd": False,
        }

        node["public"] = pubips[i].split("/")[0]
        node["internal"] = intips[i].split("/")[0]
        if len(names) > 3:
            if i < 3:
                node["iscontroller"] = True
                node["isetcd"] = True
            else:
                node["isworker"] = True
        else:
            if i == 0:
                node["iscontroller"] = True
                node["isetcd"] = True
            else:
                node["isworker"] = True
        nodes.append(node)

    # Generate template
    fsloader = jinja2.FileSystemLoader(searchpath="./")
    env = jinja2.Environment(loader=fsloader, trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(TEMPLATE)
    rkeconfig = template.render(nodes=nodes)
    
    with open("cluster.yml", "w") as f:
        f.write(rkeconfig)
