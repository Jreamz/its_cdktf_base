#!/bin/bash

region="westus2"
subscription_id="<subscriptionid>"
customer="<customerabbreviation>"

resource_group_name=$customer"tfstate"
storage_account_name=$customer"tfstate"
container_name=$customer"tfstate"
service_principal_name=$customer"cdktfsp"


# Create resource group
az group create --name "$resource_group_name" --location "$region"

# Create storage account
az storage account create --resource-group "$resource_group_name" --name "$storage_account_name" --sku Standard_LRS --location "$region" --encryption-services blob

# Disable public access on the storage account
az storage account update --resource-group "$resource_group_name" --name "$storage_account_name"  --allow-blob-public-access false

# Create blob container
az storage container create --name "$container_name" --account-name "$storage_account_name"

# Create cdktf service principal and capture the output in a variable
sp_output=$(az ad sp create-for-rbac --name "$service_principal_name" --role Contributor --scopes "/subscriptions/$subscription_id")

# Extract the secret key from the output
secret_key=$(echo "$sp_output" | jq -r .password)

# Create key vault for service principal secret
az keyvault create --name "$service_principal_name" --resource-group "$resource_group_name" --location "$region"

# Set the service principal secret in the key vault
az keyvault secret set --vault-name "$service_principal_name" --name "$service_principal_name" --value "$secret_key"