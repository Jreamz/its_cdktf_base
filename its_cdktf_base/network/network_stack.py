#!/usr/bin/env python
from constructs import Construct
from cdktf import TerraformStack, AzurermBackend
from cdktf_cdktf_provider_azurerm import (
    data_azurerm_client_config,
    nat_gateway,
    nat_gateway_public_ip_association,
    network_security_group,
    network_security_rule,
    provider,
    public_ip,
    resource_group,
    subnet,
    subnet_nat_gateway_association,
    subnet_network_security_group_association,
    virtual_network,
    virtual_network_gateway,
)


class ItsNetworkingStackConfig:
    def __init__(
        self,
        customer: str,
        region: str = "westus2",
        enable_pts_vpn: bool = True,
        vnet_subnet: str = "10.0.0.0/16",
        dmz_subnet: str = "10.0.0.0/24",
        server_subnet: str = "10.0.1.0/24",
        client_subnet: str = "10.0.2.0/24",
        vngw_subnet: str = "10.0.254.0/24",
        vngw_client_subnet: str = "10.10.10.0/24",
    ):
        self.customer = customer
        self.region = region
        self.enable_pts_vpn = enable_pts_vpn
        self.vnet_subnet = vnet_subnet
        self.dmz_subnet = dmz_subnet
        self.server_subnet = server_subnet
        self.client_subnet = client_subnet
        self.vngw_subnet = vngw_subnet
        self.vngw_client_subnet = vngw_client_subnet


