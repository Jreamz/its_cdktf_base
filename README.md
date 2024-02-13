# Introduction 
A base package which defines all of our cdktf for our customer stacks.

### Requirements
-   [Python 3](https://www.python.org/downloads/)
-   [Poetry](https://python-poetry.org/docs/#installation)
-   [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
-   [CDKTF CLI](https://developer.hashicorp.com/terraform/cdktf/cli-reference/cli-configuration)


See also the [Getting started](https://dev.azure.com/itsc-dev/its_cdktf_base/_wiki?pageId=17&friendlyName=Getting-Started#) wiki for further detailed instructions

### Test, Synthesize & Deploy
- ** The below commands are for reference, synthesis and deployments are done within stacks that consume this package **
- Testing resource synthesis and deployment is done using the [cdktf-cli](https://developer.hashicorp.com/terraform/cdktf/cli-reference/commands)
- Basic synthesis: `cdktf synth`
- Basic deployment: `cdktf deploy`
- You can run `cat help` inside this package to learn more
- You can also run `cdktf -help` for further guidance


### Pipeline - Build and Publish

- This package is published to an Azure artifact feed, so it can be consumed by other customer stacks
- Changes are built and then published to an Azure Artifacts feed via a build pipeline
- The Azure Artifact feed is `its-cdktf-base`
- You still need to run 'poetry version patch' and include the `pyproject.toml` in your commit
- It is important you follow the above step, otherwise the version in the pipeline and feed will not have parity

### Manual - Build & Publish
- **This should be avoided generally speaking**
- To build and publish this package locally to the Azure artifact feed:
    - You will need to install `twine`, `keyring`, `artifacts-keyring`
    - Within your poetry virtualenv you can `poetry add twine keyring artifacts-keyring`
    - Then run `poetry install`
- Steps to manually build and publish are quite simple
    - Run `poetry version patch`
    - Run `poetry build`
    - Run `twine upload -r its-cdktf-base dist/*`
    - 
- _If you're using Linux, ensure you've installed the [prerequisites](https://go.microsoft.com/fwlink/?linkid=2103695), which are required for artifacts-keyring._
 
###	CDKTF references
- [Terraform - Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Github - CDKTF Azurerm Provider](https://github.com/cdktf/cdktf-provider-azurerm)
