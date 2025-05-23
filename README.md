# smart-k8s-monitor

A smart monitoring tool that watches Kubernetes deployments and uses AI to propose simple fixes when it detects issues.

## Phase 1: Setup

### Prerequisites

**Note**: If you already have Minikube installed and started you can skip this part.

1. Install Minikube

```shell
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-darwin-arm64
sudo install minikube-darwin-arm64 /usr/local/bin/minikube
```

1. Start Minikube

```shell
minikbube start
```

1. Check installation

```shell
$ kubectl get nodes
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   10m   v1.32.0
```

### Deploy a sample app

1. Deploy Nginx:

```shell
kubectl apply -f k8s/deployment.yaml
```

1. Check deployment:

```shell
$ kubectl get pods
NAME                              READY   STATUS    RESTARTS   AGE
nginx-deployment-96b9d695-4tks8   1/1     Running   0          22s
nginx-deployment-96b9d695-g4lwt   1/1     Running   0          22s
nginx-deployment-96b9d695-qjwvm   1/1     Running   0          22s
```

1. Deploy service to expose Nginx pods:

```shell
$ kubectl apply -f k8s/service.yaml
service/nginx-service created
```

### Ingress Controller Setup

1. Enable Minikube built-in addon for Ingress and create a tunnel.

```shell
$ minikube addons enable ingress
$ minikube tunnel
```

**Note**: This will install the nginx-ingress controller. To check if it deployed successfully run:

```shell
kubectl get pods -n ingress-nginx
```

By default, ingress-nginx-controller service is deployed as NodePort, and we need it to be LoadBalacer. So we need to change it:

```shell
kubectl edit svc ingress-nginx-controller -n ingress-nginx
```

1. Create a simple Ingress resource. This will route traffic from `http://my-nginx.local` to the nginx service on port 80.

```shell
kubectl apply -f k8s/ingress.yaml
```

**Note**: To fake DNS locally edit `/etc/hosts` file:

```shell
127.0.0.1 my-nginx.local
```

For more details about how does this work check `./docs/minikube-diagram.txt` and `./docs/ingress-networking-workflow.txt`.

### Structure so far

- `deployment.yaml` - nginx Deployemnt
- `service.yaml` - LoadBalancer Service
- `ingress.yaml` - Ingress for routing

## Phase 2: Monitoring and alerting

🌟 Goal: Install Prometheus (to scrape metrics) and Alertmanager (to send alerts).

**Note**: If you don't have *helm* already, try using brew to install it: `brew install helm`.

### 1. Add Prometheus Community Helm repo

```shell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### 2. Install Prometheus stack

This command will install:

- Prometheus
- Alertmanager
- Grafana
- kube-state-metrics
- node-exporter

```shell
helm install prometheus prometheus-community/kube-prometheus-stack
```

Command to get the admin password of Grafana:

```shell
kubectl --namespace default get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

Command to access Grafana local instance:

```shell
export POD_NAME=$(kubectl --namespace default get pod -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=prometheus" -oname)
kubectl --namespace default port-forward $POD_NAME 3000
```

Command to access the Prometheus UI:

```shell
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090
```

Even if the nginx app doesn't appear in the list of targets in Prometheus UI (because it is not configured to expose metrics via `/metrics` endpoint), we can still set up alerts using data from `kube-state-metrics`.

To create a Custom Alerting Rule that would watch for frequent pod restarts, we need to deploy a PrometheusRule CRD:

```shell
kubectl apply -f ./k8s/high-pod-restarts-rule.yaml
```

To test the alert we need to deploy a crashing pod.

```shell
kubectl apply -f ./k8s/crashy.yaml
```

The pod should have the status `CrashLoopBackOff` and, after a couple of minutes, the alert should be Firing.

### 3. Alert delivery via WebHooks

#### Start locally the alert receiver app

```shell
python3 ./ai-bot/alert_receiver.py
```

#### Expose the local Python server to your cluster using Ngrok

```shell
ngrok http 5000
```

You will be provided with a public URL like: `https://d207-2001-2044-120f-6f00-199d-9c43-f442-6627.ngrok-free.app`

To test if the Python server works as expected run the following request:

```shell
curl -X POST https://d207-2001-2044-120f-6f00-199d-9c43-f442-6627.ngrok-free.app/alert -H "Content-Type: application/json" -d '{"test": "hello"}'
```

In the logs of the local Python server you should see:

```nocode
🚨 Alert received!
{'test': 'hello'}
```

#### Update Alertmanager config

Update the Ngrok URL in the `./k8s/alertmanager-values.yaml` file and run:

```shell
helm upgrade prometheus prometheus-community/kube-prometheus-stack -f ./k8s/alertmanager-values.yaml
```

#### Send alert to Discord

Change the DISCORD_WEBHOOK_URL variable from the `ai-bot/alert_receiver.py` file to your own Discord Webhook URL.

#### Local LLM

For this project I will be deploying locally Ollama.
To install check `https://ollama.com/download`.
To run model `mistral` (a smaller version of llama3 model):

```commandline
ollama run mistral
```
