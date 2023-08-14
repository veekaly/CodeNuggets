import os, sys, ipaddress, boto3, argparse
from botocore.exceptions import BotoCoreError, ClientError
from tabulate import tabulate

parser = argparse.ArgumentParser()

parser.add_argument("--vpc", help="VPC Identifier")
parser.add_argument("--region", help="AWS Region")
args = parser.parse_args()

#-------------------------------------------------------------------------------------------------------------------------#
# This function returns VPC list in the specified region                                                                  #
#-------------------------------------------------------------------------------------------------------------------------#
def list_vpcs() -> list:
    try:
        response = ec2.describe_vpcs()
        vpcs = response['Vpcs']
        vpc_ids = [item['VpcId'] for item in vpcs]
    except ClientError as e:
        print("An error occurred:", e)
        raise e
    else:
        return vpc_ids

#-------------------------------------------------------------------------------------------------------------------------#
# This function takes VPC ID as input and check if VPC exists                                                             #
#-------------------------------------------------------------------------------------------------------------------------#
def check_vpc_exists(vpc_id: str) -> bool:
    try:
        response = ec2.describe_vpcs(VpcIds=[vpc_id])
        if len(response['Vpcs']) > 0:
            return True
        else:
            return False
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidVpcID.NotFound':
            return False
        else:
            print("An error occurred:", e)
            return False

#-------------------------------------------------------------------------------------------------------------------------#
# This function takes VPC ID as input and retrieve the list of subnet IDs                                                 #
#-------------------------------------------------------------------------------------------------------------------------#
def get_vpc_subnets(vpc_id: str) -> list:
    try:
        response = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        subnets = [item['SubnetId'] for item in response['Subnets']]
    except BotoCoreError as e:
        ValueError("BotoCoreError:", e)
    except ClientError as e:
        ValueError("ClientError:", e)
    else:
        return subnets
    
#-------------------------------------------------------------------------------------------------------------------------#
# This function takes a CIDR range as input and output a list of /28 Prefixes                                             #
#-------------------------------------------------------------------------------------------------------------------------#
def list_prefixes(cidr_range):
    cidr = ipaddress.IPv4Network(cidr_range)
    return list(cidr.subnets(new_prefix=28))

#-------------------------------------------------------------------------------------------------------------------------#
#  This function takes an input of the Subnet's whole CIDR range and individual Subnet Reservation CIDR ranges as a list  #
#  and calculate the rest of the CIDR range i.e. unreserved block(s)                                                         #
#-------------------------------------------------------------------------------------------------------------------------#
def get_unreserved_range(subnet_cidr_range: str, subnet_reservation_cidrs: list) -> str:
    reserved_networks = [ipaddress.IPv4Network(item['cidr']) for item in subnet_reservation_cidrs]
    reserved_networks_sorted = sorted(reserved_networks, key=lambda subnet: subnet.prefixlen, reverse=True)
    if len(reserved_networks_sorted) == 0:
        remaining_blocks = [ipaddress.IPv4Network(subnet_cidr_range)]
    else:
        remaining_blocks = list()

    for network in reserved_networks_sorted:
        if len(remaining_blocks) == 0:
            remaining_blocks = list(ipaddress.IPv4Network(subnet_cidr_range).address_exclude(network))
        else:
            for index, block in enumerate(remaining_blocks):
                if network.subnet_of(block):
                    new_blocks = ipaddress.IPv4Network(block).address_exclude(network)
                    remaining_blocks.pop(index)
                    remaining_blocks[index:index] = new_blocks

    return remaining_blocks

#-------------------------------------------------------------------------------------------------------------------------#
# This function takes Subnet ID as input and retrieve its CIDR Range                                                      #
#-------------------------------------------------------------------------------------------------------------------------#
def get_subnet_cidr(subnet_id: str) -> str:
    try:
        response = ec2.describe_subnets(SubnetIds=[subnet_id])
        subnet_cidr = response['Subnets'][0]['CidrBlock']
    except BotoCoreError as e:
        ValueError("BotoCoreError:", e)
    except ClientError as e:
        ValueError("ClientError:", e)
    else:
        return subnet_cidr
    
