// Infrastructure Azure de l'application FFK avec réseau privé.
//
//   Static Web Apps (React)  ──HTTPS──▶  Container Apps (API, sortie via le VNet)
//                                          ├─▶ PostgreSQL Flexible Server  (accès privé, sous-réseau délégué)
//                                          └─▶ Blob Storage                (Private Endpoint, identité managée)
//
// Déploiement : voir infra/README.md

targetScope = 'resourceGroup'

@description('Préfixe court utilisé dans le nom des ressources (minuscules et chiffres).')
@minLength(2)
@maxLength(8)
param baseName string = 'ffk'

@description('Région des ressources. Par défaut, celle du groupe de ressources.')
param location string = resourceGroup().location

@description('Région du Static Web App (liste restreinte : westeurope, westus2, centralus, eastus2, eastasia).')
param swaLocation string = 'westeurope'

@description('Image du backend (ex. acrffkxxxx.azurecr.io/ffk-api:1.0). Vide au premier déploiement : une image de démarrage est utilisée.')
param apiImage string = ''

@description('Nombre minimum de réplicas de l\'API. 0 = coût nul à l\'arrêt, mais démarrage à froid.')
@minValue(0)
param apiMinReplicas int = 0

@description('Identifiant administrateur PostgreSQL.')
param postgresAdminLogin string = 'ffkadmin'

@description('Mot de passe administrateur PostgreSQL (12 caractères minimum).')
@secure()
@minLength(12)
param postgresAdminPassword string

@description('Nom de la base PostgreSQL.')
param postgresDatabaseName string = 'ffk'

@description('Adresse de l\'API LLM compatible OpenAI (LLM_BASE_URL).')
param llmBaseUrl string = ''

@description('Modèle LLM (LLM_MODEL).')
param llmModel string = ''

@description('Clé de l\'API LLM (LLM_API_KEY). Laisser vide si le LLM n\'est pas encore configuré.')
@secure()
param llmApiKey string = ''

@description('Origines CORS supplémentaires, séparées par des virgules (le Static Web App est ajouté automatiquement).')
param extraCorsOrigins string = ''

var suffix = uniqueString(resourceGroup().id)
var storageContainerName = 'documents'
var usePlaceholderImage = empty(apiImage)
var apiPort = 8000

// Plages d'adresses du réseau
var vnetPrefix = '10.0.0.0/16'
var acaSubnetPrefix = '10.0.0.0/23'
var postgresSubnetPrefix = '10.0.2.0/27'
var privateEndpointSubnetPrefix = '10.0.3.0/27'

// Rôles Azure intégrés
var roleStorageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var roleAcrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

// ---------------------------------------------------------------------------
// Réseau : VNet, sous-réseaux et NSG
// ---------------------------------------------------------------------------

resource nsgAca 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${baseName}-aca'
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-Internet-HTTPS-HTTP'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: acaSubnetPrefix
          destinationPortRanges: ['80', '443']
        }
      }
    ]
  }
}

resource nsgPostgres 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${baseName}-postgres'
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-Aca-Postgres'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: acaSubnetPrefix
          sourcePortRange: '*'
          destinationAddressPrefix: postgresSubnetPrefix
          destinationPortRange: '5432'
        }
      }
      {
        name: 'Deny-Vnet-Postgres'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: postgresSubnetPrefix
          destinationPortRange: '5432'
        }
      }
    ]
  }
}

resource nsgPrivateEndpoints 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${baseName}-pe'
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-Aca-HTTPS'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: acaSubnetPrefix
          sourcePortRange: '*'
          destinationAddressPrefix: privateEndpointSubnetPrefix
          destinationPortRange: '443'
        }
      }
      {
        name: 'Deny-Vnet-HTTPS'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: privateEndpointSubnetPrefix
          destinationPortRange: '443'
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-${baseName}'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [vnetPrefix]
    }
    subnets: [
      {
        name: 'snet-aca'
        properties: {
          addressPrefix: acaSubnetPrefix
          networkSecurityGroup: { id: nsgAca.id }
          delegations: [
            {
              name: 'aca'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'snet-postgres'
        properties: {
          addressPrefix: postgresSubnetPrefix
          networkSecurityGroup: { id: nsgPostgres.id }
          delegations: [
            {
              name: 'postgres'
              properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' }
            }
          ]
        }
      }
      {
        name: 'snet-pe'
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          networkSecurityGroup: { id: nsgPrivateEndpoints.id }
          privateEndpointNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

resource acaSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: vnet
  name: 'snet-aca'
}

resource postgresSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: vnet
  name: 'snet-postgres'
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: vnet
  name: 'snet-pe'
}

// ---------------------------------------------------------------------------
// DNS privé (résolution des adresses privées de PostgreSQL et du Blob Storage)
// ---------------------------------------------------------------------------

resource dnsPostgres 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: '${baseName}.private.postgres.database.azure.com'
  location: 'global'
}

resource dnsPostgresLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: dnsPostgres
  name: 'link-${vnet.name}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

resource dnsBlob 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  location: 'global'
}

resource dnsBlobLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: dnsBlob
  name: 'link-${vnet.name}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

// ---------------------------------------------------------------------------
// Identité managée de l'API (accès au Blob Storage et au registre d'images)
// ---------------------------------------------------------------------------

resource apiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${baseName}-api'
  location: location
}

