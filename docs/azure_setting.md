# Working on MS Azure Cloud
This tutorial helps you to setup the authentication to connect to Azure cloud from your laptop so that you can use `cloudal` to provision machines and perform the experiments.

If you do not have an Azure account yet, you should create an [Azure free account](https://azure.microsoft.com/en-us/free/) before begin.

# How to authenticate with Azure?

To setup an authentication, you have to provide the following information:
1. The subscription ID
2. The tenant ID
3. The application ID 
4. The client secret key

If you already set up and had these information, just provide it in a system config file and run the  `cloudal` examples. Otherwise, please follow the instruction below about what are they and how to get them. For each information, you can create and retrieve it from Azure portal or use Azure CLI. For Azure CLI, I prefer to use [Azure Cloud Shell](https://docs.microsoft.com/en-us/azure/cloud-shell/overview#:~:text=Azure%20Cloud%20Shell%20is%20an,work%2C%20either%20Bash%20or%20PowerShell.) so that all the requirements have already been installed for you.


## 1. Get the subscription ID:

The subscription ID is a [GUID](https://www.guidgenerator.com/) that uniquely identifies the agreements with Microsoft to use Azure cloud services. Every resource is associated with a subscription.

To get your subscription ID, log in to the Azure portal. Go to `Subscriptions`. The list of your subscriptions is displayed along with the subscription ID. 

Or using the following command to list all account information:

```bash
az account list --output table --all
```

## 2. Get the tenant ID:

A Tenant is representative of an organization within Azure Active Directory (Azure AD). It is a dedicated instance of the Azure AD service. An Azure AD tenant is required for defining an application and for assigning permissions so the application can make use of other Azure services' REST APIs.[1](https://docs.bmc.com/docs/cloudlifecyclemanagement/46/setting-up-a-tenant-id-client-id-and-client-secret-for-azure-resource-manager-provisioning-669202145.html)

Normally, when you have an Azure account, you also have an tenant ID, you can find your tenant information in the `Azure AD` on the Azure portal.

Or using the command:
```bash
az account show
```

If you do not have an Azure tenant, you can create a new one in Azure Active Directory by following the instruction [here](https://docs.microsoft.com/en-us/azure/active-directory/fundamentals/active-directory-access-create-new-tenant)


## 3. Get an application ID

If you already had an application, go straight to [Step 4](#step-4:-retrieve-the-application-id) to retrieve the information. If not, you have to register one.

### Step 1: Check permission
First you must have sufficient permissions to register an application with your Azure AD tenant, and assign a role to the application with your Azure subscription. Follow the guidance at [Permissions required for registering an app](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#permissions-required-for-registering-an-app) to check and modify the permission of your tenant.


### Step 2: Register an application with Azure AD and create a service principal
[Azure Active Directory](https://docs.microsoft.com/en-us/azure/active-directory/fundamentals/active-directory-whatis) is Microsoft’s cloud-based identity and access management service, which helps you sign in and access resources on Azure. You need to register an application with an Azure AD tenant to create an identity configuration that allows it to integrate with Azure AD.

When you have softwares, hosted services, or automated tools that need to access or modify resources, you can create an identity for them. This identity is known as a service principal. Access to resources is restricted by the roles assigned to the service principal, giving you control over which resources can be accessed and at which level. For security reasons, it is always recommended to use service principals with automated tools rather than allowing them to log in with a user identity. [[2]](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#required-permissions)


The application object is the global representation of your software/services for use across all tenants, and the service principal is the local representation for use in a specific tenant. [[3]](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals#service-principal-object)

You can follow the guide at [Registering an application](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#register-an-application-with-azure-ad-and-create-a-service-principal) to make an application registration and create a service principal on Azure portal.

or using Azure CLI,

to register an application:
```bash
az ad app create --display-name "application name" --identifier-uris "application uri" --password "your password"
```

to create a Service Principal:
```bash
az ad sp create --id "Application ID"
```

### Step 3: Assign a role to the application

To access resources in your subscription, you must assign a role to the application. Decide which role offers the right permissions for the application. To learn about the available roles, see [Azure built-in roles](https://docs.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)

To do it via portal, follow [Assign a role to the application](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#assign-a-role-to-the-application)


or using Azure CLI:

Follow [View the service principal of a managed identity in the Azure portal](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/how-to-view-managed-identity-service-principal-portal) to get the `Principal ID` (objectID) and change the role of that Service Principle to be an `owner`:

```bash
az role assignment create --assignee "Principal ID" --role Owner --scope /subscriptions/<subscription_id>
```

### Step 4: Retrieve the application ID

Once your service principal is set up, you can start using it to sign in programmatically in other to run your scripts or apps. To manage your service principal (permissions, user consented permissions, see which users have consented, review permissions, see sign in information, and more), go to `Azure Active Directory`, then select `Enterprise applications`.

To get the Application ID, go to `Azure Active Directory`, select `App registrations` in Azure AD, select your application, then you get the information of Application (client) ID, Directory (tenant) ID, Object ID (or Service Principal ID).


## 4. Get a client secret key

Azure supports 2 ways of authentication for service principals: password-based authentication (application secret) and certificate-based authentication. `libcloud` currently uses application secrets so we need to setup one.

Follow [Create a new application secret](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#option-2-create-a-new-application-secret) to create a secret key on Azure portal.


## 5. Create some resources to use service on Azure
On Azure, to create a VM, you have to create the following resource on each region to manage VMS.

### Create the resource group
A [resource group](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/overview#understand-scope) is a container that holds related resources for an Azure solution. All the resources in a resource group should share the same lifecycle. You deploy, update, and delete them together. 

You can follow [Create resource groups](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal#create-resource-groups) to create your resource group.

or using Azure Command line:
```bash
az group create -l <location-region> -n <name_of_resource_group>
```

### Create a virtual network

```bash
az network vnet create --name <name_of_virtual_network> --resource-group <name_of_resource_group> --subnet-name default
```

### Create a storage account using the same resource group

```bash
az storage account create --name <name_of_your_storage_account> --resource-group <name_of_resource_group>
```
# How to connect to your VM after creating them?
There are many ways to connect to an Azure VM as following:

1. [Assign a public IP](https://docs.microsoft.com/en-us/azure/virtual-network/associate-public-ip-address-vm) to the VM. This is not recommended and only should be used for testing.

2. Using [Point-to-Site connection](https://docs.microsoft.com/en-us/azure/vpn-gateway/vpn-gateway-howto-point-to-site-classic-azure-portal?fbclid=IwAR3hEXrKoTeGBZ1JakcqBaAc93Epf7AyqGHAqPWjOfTsIZlqU-6mzx4zjxY) service to connect to VMs via private IPs.

3. Deploy your own VPN service to connect to VMs via private IPs (to be planned to support by `cloudal` )