# Smart K8s Monitor

An AI-enhanced Kubernetes monitoring tool that detects issues (e.g., frequent pod restarts) and uses a local LLM to propose fixes, sending notifications to Discord.

---

## Architecture Diagram

```ignorelang
            +-----------------+
            |  Kubernetes     |
            |  Cluster (Minikube)
            +--------+--------+
                     |
                +----v----+
                | NGINX    |  <-- Sample App
                +----+----+
                     |
     +---------------v---------------+
     |     Prometheus + Alertmanager |
     +---------------+---------------+
                     |
         Webhook (HTTP POST alert)
                     |
           +---------v----------+
           |  Flask Alert Bot   |
           |  (Python + LLM)    |
           +---------+----------+
                     |
       +-------------v-------------+
       |  Mistral via Ollama LLM   |
       +-------------+-------------+
                     |
       +-------------v-------------+
       |        Discord Channel     |
       +----------------------------+
```

---

## Project Overview

This project sets up a smart Kubernetes monitoring pipeline with:

- Prometheus for metrics
- Alertmanager for alerting
- Discord for notifications
- A locally hosted LLM (via Ollama) for AI-generated suggestions

---

## Project Structure

```ignorelang
smart-k8s-monitor/
├── ai-bot/
│ └── alert_receiver.py # Flask app that receives alerts, calls LLM, and posts to Discord
├── k8s/
│ ├── deployment.yaml # nginx Deployment
│ ├── service.yaml # LoadBalancer Service
│ ├── ingress.yaml # Ingress route
│ ├── crashy.yaml # Crashing pod to trigger alerts
│ ├── high-pod-restarts-rule.yaml # Custom PrometheusRule
│ └── alertmanager-values.yaml # Custom Alertmanager config
└── docs/
└── (networking diagrams and notes)
```

---

## Quick Setup Instructions

### Prerequisites

- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [Helm](https://helm.sh/docs/intro/install/)
- [Python 3](https://www.python.org/downloads/)
- [Ngrok](https://ngrok.com)
- [Ollama](https://ollama.com/download)


### Run the project

```bash
git clone https://github.com/cristina-sirbu/smart-k8s-monitor.git
cd smart-k8s-monitor

minikube start  # Start your local Kubernetes cluster using Minikube

kubectl apply -f k8s/deployment.yaml  # Deploy the NGINX sample app using the Deployment resource
kubectl apply -f k8s/service.yaml  # Create a LoadBalancer service to expose the NGINX app

minikube addons enable ingress  # Enable the built-in ingress addon for routing HTTP traffic
minikube tunnel  # Opens a tunnel to allow access to LoadBalancer services from localhost
# By default, ingress-nginx-controller service is deployed as NodePort, and we need it to be LoadBalacer.
kubectl edit svc ingress-nginx-controller -n ingress-nginx  # Edit the ingress controller service to change its type to LoadBalancer
kubectl apply -f k8s/ingress.yaml  # Apply the ingress rule that routes my-nginx.local to the NGINX service
```

**Note**: To fake DNS locally edit `/etc/hosts` file:

```shell
127.0.0.1 my-nginx.local
```

For more details about how does this work check `./docs/minikube-diagram.txt` and `./docs/ingress-networking-workflow.txt`.

Then install Prometheus (to scrape metrics) and Alertmanager (to send alerts).:

```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack  # Deploy the Prometheus monitoring stack with Alertmanager and Grafana
# The kube-prometheus-stack helm chart will install: Prometheus, Alertmanager, Grafana, kube-state-metrics and node-exporter.

kubectl apply -f k8s/high-pod-restarts-rule.yaml  # Apply a custom rule that triggers an alert on frequent pod restarts

kubectl apply -f k8s/crashy.yaml  # Deploy a pod that simulates failure to trigger alerts
# The pod should have the status `CrashLoopBackOff` and, after a couple of minutes, the alert should be Firing.
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

Change the DISCORD_WEBHOOK_URL variable from the `ai-bot/alert_receiver.py` file to your own Discord Webhook URL.
Then start your Python app:

```shell
python3 ai-bot/alert_receiver.py  # Run the Flask app that receives alerts and sends AI-enhanced responses to Discord
```

Expose the local Python server to your cluster using Ngrok:

```shell
ngrok http 5000
```

You will be provided with a public URL like: `https://d207-2001-2044-120f-6f00-199d-9c43-f442-6627.ngrok-free.app`

Update the Ngrok URL in the `./k8s/alertmanager-values.yaml` file and run:

```shell
helm upgrade prometheus prometheus-community/kube-prometheus-stack -f ./k8s/alertmanager-values.yaml
```

To run model `mistral` (a smaller version of llama3 model):

```commandline
ollama run mistral
```

That’s it! Alerts from Kubernetes will be analyzed by your local LLM and posted to your Discord.

### Result

When an alert like HighPodRestarts is triggered:
- Alertmanager sends it to the Flask app
- Flask sends it to Mistral for advice
- The response is posted to Discord

You're now running a fully local, AI-assisted Kubernetes alerting system 🚀

### Cleanup

To remove all components and reclaim local resources after you're done testing:

```shell
# Uninstall Prometheus stack
helm uninstall prometheus

# Delete deployed Kubernetes resources
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/service.yaml
kubectl delete -f k8s/ingress.yaml
kubectl delete -f k8s/crashy.yaml
kubectl delete -f k8s/high-pod-restarts-rule.yaml

# Disable and clean up Minikube
minikube addons disable ingress
minikube stop
minikube delete

# (Optional) Delete Ollama models to free disk space
rm -rf ~/.ollama/models
```