// ---------------------------------------------------------------------------
// Registre d'images
// ---------------------------------------------------------------------------

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${baseName}${suffix}'
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, apiIdentity.id, roleAcrPull)
  properties: {
    principalId: apiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleAcrPull)
  }
}

// ---------------------------------------------------------------------------
// Stockage des PDF : compte privé, sans clé, accessible seulement via Private Endpoint
// ---------------------------------------------------------------------------

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('st${baseName}${suffix}')
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: storageContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, apiIdentity.id, roleStorageBlobDataContributor)
  properties: {
    principalId: apiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageBlobDataContributor)
  }
}

resource blobPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${baseName}-blob'
  location: location
  properties: {
    subnet: { id: privateEndpointSubnet.id }
    privateLinkServiceConnections: [
      {
        name: 'blob'
        properties: {
          privateLinkServiceId: storage.id
          groupIds: ['blob']
        }
      }
    ]
  }
}

resource blobDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: blobPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob'
        properties: { privateDnsZoneId: dnsBlob.id }
      }
    ]
  }
  dependsOn: [dnsBlobLink]
}

// ---------------------------------------------------------------------------
// PostgreSQL Flexible Server (accès privé uniquement)
// ---------------------------------------------------------------------------

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: 'psql-${baseName}-${suffix}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: { mode: 'Disabled' }
    network: {
      delegatedSubnetResourceId: postgresSubnet.id
      privateDnsZoneArmResourceId: dnsPostgres.id
      publicNetworkAccess: 'Disabled'
    }
  }
  dependsOn: [dnsPostgresLink]
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: postgresDatabaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ---------------------------------------------------------------------------
// Journaux et environnement Container Apps (intégré au VNet)
// ---------------------------------------------------------------------------

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${baseName}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource acaEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${baseName}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: acaSubnet.id
      internal: false
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Frontend : Static Web Apps
// ---------------------------------------------------------------------------

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: 'swa-${baseName}-${suffix}'
  location: swaLocation
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {}
}

// ---------------------------------------------------------------------------
// API : Container App
// ---------------------------------------------------------------------------

var corsOrigins = empty(extraCorsOrigins)
  ? 'https://${staticWebApp.properties.defaultHostname}'
  : 'https://${staticWebApp.properties.defaultHostname},${extraCorsOrigins}'

var databaseUrl = 'postgresql+psycopg://${postgresAdminLogin}:${uriComponent(postgresAdminPassword)}@${postgres.properties.fullyQualifiedDomainName}:5432/${postgresDatabaseName}?sslmode=require'

var llmSecrets = empty(llmApiKey) ? [] : [
  {
    name: 'llm-api-key'
    value: llmApiKey
  }
]

var llmEnv = empty(llmApiKey) ? [] : [
  {
    name: 'LLM_API_KEY'
    secretRef: 'llm-api-key'
  }
]

var apiProbes = usePlaceholderImage ? [] : [
  {
    type: 'Liveness'
    httpGet: {
      path: '/health/live'
      port: apiPort
    }
    periodSeconds: 30
  }
  {
    type: 'Readiness'
    httpGet: {
      path: '/health/ready'
      port: apiPort
    }
    periodSeconds: 10
  }
]

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${baseName}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${apiIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: acaEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: usePlaceholderImage ? 80 : apiPort
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: apiIdentity.id
        }
      ]
      secrets: concat(
        [
          {
            name: 'database-url'
            value: databaseUrl
          }
        ],
        llmSecrets
      )
    }
    template: {
      containers: [
        {
          name: 'api'
          image: usePlaceholderImage ? 'mcr.microsoft.com/k8se/quickstart:latest' : apiImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(
            [
              { name: 'DATABASE_URL', secretRef: 'database-url' }
              { name: 'CORS_ORIGINS', value: corsOrigins }
              { name: 'LLM_BASE_URL', value: llmBaseUrl }
              { name: 'LLM_MODEL', value: llmModel }
              { name: 'AZURE_STORAGE_ACCOUNT_URL', value: storage.properties.primaryEndpoints.blob }
              { name: 'AZURE_STORAGE_CONTAINER', value: storageContainerName }
              { name: 'AZURE_CLIENT_ID', value: apiIdentity.properties.clientId }
            ],
            llmEnv
          )
          probes: apiProbes
        }
      ]
      scale: {
        minReplicas: apiMinReplicas
        maxReplicas: 3
        rules: [
          {
            name: 'http'
            http: { metadata: { concurrentRequests: '30' } }
          }
        ]
      }
    }
  }
  dependsOn: [
    acrPullAssignment
    storageRoleAssignment
    database
    blobDnsGroup
  ]
}

// ---------------------------------------------------------------------------
// Sorties
// ---------------------------------------------------------------------------

output apiUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
output staticWebAppName string = staticWebApp.name
output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output containerAppName string = api.name
output storageAccountName string = storage.name
output postgresHost string = postgres.properties.fullyQualifiedDomainName
