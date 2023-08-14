# Subnet Prefix Collector

Amazon EKS users running their clusters at scale typically use prefix delegation feature of the VPC CNI to allocate IPv4 address prefixes to the EKS node ENIs instead of assigning individual IPv4 addresses to the slots on network interfaces. 

By doing this, VPC CNI allocates an IP address to a pod from the prefix assigned to an ENI. This helps in reducing the number of API calls made to the EC2 service when there is greater pod churn on the worker nodes.

The official [recommendation](https://aws.github.io/aws-eks-best-practices/networking/prefix-mode/index_linux/#use-prefix-mode-when) is to examine the subnets for contiguous block of addresses for `/28` prefix before migrating to prefix mode.

Therefore, I built this python tool to check all, allocated, and available `/28` prefixes in a VPC to estimate if prefix delegation is a viable option.

This will also help in troubleshooting issues that might arise when the VPC CNI is unable to get a contiguous `/28` Prefix for allocation (`Client.InsufficientCidrBlocks`) even when there are free IP addresses available in the subnets.

This tool also considers the subnet CIDR reservations of the subnets and calculate accordingly.

## Usage
#### Clone the git repository and navigate to `subnet-prefix-collector` directory

```
git clone https://github.com/veekaly/CodeNuggets.git
cd CodeNuggets/subnet-prefix-collector
```

#### Run below command to install the required python packages

```
pip install -r requirements.txt
```

#### Run the `main.py` and provide the requested inputs

```
python main.py 
AWS Region: us-west-2
Select a VPC:
1. vpc-xxxx
2. vpc-yyyy
Enter VPC selection: 1
```

> [!Note] 
> VPC and region information can also be passed using command line arguments: 
>
> ```python main.py --vpc vpc-xxxx --region us-west-2```

###### Output will be shown as below:

```
VPC: vpc-xxxx
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
| Subnet                   | Reservation           | CIDR            |   All Prefixes |   Allocated Prefixes |   Available Prefixes |
+==========================+=======================+=================+================+======================+======================+
| subnet-xxxxxxxxxxxxxxxxx | unreserved            | 100.64.192.0/18 |           1024 |                    1 |                 1023 |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
| subnet-yyyyyyyyyyyyyyyyy | scr-01234567890       | 100.64.112.0/22 |             64 |                    0 |                   64 |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
|                          | scr-09876543210       | 100.64.96.0/21  |            128 |                    0 |                  128 |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
|                          | scr-12233344445       | 100.64.72.0/22  |             64 |                    0 |                   64 |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
|                          | unreserved            | 100.64.80.0/20  |            768 |                    1 |                  767 |
|                          |                       | 100.64.64.0/21  |                |                      |                      |
|                          |                       | 100.64.76.0/22  |                |                      |                      |
|                          |                       | 100.64.104.0/21 |                |                      |                      |
|                          |                       | 100.64.120.0/21 |                |                      |                      |
|                          |                       | 100.64.116.0/22 |                |                      |                      |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
| subnet-zzzzzzzzzzzzzzzzz | scr-55555666666       | 100.64.144.0/20 |            256 |                    0 |                  256 |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
|                          | scr-77777778888       | 100.64.160.0/19 |            512 |                    0 |                  512 |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
|                          | unreserved            | 100.64.128.0/20 |            256 |                    0 |                  256 |
+--------------------------+-----------------------+-----------------+----------------+----------------------+----------------------+
```

> [!NOTE]  
> The first prefix in every subnet (that contains the Network Address) is not assigned to the ENIs