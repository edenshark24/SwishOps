# 🏀 SwishOps

An enterprise-grade, AI-powered Basketball Insights Platform built to demonstrate modern DevOps, cloud architecture, and infrastructure-as-code best practices.

---

## 🏗️ Tech Stack

* **Cloud & Infra:** AWS (EKS, RDS PostgreSQL, Lambda, ECR), Terraform (Modular)
* **CI/CD & Security:** Jenkins, SonarQube, Trivy (Vulnerability Scanning)
* **Orchestration:** Kubernetes, Helm 3 (Atomic deployments & HPA)
* **Microservices:** 
  * Backend: FastAPI (Python 3.11)
  * AI Service: FastAPI + NumPy/Pandas
  * Frontend: Node.js / Express
* **Observability:** Prometheus, Grafana, Alertmanager

---

## 🔐 Key Architectural & Security Highlights

* **Zero Hardcoded Secrets:** Sensitive keys (DB passwords, API keys, Grafana credentials) are dynamically fetched via **AWS Secrets Manager**.
* **Container Hardening:** All application containers run as unprivileged, **non-root users** to mitigate escape risks.
* **Automated Security Gates:** Jenkins pipelines block builds on `HIGH`/`CRITICAL` Trivy container vulnerabilities or SonarQube quality failures.
* **Resilient Infrastructure:** RDS instances bound to dedicated security groups; Helm upgrades protected by automatic `--atomic` rollbacks.

---

## 📁 Repository Structure

```text
SwishOps/
├── ai-service/          # Predictive analytics service (FastAPI)
├── backend/             # Core REST API & database service (FastAPI)
├── charts/              # Helm charts (Backend, AI Service, Frontend)
├── frontend/            # Node.js web client
├── jenkins/             # Jenkinsfile CI/CD pipeline
├── lambda/              # Serverless data ingestion worker
├── monitoring/          # Prometheus & Grafana configuration
└── terraform/           # Modular infrastructure definitions
