#!/usr/bin/env python
import os
from constructs import Construct
from cdktf import TerraformStack, AzurermBackend
from cdktf_cdktf_provider_azurerm import (
    provider,
    resource_group,
    storage_account,
)


class ItsStorageShareStackConfig:
    def __init__(
        self,
        customer: str,
        region: str = "westus2",
    ):
        self.customer = customer
        self.region = region


class ItsStorageShareStack(TerraformStack):
    def __init__(self, scope: Construct, id: str, config: ItsStorageShareStackConfig):
        super().__init__(scope, id)

        # Initialize the Azure provider
        azure_provider = provider.AzurermProvider(self, "azure", features={})

        # Create resource group for server stack
        its_storage_share_rg = resource_group.ResourceGroup(
            self,
            "its-storage-share-stack-rg",
            name="its-storageshare-stack",
            location=config.region,
        )

        # Create storage account resource
        its_storage_share_account = storage_account.StorageAccount(
            self,
            "its-storageshare-stack",
            name="itsstorageshare",
            location=config.region,
            resource_group_name=its_storage_share_rg.name,
            account_tier="Standard",
            account_replication_type="GRS",
            account_kind="StorageV2",
        )

        # Define the remote storage backend connection for tfstate file
        AzurermBackend(
            self,
            resource_group_name=f"{config.customer}tfstate",
            storage_account_name=f"{config.customer}tfstate",
            container_name=f"{config.customer}tfstate",
            key="its_cisco_vmx_stack",
        )