class ItsNetworkingStack(TerraformStack):
    def __init__(self, scope: Construct, id: str, config: ItsNetworkingStackConfig):
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
        its_networking_stack_rg = resource_group.ResourceGroup(
            self,
            "its-networking-stack",
            name="its-networking-stack",
            location=config.region,
        )

        # Create the virtual network
        its_vnet = virtual_network.VirtualNetwork(
            self,
            "its-vnet",
            name="its-vnet",
            location=config.region,
            resource_group_name=its_networking_stack_rg.name,
            address_space=[config.vnet_subnet],
            depends_on=[its_networking_stack_rg],
        )

        # Create client subnet
        its_client_subnet = subnet.Subnet(
            self,
            "its-client-subnet",
            name="its-client-subnet",
            resource_group_name=its_networking_stack_rg.name,
            virtual_network_name=its_vnet.name,
            address_prefixes=[config.client_subnet],
            depends_on=[its_vnet],
        )

        # Create server subnet
        its_server_subnet = subnet.Subnet(
            self,
            "its-server-subnet",
            name="its-server-subnet",
            resource_group_name=its_networking_stack_rg.name,
            virtual_network_name=its_vnet.name,
            address_prefixes=[config.server_subnet],
            depends_on=[its_vnet],
        )

        # Create dmz subnet
        its_dmz_subnet = subnet.Subnet(
            self,
            "its-dmz-subnet",
            name="its-dmz-subnet",
            resource_group_name=its_networking_stack_rg.name,
            virtual_network_name=its_vnet.name,
            address_prefixes=[config.dmz_subnet],
            depends_on=[its_vnet],
        )

        # Create the VNGW subnet
        its_vngw_subnet = subnet.Subnet(
            self,
            "its-vngw-subnet",
            name="GatewaySubnet",
            resource_group_name=its_networking_stack_rg.name,
            virtual_network_name=its_vnet.name,
            address_prefixes=[config.vngw_subnet],
            depends_on=[its_vnet],
        )

        # Create network security group for client subnet
        its_client_nsg = network_security_group.NetworkSecurityGroup(
            self,
            "its-client-nsg",
            name="its-client-nsg",
            location=config.region,
            resource_group_name=its_networking_stack_rg.name,
            depends_on=[its_vnet],
        )

        # Create network security group for server subnet
        its_server_nsg = network_security_group.NetworkSecurityGroup(
            self,
            "its-server-nsg",
            name="its-server-nsg",
            location=config.region,
            resource_group_name=its_networking_stack_rg.name,
            depends_on=[its_vnet],
        )

        # Create network security group for dmz subnet
        its_dmz_nsg = network_security_group.NetworkSecurityGroup(
            self,
            "its-dmz-nsg",
            name="its-dmz-nsg",
            location=config.region,
            resource_group_name=its_networking_stack_rg.name,
            depends_on=[its_vnet],
        )

        # Create the nsg rule to allow rdp inbound from vngw to client subnet
        its_client_vngw_rdp_inbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-client-vngw-rdp-inbound",
            name="AllowVngwRdpInbound",
            priority=100,
            direction="Inbound",
            access="Allow",
            protocol="Tcp",
            source_port_range="*",
            destination_port_range="3389",
            source_address_prefix=config.vngw_client_subnet,
            destination_address_prefix=config.client_subnet,
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_client_nsg.name,
            depends_on=[its_client_nsg],
        )

        # Create the nsg rule to allow ssh inbound from vngw to the client subnet
        its_client_vngw_ssh_inbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-client-vngw-ssh-inbound",
            name="AllowVngwSshInbound",
            priority=110,
            direction="Inbound",
            access="Allow",
            protocol="Tcp",
            source_port_range="*",
            destination_port_range="22",
            source_address_prefix=config.vngw_client_subnet,
            destination_address_prefix=config.client_subnet,
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_client_nsg.name,
            depends_on=[its_client_nsg],
        )

        # Create the nsg rule to allow any server subnet inbound
        its_client_server_any_inbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-server-any-inbound",
            name="AllowServerAnyInbound",
            priority=120,
            direction="Inbound",
            access="Allow",
            protocol="*",
            source_port_range="*",
            destination_port_range="*",
            source_address_prefix=config.server_subnet,
            destination_address_prefix=config.client_subnet,
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_client_nsg.name,
            depends_on=[its_client_nsg],
        )

        # Create the nsg rule to allow rdp inbound from vngw to the server subnet
        its_server_vngw_rdp_inbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-server-vngw-rdp-inbound",
            name="AllowVngwRdpInbound",
            priority=100,
            direction="Inbound",
            access="Allow",
            protocol="Tcp",
            source_port_range="*",
            destination_port_range="3389",
            source_address_prefix=config.vngw_client_subnet,
            destination_address_prefix=config.server_subnet,
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_server_nsg.name,
            depends_on=[its_server_nsg],
        )

        # Create the nsg rule to allow ssh inbound from vngw to the server subnet
        its_server_vngw_ssh_inbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-server-vngw-ssh-inbound",
            name="AllowVngwSshInbound",
            priority=110,
            direction="Inbound",
            access="Allow",
            protocol="Tcp",
            source_port_range="*",
            destination_port_range="22",
            source_address_prefix=config.vngw_client_subnet,
            destination_address_prefix=config.server_subnet,
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_server_nsg.name,
            depends_on=[its_server_nsg],
        )

        # Create the nsg rule to allow any client subnet inbound
        its_server_client_any_inbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-server-client-any-inbound",
            name="AllowClientAnyInbound",
            priority=120,
            direction="Inbound",
            access="Allow",
            protocol="*",
            source_port_range="*",
            destination_port_range="*",
            source_address_prefix=config.client_subnet,
            destination_address_prefix=config.server_subnet,
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_server_nsg.name,
            depends_on=[its_server_nsg],
        )

        # Create the deny all inbound rule for the DMZ
        its_dmz_deny_all_inbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-dmz-deny-all-inbound",
            name="DenyAllInbound",
            priority=400,
            direction="Inbound",
            access="Deny",
            protocol="*",
            source_port_range="*",
            destination_port_range="*",
            source_address_prefix="*",
            destination_address_prefix="*",
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_dmz_nsg.name,
            depends_on=[its_dmz_nsg],
        )

        # Create the deny all outbound rule for the DMZ
        its_dmz_deny_all_outbound = network_security_rule.NetworkSecurityRule(
            self,
            "its-dmz-deny-all-outbound",
            name="DenyAllOutbound",
            priority=410,
            direction="Outbound",
            access="Deny",
            protocol="*",
            source_port_range="*",
            destination_port_range="*",
            source_address_prefix="*",
            destination_address_prefix="*",
            resource_group_name=its_networking_stack_rg.name,
            network_security_group_name=its_dmz_nsg.name,
            depends_on=[its_dmz_nsg],
        )

        # Create the nat gateway public ip
        its_natgw_public_ip = public_ip.PublicIp(
            self,
            "its-natgw-public-ip",
            name="its-natgw-public-ip",
            resource_group_name=its_networking_stack_rg.name,
            location=config.region,
            allocation_method="Static",
            sku="Standard",
            zones=["1"],
        )

        # Create the nat gateway
        its_natgw = nat_gateway.NatGateway(
            self,
            "its-natgw",
            name="its-natgw",
            resource_group_name=its_networking_stack_rg.name,
            location=config.region,
            sku_name="Standard",
            idle_timeout_in_minutes=10,
            zones=["1"],
            depends_on=[its_natgw_public_ip],
        )

        # Create the natgw public ip association
        its_natgw_association = (
            nat_gateway_public_ip_association.NatGatewayPublicIpAssociation(
                self,
                "its-natgw-public-ip-association",
                nat_gateway_id=its_natgw.id,
                public_ip_address_id=its_natgw_public_ip.id,
                depends_on=[its_natgw, its_natgw_public_ip],
            )
        )

        # Create the client subnet and nsg association
        its_client_nsg_association = subnet_network_security_group_association.SubnetNetworkSecurityGroupAssociation(
            self,
            "its-client-nsg-association",
            subnet_id=its_client_subnet.id,
            network_security_group_id=its_client_nsg.id,
            depends_on=[its_client_subnet, its_client_nsg],
        )

        # Create the server subnet and nsg association
        its_server_nsg_association = subnet_network_security_group_association.SubnetNetworkSecurityGroupAssociation(
            self,
            "its-server-nsg-association",
            subnet_id=its_server_subnet.id,
            network_security_group_id=its_server_nsg.id,
            depends_on=[its_server_subnet, its_server_nsg],
        )

        # Create the dmz subnet and nsg association
        its_dmz_nsg_association = subnet_network_security_group_association.SubnetNetworkSecurityGroupAssociation(
            self,
            "its-dmz-nsg-association",
            subnet_id=its_dmz_subnet.id,
            network_security_group_id=its_dmz_nsg.id,
            depends_on=[its_dmz_subnet, its_dmz_nsg],
        )

        # Create the client subnet natgw association
        its_client_natgw_association = (
            subnet_nat_gateway_association.SubnetNatGatewayAssociation(
                self,
                "its-client-natgw-association",
                subnet_id=its_client_subnet.id,
                nat_gateway_id=its_natgw.id,
                depends_on=[
                    its_client_subnet,
                    its_natgw_public_ip,
                    its_natgw,
                    its_natgw_association,
                ],
            )
        )

        # Create the server subnet natgw association
        its_server_natgw_association = (
            subnet_nat_gateway_association.SubnetNatGatewayAssociation(
                self,
                "its-server-natgw-association",
                subnet_id=its_server_subnet.id,
                nat_gateway_id=its_natgw.id,
                depends_on=[
                    its_server_subnet,
                    its_natgw_public_ip,
                    its_natgw,
                    its_natgw_association,
                ],
            )
        )

        if config.enable_pts_vpn:
            # Create a public ip for our VNGW
            its_vngw_public_ip = public_ip.PublicIp(
                self,
                "its-vngw-public-ip",
                name="its-vngw-public-ip",
                location=config.region,
                allocation_method="Dynamic",
                resource_group_name=its_networking_stack_rg.name,
            )

            # Create the VPN client configuration and address space for the VNGW
            its_vngw_client_config = (
                virtual_network_gateway.VirtualNetworkGatewayVpnClientConfiguration(
                    address_space=[config.vngw_client_subnet],
                    vpn_client_protocols=["OpenVPN"],
                    aad_tenant=f"https://login.microsoftonline.com/{tenant_id}",
                    aad_audience="41b23e61-6c1e-4545-b367-cd054e0ed4b4",
                    aad_issuer=f"https://sts.windows.net/{tenant_id}/",
                )
            )

            # Create the virtual network gateway
            its_vngw = (
                virtual_network_gateway.VirtualNetworkGateway(
                    self,
                    "its-vngw",
                    name="its-vngw",
                    resource_group_name=its_networking_stack_rg.name,
                    location=config.region,
                    type="Vpn",
                    sku="Standard",
                    vpn_type="RouteBased",
                    ip_configuration=[
                        {
                            "name": "vngw-config",
                            "publicIpAddressId": its_vngw_public_ip.id,
                            "private_ip_address_allocation": "Dynamic",
                            "subnetId": its_vngw_subnet.id,
                        }
                    ],
                    vpn_client_configuration=its_vngw_client_config,
                    depends_on=[
                        its_networking_stack_rg,
                        its_vnet,
                        its_client_subnet,
                        its_server_subnet,
                        its_dmz_subnet,
                        its_vngw_subnet,
                        its_vngw_public_ip,
                        its_client_nsg,
                        its_server_nsg,
                        its_dmz_nsg,
                        its_client_vngw_rdp_inbound,
                        its_client_vngw_ssh_inbound,
                        its_client_server_any_inbound,
                        its_server_vngw_rdp_inbound,
                        its_server_vngw_ssh_inbound,
                        its_server_client_any_inbound,
                        its_dmz_deny_all_inbound,
                        its_dmz_deny_all_outbound,
                        its_client_nsg_association,
                        its_server_nsg_association,
                        its_dmz_nsg_association,
                        its_natgw_public_ip,
                        its_natgw,
                        its_natgw_association,
                        its_server_nsg_association,
                        its_client_natgw_association,
                        its_server_natgw_association,
                    ],
                ),
            )

        # Define the remote storage backend connection for tfstate file
        AzurermBackend(
            self,
            resource_group_name=f"{config.customer}tfstate",
            storage_account_name=f"{config.customer}tfstate",
            container_name=f"{config.customer}tfstate",
            key="its_network_stack",
        )