#-------------------------------------------------------------------------------------------------------------------------#
# This function takes Subnet ID as input and retrieve the list of Subnet CIDR reservations (if any)                       #
#-------------------------------------------------------------------------------------------------------------------------#
def get_subnet_reservation_cidrs(subnet_id: str) -> list:
    try:
        subnet_reservations = []
        response = ec2.get_subnet_cidr_reservations(SubnetId=subnet_id)
        for item in response['SubnetIpv4CidrReservations']:
            subnet_reservations.append({
                "id": item['SubnetCidrReservationId'],
                "cidr": item['Cidr']
            })

    except BotoCoreError as e:
        ValueError("BotoCoreError:", e)
    except ClientError as e:
        ValueError("ClientError:", e)
    else:
        return subnet_reservations

#-------------------------------------------------------------------------------------------------------------------------#
# This function takes Subnet ID as input and retrieve the list of IPv4 Prefixes assigned to the ENIs in the subnet        #
#-------------------------------------------------------------------------------------------------------------------------#
def get_allocated_prefixes(subnet_id: str) -> list:
    try:
        response = ec2.describe_network_interfaces(Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}])

        prefixes_allocated = []
        for eni in response['NetworkInterfaces']:
            if 'Ipv4Prefixes' in eni.keys():
                prefix_data = eni['Ipv4Prefixes']
                prefix_list = [ipaddress.IPv4Network(item['Ipv4Prefix']) for item in prefix_data]
                prefixes_allocated = prefixes_allocated + prefix_list

    except BotoCoreError as e:
        ValueError("BotoCoreError:", e)
    except ClientError as e:
        ValueError("ClientError:", e)
    else:
        return prefixes_allocated

#-------------------------------------------------------------------------------------------------------------------------#
# This function takes Subnet ID as input and retrieve the list of IPv4 Addresses assigned to the ENIs in the subnet       #
#-------------------------------------------------------------------------------------------------------------------------#
def get_eni_ips_allocated(subnet_id: str) -> list:
    try:
        eni_ips_allocated = []
        response = ec2.describe_network_interfaces(Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}])
        if 'NetworkInterfaces' in response:
            for eni in response['NetworkInterfaces']:
                for private_ip in eni['PrivateIpAddresses']:
                    eni_ips_allocated.append(private_ip['PrivateIpAddress'])
            eni_ips_allocated = [ipaddress.IPv4Address(item) for item in eni_ips_allocated]
        else:
            print("No ENIs found in the specified subnet.")

    except BotoCoreError as e:
        ValueError("BotoCoreError:", e)
    except ClientError as e:
        ValueError("ClientError:", e)
    else:
        return eni_ips_allocated
    
#-------------------------------------------------------------------------------------------------------------------------#
# This function takes an input of list of IP Addresses and a list of /28 Prefixes and calculate the list of Prefixes that #
# contain the IP Addresses from the IP Address list                                                                       #
#-------------------------------------------------------------------------------------------------------------------------#
def get_prefixes_allocated_standalone_ips(eni_ip_list: list, prefixes: list) -> list:
    allocated_prefixes = []
    for prefix in prefixes:
        for ip in eni_ip_list:
            if ip in prefix and ip not in allocated_prefixes:
                allocated_prefixes.append(prefix)
    return allocated_prefixes
    
