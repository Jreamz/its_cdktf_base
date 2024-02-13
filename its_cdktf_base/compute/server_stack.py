#!/usr/bin/env python
import os
from constructs import Construct
from cdktf import TerraformStack, AzurermBackend
from cdktf_cdktf_provider_azurerm import (
    provider,
    resource_group,
    network_interface,
    windows_virtual_machine,
    virtual_machine_data_disk_attachment,
    managed_disk,
    data_azurerm_subnet,
)


class ItsServerStack(TerraformStack):
    def __init__(self, scope: Construct, id: str, tfstate_key: str, customer: str):
        super().__init__(scope, id)

        # Initialize the Azure provider
        azure_provider = provider.AzurermProvider(self, "azure", features={})

        # Create resource group for server stack
        its_server_rg = resource_group.ResourceGroup(
            self,
            "its-server-stack",
            name="its-server-stack",
            location="westus2",
        )

        # Create the NIC for the windows server
        its_server_nic = network_interface.NetworkInterface(
            self,
            "its-server-nic",
            name="its-server-nic",
            resource_group_name=its_server_rg.name,
            location="westus2",
            ip_configuration=[
                {
                    "name": "its-server-ip-config",
                    "subnetId": self.get_subnet_id(
                        "its-vnet", "its-server-subnet", "its-networking-stack"
                    ),
                    "privateIpAddressAllocation": "Static",
                    "privateIpAddress": "10.0.1.10",
                }
            ],
        )

        # Create the Windows server 2022 vm
        its_server_windows_vm = windows_virtual_machine.WindowsVirtualMachine(
            self,
            "its-server-vm",
            name="its-server-vm",
            computer_name="its-server-vm",
            location="westus2",
            resource_group_name=its_server_rg.name,
            size="Standard_D4s_v3",
            os_disk={
                "storage_account_type": "StandardSSD_LRS",
                "caching": "ReadWrite",
            },
            network_interface_ids=[its_server_nic.id],
            source_image_reference={
                "publisher": "MicrosoftWindowsServer",
                "offer": "WindowsServer",
                "sku": "2022-datacenter-azure-edition",
                "version": "latest",
            },
            admin_username=os.environ.get("ADMIN_USERNAME"),
            admin_password=os.environ.get("ADMIN_PASSWORD"),
            depends_on=[its_server_rg, its_server_nic],
        )

        # Create server vm data disk
        its_server_data_disk = managed_disk.ManagedDisk(
            self,
            "its-server-data-disk",
            name="its-server-data-disk",
            location="westus2",
            resource_group_name=its_server_rg.name,
            storage_account_type="Standard_LRS",
            create_option="Empty",
            disk_size_gb=256,
            depends_on=[its_server_rg],
        )

        # Create data disk attachment to server vm
        its_server_data_disk_attachment = (
            virtual_machine_data_disk_attachment.VirtualMachineDataDiskAttachment(
                self,
                "its-server-data-disk-attachment",
                managed_disk_id=its_server_data_disk.id,
                virtual_machine_id=its_server_windows_vm.id,
                lun=0,
                caching="ReadWrite",
                depends_on=[its_server_data_disk, its_server_windows_vm],
            )
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
