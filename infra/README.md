# Déploiement Azure

[main.bicep](./main.bicep) crée : VNet (3 sous-réseaux + NSG), Container Apps (API), PostgreSQL Flexible Server privé,
Blob Storage privé (Private Endpoint), Azure Container Registry, Static Web Apps, Log Analytics et l'identité managée de l'API.

## 1. Infrastructure

```powershell
az group create -n rg-ffk -l francecentral
az deployment group create -g rg-ffk -f infra/main.bicep `
  -p postgresAdminPassword='<mot-de-passe-fort>' llmBaseUrl='<url>' llmModel='<modele>' llmApiKey='<cle>'
```

Les sorties donnent `acrName`, `containerAppName`, `staticWebAppName` et `apiUrl`.

## 2. Image du backend

Le premier déploiement utilise une image de démarrage. Construisez ensuite l'image du backend (un `Dockerfile` est
nécessaire dans `backend/`, lancé avec `uvicorn app.main:app --host 0.0.0.0 --port 8000`) :

```powershell
az acr build -r <acrName> -t ffk-api:1 backend
az deployment group create -g rg-ffk -f infra/main.bicep `
  -p postgresAdminPassword='<mot-de-passe-fort>' apiImage='<acrLoginServer>/ffk-api:1' ...
```

Repassez les mêmes paramètres à chaque déploiement, notamment `apiImage`.

## 3. Frontend

Compilez avec `VITE_API_URL=<apiUrl>`, puis déployez sur le Static Web App (jeton : `az staticwebapp secrets list -n <staticWebAppName>`).

## Points d'attention

- Le backend doit lire `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_STORAGE_CONTAINER` et `AZURE_CLIENT_ID`
  (classe `BlobStorage` avec `azure-storage-blob` et `azure-identity`, voir `app/storage.py`).
- Postgres et le stockage ne sont joignables que depuis le VNet : l'administration depuis un poste demande un bastion ou un VPN.
- L'API reste exposée publiquement (HTTPS) pour que le navigateur puisse l'appeler.
- Le VNet est fixé à la création de l'environnement Container Apps : changer le réseau impose de recréer l'environnement.
