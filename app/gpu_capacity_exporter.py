from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from kubernetes import client, config
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

gpu_capacity = Gauge(
    'kubevirt_gpu_capacity',
    'GPU capacity per node (from node label)',
    ['node', 'gpu_type']
)

gpu_total_cluster_capacity = Gauge(
    'kubevirt_gpu_total_cluster_capacity',
    'Total GPU capacity per GPU type in the cluster',
    ['gpu_type']
)

gpu_reserved = Gauge(
    'kubevirt_gpu_reserved',
    'GPU reserved per node per GPU type',
    ['node', 'gpu_type']
)

gpu_free = Gauge(
    'kubevirt_gpu_free',
    'Remaining GPU free per node per GPU type',
    ['node', 'gpu_type']
)

# Track previously seen label combinations to handle removal when configs change
previous_node_gpu_info = {}

GPU_DEVICE_MAP = lambda gpu_type: gpu_type

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        elif parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            info_page = '''
<!DOCTYPE html>
<html>
<head>
    <title>GPU Capacity Exporter</title>
</head>
<body>
    <h1>GPU Capacity Exporter</h1>
    <p>This exporter provides GPU capacity metrics for supporting Kubevirt VM.</p>
    <p><a href="/metrics">View Metrics</a></p>
    <p>Metrics are updated every 10 seconds.</p>
</body>
</html>
'''
            self.wfile.write(info_page.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def fetch():
    global previous_node_gpu_info
    
    v1 = client.CoreV1Api()
    virt = client.CustomObjectsApi()

    # -------- 1. FETCH GPU TYPE & CAPACITY FROM LABEL --------
    nodes = v1.list_node()

    node_gpu_info = {}

    for node in nodes.items:
        labels = node.metadata.labels or {}

        if "gpu-type" not in labels or "gpu-capacity" not in labels:
            continue

        gpu_type = labels["gpu-type"]
        try:
            capacity = int(labels["gpu-capacity"])
        except:
            capacity = 0

        node_gpu_info[node.metadata.name] = {
            "gpu_type": gpu_type,
            "capacity": capacity
        }

        gpu_capacity.labels(
            node=node.metadata.name,
            gpu_type=gpu_type
        ).set(capacity)

    # -------- REMOVE STALE METRICS --------
    # Remove metrics for nodes that no longer exist or have changed GPU type
    for node_name, prev_info in previous_node_gpu_info.items():
        # If node no longer exists or has changed GPU type, remove old metrics
        if node_name not in node_gpu_info or node_gpu_info[node_name]["gpu_type"] != prev_info["gpu_type"]:
            try:
                gpu_capacity.remove(node_name, prev_info["gpu_type"])
                gpu_reserved.remove(node_name, prev_info["gpu_type"])
                gpu_free.remove(node_name, prev_info["gpu_type"])
            except KeyError:
                # Label combination didn't exist, ignore
                pass
    
    # Update previous_node_gpu_info for next iteration
    previous_node_gpu_info = node_gpu_info.copy()

    # -------- 2. TOTAL CLUSTER CAPACITY --------
    total_capacity = {}
    for node, info in node_gpu_info.items():
        gpu_type = info["gpu_type"]
        if gpu_type not in total_capacity:
            total_capacity[gpu_type] = 0
        total_capacity[gpu_type] += info["capacity"]
    
    # Remove stale total cluster capacity metrics
    # Get all current GPU types
    current_gpu_types = set(total_capacity.keys())
    # Get previous GPU types (from previous_node_gpu_info)
    previous_gpu_types = set(prev_info["gpu_type"] for prev_info in previous_node_gpu_info.values())
    
    # Remove metrics for GPU types that no longer exist in the cluster
    for gpu_type in previous_gpu_types:
        if gpu_type not in current_gpu_types:
            try:
                gpu_total_cluster_capacity.remove(gpu_type)
            except KeyError:
                # Label combination didn't exist, ignore
                pass
    
    # Publish total cluster capacity metrics
    for gpu_type, total in total_capacity.items():
        gpu_total_cluster_capacity.labels(gpu_type=gpu_type).set(total)

    # -------- 3. FETCH GPU RESERVED FROM VMI --------
    vmis = virt.list_cluster_custom_object(
        group="kubevirt.io",
        version="v1",
        plural="virtualmachineinstances"
    )

    reserved = {node: 0 for node in node_gpu_info}

    for vmi in vmis["items"]:
        nodeName = vmi.get("status", {}).get("nodeName")
        if nodeName not in reserved:
            continue

        devices = (
            vmi.get("spec", {})
               .get("domain", {})
               .get("devices", {})
               .get("hostDevices", [])
        )

        gpu_type = node_gpu_info[nodeName]["gpu_type"]
        expected_device = GPU_DEVICE_MAP(gpu_type)

        # count hostDevices that match gpu_type
        count = sum(1 for d in devices if d.get("deviceName") == expected_device)
        reserved[nodeName] += count

    for node, count in reserved.items():
        gpu_type = node_gpu_info[node]["gpu_type"]
        gpu_reserved.labels(node=node, gpu_type=gpu_type).set(count)

    # -------- 4. FREE GPU --------
    free = {}
    for node, info in node_gpu_info.items():
        free_gpu = max(info["capacity"] - reserved[node], 0)
        free[node] = free_gpu

        gpu_free.labels(node=node, gpu_type=info["gpu_type"]).set(free_gpu)

def main():
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

    # Start HTTP server in a separate thread
    from threading import Thread
    server = HTTPServer(('', 9100), MetricsHandler)
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print("GPU exporter running on :9100")

    while True:
        fetch()
        time.sleep(10)


if __name__ == "__main__":
    main()