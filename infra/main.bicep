targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources. Must support gpt-image-1.5 via Global Standard deployment.')
@allowed(['australiaeast', 'canadacentral', 'centralus', 'eastus', 'eastus2', 'francecentral', 'southcentralus', 'swedencentral', 'uksouth', 'westus', 'westus3', 'eastus2euap'])
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

param resourceGroupName string = ''
param foundryName string = ''
param bingName string = ''
param modelDeploymentName string = ''
param modelName string = ''
param modelVersion string = ''
param modelCapacity int = 0
param imageModelDeploymentName string = ''
param imageModelName string = ''
param imageModelVersion string = ''
param imageModelCapacity int = 0

@description('Set to true to deploy the gpt-image-1.5 model (requires limited-access approval)')
param deployImageModel bool = false

@description('Id of the user or app to assign application roles')
param principalId string = ''

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location, 'v4'))
var tags = { 'azd-env-name': environmentName }

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// Azure AI Foundry (unified resource with built-in project)
module foundry './core/ai/foundry.bicep' = {
  name: 'foundry'
  scope: rg
  params: {
    foundryName: !empty(foundryName) ? foundryName : 'mlw-foundry-${resourceToken}'
    bingName: !empty(bingName) ? bingName : 'cog-bing-${resourceToken}'
    location: location
    modelDeploymentName: !empty(modelDeploymentName) ? modelDeploymentName : 'gpt-5.2-chat'
    modelName: !empty(modelName) ? modelName : 'gpt-5.2-chat'
    modelVersion: !empty(modelVersion) ? modelVersion : '2025-12-11'
    modelCapacity: modelCapacity != 0 ? modelCapacity : 110
    imageModelDeploymentName: !empty(imageModelDeploymentName) ? imageModelDeploymentName : 'gpt-image-1.5'
    imageModelName: !empty(imageModelName) ? imageModelName : 'gpt-image-1.5'
    imageModelVersion: !empty(imageModelVersion) ? imageModelVersion : '2025-12-16'
    imageModelCapacity: imageModelCapacity != 0 ? imageModelCapacity : 9
    deployImageModel: deployImageModel
    principalId: principalId
  }
}

// App outputs (names match .env variables expected by query.py)
output AZURE_AI_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output AI_PROJECT_NAME string = foundry.outputs.foundryAccountName
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_AI_MODEL_DEPLOYMENT_NAME string = foundry.outputs.modelDeploymentName
output AZURE_AI_IMAGE_MODEL_DEPLOYMENT_NAME string = foundry.outputs.imageModelDeploymentName  // empty when deployImageModel=false
output BING_PROJECT_CONNECTION_ID string = foundry.outputs.bingConnectionId
output BING_CONNECTION_NAME string = foundry.outputs.bingConnectionName
