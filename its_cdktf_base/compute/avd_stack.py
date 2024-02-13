#!/usr/bin/env python
import datetime
from constructs import Construct
from cdktf import TerraformStack, AzurermBackend
from cdktf_cdktf_provider_azurerm import (
    provider,
    resource_group,
    virtual_desktop_workspace,
    virtual_desktop_host_pool,
    virtual_desktop_host_pool_registration_info,
    virtual_desktop_application_group,
    virtual_desktop_workspace_application_group_association,
    data_azurerm_subnet,
)


class ItsVirtualDesktopStack(TerraformStack):
    def __init__(self, scope: Construct, id: str, tfstate_key: str, customer: str):
        super().__init__(scope, id)

        # Initialize the Azure provider
        azure_provider = provider.AzurermProvider(self, "azure", features={})

        # Create resource group for AVD
        its_avd_rg = resource_group.ResourceGroup(
            self,
            "its-avd-stack",
            name="its-avd-stack",
            location="westus2",
        )

        # Create AVD workspace
        its_avd_workspace = virtual_desktop_workspace.VirtualDesktopWorkspace(
            self,
            "its-avd-workspace",
            name="its-avd-workspace",
            resource_group_name=its_avd_rg.name,
            location="westus2",
        )

        # Create AVD host pool
        its_avd_host_pool = virtual_desktop_host_pool.VirtualDesktopHostPool(
            self,
            "its-avd-host-pool",
            name="its-avd-host-pool",
            location="westus2",
            resource_group_name=its_avd_rg.name,
            type="Personal",
            personal_desktop_assignment_type="Automatic",
            load_balancer_type="Persistent",
            validate_environment=True,
            custom_rdp_properties="enablerdsaadauth:i:1;promptcredentialonce:i:1;autoreconnection enabled:i:1;videoplaybackmode:i:1;audiocapturemode:i:1;audiomode:i:1;camerastoredirect:s:1;redirectclipboard:i:1;redirectprinters:i:1;usbdevicestoredirect:s:1;use multimon:i:1;maximizetocurrentdisplays:i:1;screen mode id:i:1;dynamic resolution:i:1;",
        )

        # Get the current time and then a delta of 7 days
        expiration_date = datetime.datetime.now() + datetime.timedelta(days=7)
        rfc3339_expiration = expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Create the AVD host pool registration
        its_avd_host_pool_registration_info = virtual_desktop_host_pool_registration_info.VirtualDesktopHostPoolRegistrationInfo(
            self,
            "its-avd-host-pool-registration-info",
            hostpool_id=its_avd_host_pool.id,
            expiration_date=rfc3339_expiration,
        )

        # Create AVD app group
        its_avd_app_group = (
            virtual_desktop_application_group.VirtualDesktopApplicationGroup(
                self,
                "its-avd-app-group",
                name="its-avd-app-group",
                location="westus2",
                resource_group_name=its_avd_rg.name,
                type="Desktop",
                host_pool_id=its_avd_host_pool.id,
                friendly_name="its-avd-app-group",
                default_desktop_display_name="its-avd-desktop",
            )
        )

        # Create AVD app group association with workspace
        its_avd_app_group_association = virtual_desktop_workspace_application_group_association.VirtualDesktopWorkspaceApplicationGroupAssociation(
            self,
            "its-avd-app-group-association",
            workspace_id=its_avd_workspace.id,
            application_group_id=its_avd_app_group.id,
        )

        # Define the remote storage backend connection for tfstate file
        AzurermBackend(
            self,
            resource_group_name=f"{customer}tfstate",
            storage_account_name=f"{customer}tfstate",
            container_name=f"{customer}tfstate",
            key=f"{tfstate_key}",
        )

    # Method get existing Subnet information
    def get_subnet_id(self, vnet_name: str, subnet_name: str, rg_name: str):
        subnet = data_azurerm_subnet.DataAzurermSubnet(
            self,
            "get-subnet-id",
            name=subnet_name,
            virtual_network_name=vnet_name,
            resource_group_name=rg_name,
        )

        return subnet.id
