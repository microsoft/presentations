@description('Name of the foundry resource')
param foundryName string

@description('Name of the Bing Grounding resource')
param bingName string

@description('Location for all resources')
param location string

@description('Chat model deployment name')
param modelDeploymentName string

@description('Chat model name')
param modelName string

@description('Chat model version')
param modelVersion string

@description('Chat model capacity')
param modelCapacity int

@description('Image model deployment name')
param imageModelDeploymentName string

@description('Image model name')
param imageModelName string

@description('Image model version')
param imageModelVersion string

@description('Image model capacity')
param imageModelCapacity int

@description('Whether to deploy the image generation model (requires limited-access approval)')
param deployImageModel bool = false

@description('Id of the user or app to assign application roles')
param principalId string = ''

// Create Bing Grounding resource
resource bingGrounding 'Microsoft.Bing/accounts@2020-06-10' = {
  name: bingName
  location: 'global'
  sku: {
    name: 'G1'
  }
  kind: 'Bing.Grounding'
  properties: {
    statisticsEnabled: false
  }
}

// Create AI Services foundry account
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: foundryName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    apiProperties: {}
    customSubDomainName: foundryName
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    allowProjectManagement: true
    defaultProject: 'proj-default'
    associatedProjects: [
      'proj-default'
    ]
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

// Deploy GPT chat model
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundryAccount
  name: modelDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    currentCapacity: modelCapacity
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// Deploy gpt-image-1.5 image generation model (optional — requires limited-access approval)
resource imageModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = if (deployImageModel) {
  parent: foundryAccount
  name: imageModelDeploymentName
  dependsOn: [modelDeployment]
  sku: {
    name: 'GlobalStandard'
    capacity: imageModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: imageModelName
      version: imageModelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    currentCapacity: imageModelCapacity
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// Create Agents capability host
resource agentsCapabilityHost 'Microsoft.CognitiveServices/accounts/capabilityHosts@2025-06-01' = {
  parent: foundryAccount
  name: 'Agents'
  properties: {
    capabilityHostKind: 'Agents'
  }
}

// Create default project
resource defaultProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundryAccount
  name: 'proj-default'
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: 'Default project for AI-powered presentation generation'
    displayName: 'proj-default'
  }
}

// Create Bing connection at project level
resource bingConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: defaultProject
  name: bingName
  properties: {
    authType: 'ApiKey'
    category: 'ApiKey'
    target: 'https://api.bing.microsoft.com/'
    credentials: {
      key: listKeys(bingGrounding.id, bingGrounding.apiVersion).key1
    }
    useWorkspaceManagedIdentity: false
    isSharedToAll: false
    sharedUserList: []
    peRequirement: 'NotRequired'
    peStatus: 'NotApplicable'
    metadata: {
      type: 'bing_grounding'
      ApiType: 'Azure'
      ResourceId: bingGrounding.id
    }
  }
}

// RBAC: Cognitive Services OpenAI User on the foundry account
@description('Built-in Cognitive Services OpenAI User role. See https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-openai-user')
resource cognitiveServicesOpenAIUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
}

resource openAIUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: foundryAccount
  name: guid(foundryAccount.id, principalId, cognitiveServicesOpenAIUser.id)
  properties: {
    roleDefinitionId: cognitiveServicesOpenAIUser.id
    principalId: principalId
    principalType: 'User'
  }
}

// RBAC: Azure AI Developer on the foundry account
@description('Built-in Azure AI Developer role. See https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#azure-ai-developer')
resource azureAIDeveloper 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '64702f94-c441-49e6-a78b-ef80e0188fee'
}

resource aiDeveloperRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: foundryAccount
  name: guid(foundryAccount.id, principalId, azureAIDeveloper.id)
  properties: {
    roleDefinitionId: azureAIDeveloper.id
    principalId: principalId
    principalType: 'User'
  }
}

// RBAC: Cognitive Services Contributor on the foundry account
@description('Built-in Cognitive Services Contributor role. See https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-contributor')
resource cognitiveServicesContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'
}

resource contributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: foundryAccount
  name: guid(foundryAccount.id, principalId, cognitiveServicesContributor.id)
  properties: {
    roleDefinitionId: cognitiveServicesContributor.id
    principalId: principalId
    principalType: 'User'
  }
}

output foundryAccountId string = foundryAccount.id
output foundryAccountName string = foundryAccount.name
output foundryEndpoint string = foundryAccount.properties.endpoint
output projectId string = defaultProject.id
output projectEndpoint string = 'https://${foundryName}.services.ai.azure.com/api/projects/proj-default'
output modelDeploymentName string = modelDeployment.name
output imageModelDeploymentName string = deployImageModel ? imageModelDeployment.name : ''
output bingConnectionId string = bingConnection.id
output bingConnectionName string = bingConnection.name
output bingResourceId string = bingGrounding.id
