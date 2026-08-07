# Multi-Agent Research — Azure Foundry Hosted Agent

A multi-agent research pipeline ported from the *Module 3 - Build Multi AI Agents Workflows* notebook and deployed as an Azure Foundry Hosted Agent.

**Pipeline:** User Query → Researcher (Tavily web search) → Analyst → Writer → Executive Report

---

## Project structure

```
hosted-agent/
├── src/
│   ├── main.py           # Agent entry point (ResponsesHostServer)
│   └── requirements.txt  # Python dependencies
├── azure.yaml            # Azure Developer CLI / Foundry configuration
├── .env.example          # Environment variable template (copy to .env)
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── deploy.yml    # GitHub Actions CI/CD pipeline
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Azure Developer CLI (`azd`) | ≥ 1.25 | [Install azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd) |
| Foundry azd extension | latest | `azd ext install microsoft.foundry` |
| Python | ≥ 3.10 | [python.org](https://www.python.org/downloads/) |
| Docker Desktop | latest | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Azure CLI | ≥ 2.80 | [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) |

You also need:
- An Azure subscription with the **Foundry Project Manager** role.
- A [Tavily API key](https://app.tavily.com) (free tier available).

---

## Local development

### 1. Create a virtual environment and install dependencies

```bash
cd hosted-agent
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r src/requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in FOUNDRY_PROJECT_ENDPOINT, AZURE_AI_MODEL_DEPLOYMENT_NAME, TAVILY_API_KEY
```

### 3. Authenticate with Azure

```bash
az login
azd auth login
```

### 4. Initialise the azd project (first time only)

```bash
azd ai agent init -m https://github.com/microsoft-foundry/foundry-samples/blob/main/samples/python/hosted-agents/agent-framework/responses/01-basic/azure.yaml
# Follow the prompts to pick / create a Foundry project and model deployment
```

### 5. Run the agent locally

```bash
azd ai agent run --no-inspector
```

The agent server starts at `http://localhost:8088`.

### 6. Invoke the local agent

```bash
# Using azd
azd ai agent invoke --local "What are the latest trends in AI agents?"

# Using curl
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "What are the latest trends in AI agents?"}'
```

---

## Deploy to Azure Foundry

### One-time deploy via CLI

```bash
# Provision cloud resources (first time only)
azd provision

# Deploy the agent
azd deploy

# Invoke the deployed agent
azd ai agent invoke "What are the latest trends in AI agents?"
```

### Monitor live logs

```bash
azd ai agent monitor
```

---

## GitHub Actions setup

The [deploy.yml](.github/workflows/deploy.yml) workflow runs on every push to `main` using **OIDC / Workload Identity Federation** — no client secrets stored in GitHub.

### Step 1 — Create a service principal

```bash
az ad sp create-for-rbac \
  --name "sp-multi-agent-research-cicd" \
  --role "Contributor" \
  --scopes "/subscriptions/<SUBSCRIPTION_ID>" \
  --json-auth
```

Note the output values: `clientId`, `tenantId`, `subscriptionId`.

### Step 2 — Add a federated credential

In the [Azure portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → your app → **Certificates & secrets** → **Federated credentials** → **Add credential**:

| Field | Value |
|-------|-------|
| Federated credential scenario | **GitHub Actions deploying Azure resources** |
| Organization | `<your-github-org>` |
| Repository | `<your-repo-name>` |
| Entity type | **Branch** |
| Branch | `main` |
| Name | `github-actions-main` |

### Step 3 — Add GitHub repository secrets

Go to **Settings → Secrets and variables → Actions** in your repository and add:

| Secret name | Value |
|-------------|-------|
| `AZURE_CLIENT_ID` | Service principal `clientId` |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `TAVILY_API_KEY` | Your Tavily API key |

### Step 4 — Add GitHub repository variables (optional)

| Variable name | Default | Description |
|---------------|---------|-------------|
| `AZURE_ENV_NAME` | `multi-agent-research-dev` | azd environment name |
| `AZURE_LOCATION` | `eastus2` | Azure deployment region |

### Step 5 — Push to main

Any push to `main` that changes `src/**`, `azure.yaml`, or the workflow file will trigger an automatic deployment. You can also run it manually via **Actions → Deploy Hosted Agent to Azure Foundry → Run workflow**.

---

## Environment variables reference

| Variable | Where set | Description |
|----------|-----------|-------------|
| `FOUNDRY_PROJECT_ENDPOINT` | Injected by platform at runtime | Foundry project URL — do **not** set in `azure.yaml` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | `azure.yaml` / `.env` | Name of the GPT model deployment |
| `TAVILY_API_KEY` | `azure.yaml` / `.env` | Tavily search API key |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Injected by platform at runtime | Application Insights telemetry |

> **Security tip:** Store `TAVILY_API_KEY` in a Foundry project connection (CustomKeys) instead of plain text.
> Replace the `TAVILY_API_KEY` entry in `azure.yaml` with:
> ```yaml
> - name: TAVILY_API_KEY
>   value: ${{connections.agent-secrets.credentials.tavily_api_key}}
> ```

---

## Troubleshooting

| Error code | Cause | Fix |
|------------|-------|-----|
| `image_pull_failed` | Project managed identity can't pull from ACR | Assign **Container Registry Repository Reader** to the project identity |
| `InvalidAcrPullCredentials` | Wrong registry RBAC | Re-check managed identity role assignment |
| `AcrImageNotFound` | Wrong image tag | Verify image name and tag in ACR |
| 401 from OpenAI endpoint | Agent identity missing RBAC | Assign **Cognitive Services OpenAI User** and **Azure AI User** roles to the agent identity |

Full reference: [Hosted agent permissions](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agent-permissions)

---

## References

- [Deploy a hosted agent — Microsoft Learn](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent?pivots=python)
- [Agent Framework samples](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework)
- [Manage hosted agent lifecycle](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-agent)