def prepare_output_per_subnet(subnet_id: str) -> list:
    # subnet reservation IDs and CIDR Blocks for the subnet: [{ id: str, cidr: str }]
    subnet_reserved_cidrs = get_subnet_reservation_cidrs(subnet_id)
    # subnet unreserved CIDR block (Total CIDR - subnet_reserved_cidrs): [IPv4Network('x.x.x.x/x')]
    subnet_unreserved_cidr = get_unreserved_range(get_subnet_cidr(subnet_id), subnet_reserved_cidrs)
    # List of all /28 prefixes in the unreserved block
    unreserved_prefixes_all = list()
    for cidr in subnet_unreserved_cidr:
        unreserved_prefixes_all = unreserved_prefixes_all + list_prefixes(cidr)

    # All IP Addresses assigned to the ENIs in the subnet
    eni_ip_list = get_eni_ips_allocated(subnet_id)

    # List of subnet reservations and their overall /28 prefixes
    prefixes_per_reservation = list()
    for item in subnet_reserved_cidrs:
        prefixes_per_reservation.append({
            "id": item['id'],
            "cidr": item['cidr'],
            "prefixes_all": list_prefixes(item['cidr'])
        })

    # List of assigned prefixes in the subnet
    prefixes_allocated = get_allocated_prefixes(subnet_id)
    # List of unreserved prefixes that are already used by standalone IPs in the subnet
    unreserved_prefixes_allocated_for_standalone_ips = get_prefixes_allocated_standalone_ips(eni_ip_list=eni_ip_list, prefixes=unreserved_prefixes_all)
    # List of available prefixes in the unreserved block (Total prefixes - unreserved_prefixes_allocated_for_standalone_ips)
    unreserved_prefixes_free = list(set(unreserved_prefixes_all) - set(unreserved_prefixes_allocated_for_standalone_ips) - set(prefixes_allocated))

    # Update the prefixes_per_reservation list with the list of prefixes that are not assigned to any ENI (available)
    for item in prefixes_per_reservation:
        item['prefixes_free'] = list(set(item['prefixes_all']) - set(prefixes_allocated))
        item['prefixes_free'] = list(set(item['prefixes_free']) - set(get_prefixes_allocated_standalone_ips(eni_ip_list=eni_ip_list, prefixes=item['prefixes_all'])))

    # Append the prefixes_per_reservation list with the info about all/available prefixes in the unreserved block
    prefixes_per_reservation.append({
        "id": "unreserved",
        "cidr": subnet_unreserved_cidr,
        "prefixes_all": unreserved_prefixes_all,
        "prefixes_free": unreserved_prefixes_free 
    })
    output_per_subnet = []
    for count, item in enumerate(prefixes_per_reservation):
        if type(item['cidr']) == list:
            CIDR = "\n".join([str(item) for item in item['cidr']])
        else:
            CIDR = item['cidr']
        if count == 0:
            output_per_subnet.append([subnet_id, item['id'], CIDR, len(item['prefixes_all']), len(item['prefixes_all']) - len(item['prefixes_free']), len(item['prefixes_free'])])
        else:
            output_per_subnet.append(["", item['id'], CIDR, len(item['prefixes_all']), len(item['prefixes_all']) - len(item['prefixes_free']), len(item['prefixes_free'])])
    
    return output_per_subnet
    
def print_output(vpc_id: str) -> str:
    subnet_list = get_vpc_subnets(vpc_id)
    output = list()
    for subnet_id in subnet_list:
        output = output + prepare_output_per_subnet(subnet_id)
    
    headers = ["Subnet", "Reservation", "CIDR", "All Prefixes", "Allocated Prefixes", "Available Prefixes"]
    table = tabulate(output, headers=headers, tablefmt="grid")
    print(f"\nVPC: {vpc_id}")
    print(table)

if __name__ == '__main__':
    if args.region: region = args.region
    else: region = input("AWS Region: ")
    ec2 = boto3.client("ec2", region_name=region)
    if args.vpc: 
        vpc_id = args.vpc
        if not check_vpc_exists(vpc_id):
            print("VPC does not exist")
            sys.exit(0)
    else:
        vpc_list = list_vpcs()
        print("Enter a VPC selection: ")
        for index, item in enumerate(vpc_list, start=1):
            print(f"{index}. {item}")
        try:
            vpc_selection = int(input("Enter VPC selection: "))
            if vpc_selection not in range(1, len(vpc_list) + 1):
                print("Input is not valid, please retry!")
                sys.exit(0)
        except ValueError:
            print("Input is not valid, please retry!")
            sys.exit(0)

        vpc_id = vpc_list[vpc_selection - 1]

    print_output(vpc_id)