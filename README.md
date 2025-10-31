# GPU Capacity Exporter

## Overview
Collects GPU capacity, reserved, free metrics from Kubernetes nodes and KubeVirt VMIs

## Disclaimer
> This repository is provided for hobby and educational purposes only. If you plan to use it in a production environment, it will most likely require significant customization, testing, and security audits. Please fork and build your own application.

## Features
- Dynamic GPU type detection via node labels
- Metrics for total capacity, reserved, and free GPUs per node
- Flexible GPU device matching (can adjust mapping)

---

## Node Labels
Add the following labels to GPU nodes:

### Example GPU NVIDIA node
```
kubectl label node node01 gpu-type=NVIDIA-H200-SXM
kubectl label node node01 gpu-capacity=8
```

### Example GPU AMD node
```
kubectl label node node02 gpu-type=AMD-INSTINCT-MI300X
kubectl label node node02 gpu-capacity=8
```

### Example GPU INTEL node
```
kubectl label node node03 gpu-type=INTEL-DCGPU-MAX1550
kubectl label node node03 gpu-capacity=8
```

- `gpu-type` = GPU type
- `gpu-capacity` = number of GPUs

---

## Metrics
### 1. GPU Node Capacity
```
kubevirt_gpu_capacity{gpu_type="NVIDIA-H200-SXM",node="node01"} 8.0
kubevirt_gpu_capacity{gpu_type="AMD-INSTINCT-MI300X",node="node02"} 8.0
kubevirt_gpu_capacity{gpu_type="INTEL-DCGPU-MAX1550",node="node03"} 8.0
```

### 2. GPU Total Cluster Capacity
```
kubevirt_gpu_total_cluster_capacity{gpu_type="NVIDIA-H200-SXM"} 8.0
kubevirt_gpu_total_cluster_capacity{gpu_type="AMD-INSTINCT-MI300X"} 8.0
kubevirt_gpu_total_cluster_capacity{gpu_type="INTEL-DCGPU-MAX1550"} 8.0
```

### 3. GPU Reserved by KubeVirt VMI
```
kubevirt_gpu_reserved{gpu_type="NVIDIA-H200-SXM",node="node01"} 4.0
kubevirt_gpu_reserved{gpu_type="AMD-INSTINCT-MI300X",node="node02"} 2.0
kubevirt_gpu_reserved{gpu_type="INTEL-DCGPU-MAX1550",node="node03"} 1.0
```

### 4. GPU Free Usage
```
kubevirt_gpu_free{gpu_type="NVIDIA-H200-SXM",node="node01"} 8.0
kubevirt_gpu_free{gpu_type="AMD-INSTINCT-MI300X",node="node02"} 8.0
kubevirt_gpu_free{gpu_type="INTEL-DCGPU-MAX1550",node="node03"} 8.0
```

---

## Running the Exporter
### Kubernetes deploy

```sh
kubectl apply -f manifests/rbac.yaml
kubectl apply -f manifests/service.yaml
kubectl apply -f manifests/deployment.yaml
kubectl apply -f manifests/serviceMonitor.yaml
```

Expose port 9100 to Prometheus.
