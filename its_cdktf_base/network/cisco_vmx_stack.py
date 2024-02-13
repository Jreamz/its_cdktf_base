#!/usr/bin/env python
import os
import json
from constructs import Construct
from cdktf import TerraformStack, AzurermBackend
from cdktf_cdktf_provider_azurerm import (
    marketplace_agreement,
    data_azurerm_client_config,
    provider,
    resource_group,
    route,
    route_table,
    subnet,
    subnet_route_table_association,
    virtual_network,
    managed_application,
)


class ItsCiscoVmxStackConfig:
    def __init__(
        self,
        customer: str,
        region: str = "westus2",
        vnet_subnet: str = "10.0.0.0/16",
        dmz_subnet: str = "10.0.0.0/24",
        server_subnet: str = "10.0.1.0/24",
        client_subnet: str = "10.0.2.0/24",
        sdwan_subnet: str = "10.0.254.0/24",
    ):
        self.customer = customer
        self.region = region
        self.vnet_subnet = vnet_subnet
        self.dmz_subnet = dmz_subnet
        self.server_subnet = server_subnet
        self.client_subnet = client_subnet
        self.sdwan_subnet = sdwan_subnet


class ItsCiscoVmxStack(TerraformStack):
    def __init__(self, scope: Construct, id: str, config: ItsCiscoVmxStackConfig):
        super().__init__(scope, id)

        # Initialize the Azure provider
        azure_provider = provider.AzurermProvider(self, "azure", features={})

        # Initialize azurerm client config data source
        azure_client_config = data_azurerm_client_config.DataAzurermClientConfig(
            self,
            "azure-tenant-id",
        )

        # Output the tenant id from the azurerm client
        tenant_id = azure_client_config.tenant_id

        # Create resource group for the Azure Virtual Desktop resources
        its_ciscovmx_stack_rg = resource_group.ResourceGroup(
            self,
            "its-ciscovmx-stack",
            name="its-ciscovmx-stack",
            location=config.region,
        )

        # Create the virtual network
        its_ciscovmx_vnet = virtual_network.VirtualNetwork(
            self,
            "its-ciscovmx-vnet",
            name="its-ciscovmx-vnet",
            location=config.region,
            resource_group_name=its_ciscovmx_stack_rg.name,
            address_space=[config.vnet_subnet],
            depends_on=[its_ciscovmx_stack_rg],
        )

        # Create client subnet
        its_ciscovmx_client_subnet = subnet.Subnet(
            self,
            "its-ciscovmx-client-subnet",
            name="client",
            resource_group_name=its_ciscovmx_stack_rg.name,
            virtual_network_name=its_ciscovmx_vnet.name,
            address_prefixes=[config.client_subnet],
            depends_on=[its_ciscovmx_vnet],
        )

        # Create server subnet
        its_ciscovmx_server_subnet = subnet.Subnet(
            self,
            "its-ciscovmx-server-subnet",
            name="server",
            resource_group_name=its_ciscovmx_stack_rg.name,
            virtual_network_name=its_ciscovmx_vnet.name,
            address_prefixes=[config.server_subnet],
            depends_on=[its_ciscovmx_vnet],
        )

        # Create dmz subnet
        its_ciscovmx_dmz_subnet = subnet.Subnet(
            self,
            "its-ciscovmx-dmz-subnet",
            name="dmz",
            resource_group_name=its_ciscovmx_stack_rg.name,
            virtual_network_name=its_ciscovmx_vnet.name,
            address_prefixes=[config.dmz_subnet],
            depends_on=[its_ciscovmx_vnet],
        )

        # Create the VMX subnet
        its_ciscovmx_sdwan_subnet = subnet.Subnet(
            self,
            "its-sdwan-subnet",
            name="sdwan",
            resource_group_name=its_ciscovmx_stack_rg.name,
            virtual_network_name=its_ciscovmx_vnet.name,
            address_prefixes=[config.sdwan_subnet],
            depends_on=[its_ciscovmx_vnet],
        )

        # Accept the EULA for the Cisco managed app
        its_ciscovmx_eula = marketplace_agreement.MarketplaceAgreement(
            self,
            "its-ciscovmx-eula",
            publisher="cisco",
            offer="cisco-meraki-vmx",
            plan="cisco-meraki-vmx",
        )

        # Create the necessary parameters which are passed to the managed app
        its_ciscovmx_params = json.dumps(
            {
                "location": config.region,
                "vmName": "its-ciscovmx",
                "merakiAuthToken": os.environ.get("MERAKI_AUTH_TOKEN"),
                "virtualNetworkName": its_ciscovmx_vnet.name,
                "virtualNetworkNewOrExisting": "existing",
                "virtualNetworkAddressPrefix": config.vnet_subnet,
                "virtualNetworkResourceGroup": its_ciscovmx_stack_rg.name,
                "virtualMachineSize": "Standard_F4s_v2",
                "subnetName": its_ciscovmx_sdwan_subnet.name,
                "subnetAddressPrefix": config.sdwan_subnet,
            }
        )

        # Create the vmx manage application definition
        its_ciscovmx_managed_application = managed_application.ManagedApplication(
            self,
            "its-ciscovmx-app",
            name="its-ciscovmx-app",
            resource_group_name=its_ciscovmx_stack_rg.name,
            managed_resource_group_name="its-ciscovmx-managed-app",
            location=config.region,
            kind="MarketPlace",
            # This is being deprecated in provider v4.0, but parameter_values was blowing up, may need to review soon
            parameter_values=its_ciscovmx_params,
            plan={
                "name": "cisco-meraki-vmx",
                "product": "cisco-meraki-vmx",
                "publisher": "cisco",
                "version": "15.37.4",
            },
            depends_on=[
                its_ciscovmx_stack_rg,
                its_ciscovmx_eula,
                its_ciscovmx_vnet,
                its_ciscovmx_sdwan_subnet,
                its_ciscovmx_server_subnet,
                its_ciscovmx_client_subnet,
                its_ciscovmx_dmz_subnet,
            ],
        )

        # Create the route table for subnets
        its_ciscovmx_route_table = route_table.RouteTable(
            self,
            "its-ciscovmx-route-table",
            name="its-ciscovmx-route-table",
            resource_group_name=its_ciscovmx_stack_rg.name,
            location=config.region,
            disable_bgp_route_propagation=True,
        )

        # Create the route to the vMX subnet and appliance
        its_ciscovmx_route = route.Route(
            self,
            "its-ciscovmx-route",
            name="its-ciscovmx-route",
            resource_group_name=its_ciscovmx_stack_rg.name,
            route_table_name=its_ciscovmx_route_table.name,
            address_prefix=config.sdwan_subnet,
            next_hop_type="VirtualAppliance",
            next_hop_in_ip_address="10.0.254.4",
            depends_on=[its_ciscovmx_route_table],
        )

        # Create the route table associations for all subnets BESIDES the sdwan
        # DO NOT associate with the sdwan subnet
        # This is known to cause packet loss and routing loops
        its_ciscovmx_route_table_association_client = (
            subnet_route_table_association.SubnetRouteTableAssociation(
                self,
                "its-ciscovmx-route-table-association-client",
                subnet_id=its_ciscovmx_client_subnet.id,
                route_table_id=its_ciscovmx_route_table.id,
                depends_on=[its_ciscovmx_route_table],
            )
        )

        its_ciscovmx_route_table_association_server = (
            subnet_route_table_association.SubnetRouteTableAssociation(
                self,
                "its-ciscovmx-route-table-association-server",
                subnet_id=its_ciscovmx_server_subnet.id,
                route_table_id=its_ciscovmx_route_table.id,
                depends_on=[its_ciscovmx_route_table],
            )
        )

        # Define the remote storage backend connection for tfstate file
        AzurermBackend(
            self,
            resource_group_name=f"{config.customer}tfstate",
            storage_account_name=f"{config.customer}tfstate",
            container_name=f"{config.customer}tfstate",
            key="its_cisco_vmx_stack",
        )
