# Chapter 3: Automating AWS Deployment with Pulumi

Welcome to the final chapter of our JWT Authentication System course! In the previous chapters, we built a secure authentication system with Flask and PostgreSQL, containerized it with Docker, and deployed it manually to AWS. Now, we'll take our deployment process to the next level by automating it with Pulumi, an Infrastructure as Code (IaC) tool.

## Table of Contents

- [Introduction](#introduction)
- [Understanding Infrastructure as Code](#understanding-infrastructure-as-code)
- [Getting Started with Pulumi](#getting-started-with-pulumi)
  - [Installing Pulumi](#installing-pulumi)
  - [Setting Up AWS Credentials](#setting-up-aws-credentials)
  - [Creating a Pulumi Project](#creating-a-pulumi-project)
- [Defining Infrastructure in Code](#defining-infrastructure-in-code)
  - [Network Resources](#network-resources)
  - [Security Resources](#security-resources)
  - [Compute Resources](#compute-resources)
- [Implementing the Deployment Script](#implementing-the-deployment-script)
- [Deploying with Pulumi](#deploying-with-pulumi)
- [Updating Infrastructure](#updating-infrastructure)
- [Destroying Infrastructure](#destroying-infrastructure)
- [Best Practices](#best-practices)
- [Conclusion](#conclusion)

## Introduction

In this chapter, we'll automate the entire AWS deployment process we performed manually in Chapter 2. We'll use Pulumi, an Infrastructure as Code (IaC) tool that allows us to define, deploy, and manage cloud infrastructure using familiar programming languages like Python.

Why automate our infrastructure? As you experienced in Chapter 2, setting up AWS resources manually can be:

- Time-consuming
- Error-prone
- Difficult to reproduce consistently
- Hard to version control

With Pulumi, we'll define our infrastructure in Python code, making it:

- Repeatable
- Version-controlled
- Testable
- Self-documenting

## Understanding Infrastructure as Code

Infrastructure as Code (IaC) is an approach to infrastructure management where you define your infrastructure resources in code files rather than manually configuring them through a user interface. This approach:

- Ensures consistency across deployments
- Enables version control for your infrastructure
- Allows for automated testing of infrastructure changes
- Facilitates collaboration among team members
- Makes infrastructure changes traceable and auditable

Pulumi is one of several IaC tools available (others include Terraform, AWS CloudFormation, and Azure Resource Manager templates). What makes Pulumi unique is its ability to use general-purpose programming languages like Python, JavaScript, and Go, rather than domain-specific languages.

## Getting Started with Pulumi

### Installing Pulumi

First, let's install Pulumi:

**For macOS:**

```bash
brew install pulumi/tap/pulumi
```

**For Linux:**

```bash
curl -fsSL https://get.pulumi.com | sh
```

**For Windows:**

```bash
choco install pulumi
```

### Setting Up AWS Credentials

To use Pulumi with AWS, we need to set up AWS credentials:

1. If you haven't already, install the AWS CLI:

```bash
pip install awscli
```

2. Configure AWS credentials:

```bash
aws configure
```

You'll be prompted for:

- AWS Access Key ID
- AWS Secret Access Key
- Default region name (e.g., us-east-1)
- Default output format (json)

### Creating a Pulumi Project

Let's create a directory structure for our Pulumi project:

```bash
mkdir -p pulumi
cd pulumi
```

Initialize a new Pulumi project:

```bash
pulumi new aws-python
```

You'll be prompted for:

- Project name: `flask-jwt-auth`
- Project description: `Flask JWT Authentication System on AWS`
- Stack name: `dev` (for development environment)

This creates a basic project structure with a `__main__.py` file where we'll define our infrastructure code.

## Defining Infrastructure in Code

Let's look at how we'll define our infrastructure in Python. Create or edit the `__main__.py` file:

```python
# filepath: pulumi/__main__.py
import pulumi
import pulumi_aws as aws

# Create a VPC
vpc = aws.ec2.Vpc("jwt-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    tags={"Name": "jwt-auth-vpc"}
)

# Create an Internet Gateway
igw = aws.ec2.InternetGateway("jwt-igw",
    vpc_id=vpc.id,
    tags={"Name": "jwt-auth-igw"}
)

# Create a public subnet
subnet = aws.ec2.Subnet("jwt-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True,
    availability_zone="ap-southeast-1a",  # Adjust for your region
    tags={"Name": "jwt-auth-subnet"}
)

# Create a route table
route_table = aws.ec2.RouteTable("jwt-route-table",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ],
    tags={"Name": "jwt-auth-route-table"}
)

# Associate route table with subnet
route_table_assoc = aws.ec2.RouteTableAssociation("jwt-route-table-assoc",
    subnet_id=subnet.id,
    route_table_id=route_table.id
)

# Create a security group
security_group = aws.ec2.SecurityGroup("jwt-security-group",
    vpc_id=vpc.id,
    description="Allow SSH, HTTP, and Flask ports",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
            description="SSH access"
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
            description="HTTP access"
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=5001,
            to_port=5001,
            cidr_blocks=["0.0.0.0/0"],
            description="Flask app port"
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=5050,
            to_port=5050,
            cidr_blocks=["0.0.0.0/0"],
            description="pgAdmin port"
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=5002,
            to_port=5002,
            cidr_blocks=["0.0.0.0/0"],
            description="PostgreSQL mapped port"
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow all outbound"
        )
    ],
    tags={"Name": "jwt-auth-security-group"}
)

# Create a key pair
key_pair = aws.ec2.KeyPair("jwt-key-pair",
    key_name="jwt-key-pair",
    public_key="ssh-rsa YOUR_PUBLIC_KEY_HERE"  # Replace with your actual public key
)

# Get the latest Ubuntu AMI
ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["099720109477"],  # Canonical
    filters=[
        aws.ec2.GetAmiFilterArgs(
            name="name",
            values=["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"],
        ),
        aws.ec2.GetAmiFilterArgs(
            name="virtualization-type",
            values=["hvm"],
        ),
    ],
)

# Define user data script for EC2 instance
user_data = """#!/bin/bash
# Update and install dependencies
set -e
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common git net-tools

# Install Docker the official way
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Enable and start Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Add ubuntu user to docker group (to avoid using sudo for docker commands)
sudo usermod -aG docker ubuntu

# Check Docker status
sudo systemctl status docker

# Install Docker Compose standalone (as a backup method)
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version || true

# Clone the repository
git clone https://github.com/yourusername/prosgres-flask-sqlalchemy-auth.git app
cd app

# Create .env file
cat << EOF > .env
DATABASE_URL=postgresql://user:password@db:5432/auth_db
JWT_SECRET_KEY=your-secret-key
SECRET_KEY=your-flask-secret-key
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=auth_db
EOF

# Create .env.pgAdmin file
cat << EOF > .env.pgAdmin
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin
EOF

# Try Docker Compose V2 plugin style first
echo "Attempting to run with docker compose (V2 plugin style)..."
sudo docker compose up -d || {
    echo "Docker Compose V2 plugin failed, trying standalone docker-compose..."
    # Fall back to standalone docker-compose if plugin version fails
    sudo /usr/local/bin/docker-compose up -d
}

# Get container status
echo "Listing running containers:"
sudo docker ps

# Log the docker-compose file for debugging
echo "Content of docker-compose.yml:"
cat docker-compose.yml || echo "docker-compose.yml not found"

# Wait for services to fully start
sleep 10

# Test network and service connectivity
echo "Testing network connectivity:"
ping -c 4 www.google.com || echo "Network ping failed but continuing"

echo "Testing application endpoints:"
curl -s http://localhost:5001 || echo "App on port 5001 not responding yet"
curl -s http://localhost:5050 || echo "pgAdmin on port 5050 not responding yet"
"""

# Create an EC2 instance
instance = aws.ec2.Instance("jwt-instance",
    ami=ami.id,
    instance_type="t2.micro",  # Free tier eligible
    subnet_id=subnet.id,
    vpc_security_group_ids=[security_group.id],
    key_name=key_pair.key_name,
    user_data=user_data,
    tags={"Name": "jwt-auth-instance"}
)

# Export outputs
pulumi.export("vpc_id", vpc.id)
pulumi.export("subnet_id", subnet.id)
pulumi.export("instance_public_ip", instance.public_ip)
pulumi.export("instance_public_dns", instance.public_dns)
pulumi.export("app_url", pulumi.Output.concat("http://", instance.public_ip, ":5001"))
pulumi.export("pgadmin_url", pulumi.Output.concat("http://", instance.public_ip, ":5050"))
```

Let's create a `requirements.txt` file in the `pulumi` directory to specify the required packages:

```
pulumi>=3.0.0
pulumi_aws>=6.0.0
```

## Deploying with Pulumi

Now that we've defined our infrastructure in code with Pulumi, let's deploy it. The core Pulumi commands are simple and powerful:

First, make sure you have configured your AWS credentials either through the AWS CLI or by setting environment variables:

```bash
# Configure AWS credentials with AWS CLI
aws configure

# Or set environment variables directly
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=your_preferred_region
```

Once your AWS credentials are configured, deploying your infrastructure is straightforward:

```bash
cd pulumi
pulumi up
```

The `pulumi up` command will:

1. Preview the resources that will be created
2. Ask for confirmation before making any changes
3. Deploy the infrastructure to AWS
4. Display outputs like your application URLs

When you run `pulumi up`, Pulumi will analyze your code and create a plan showing what resources will be created:

```
Previewing update (dev):
     Type                      Name                     Plan
 +   pulumi:pulumi:Stack       flask-jwt-auth-dev       create
 +   ├─ aws:ec2:Vpc            jwt-vpc                  create
 +   ├─ aws:ec2:InternetGateway jwt-igw                  create
 +   ├─ aws:ec2:Subnet         jwt-subnet               create
 +   ├─ aws:ec2:RouteTable     jwt-route-table          create
 +   ├─ aws:ec2:SecurityGroup  jwt-security-group       create
 +   ├─ aws:ec2:KeyPair        jwt-key-pair             create
 +   ├─ aws:ec2:Instance       jwt-instance             create
 +   └─ aws:ec2:RouteTableAssociation jwt-route-table-assoc   create
```

After confirmation, Pulumi will create the resources and show you the outputs:

```
Outputs:
    app_url           : "http://xx.xx.xx.xx:5001"
    instance_public_dns: "ec2-xx-xx-xx-xx.compute-1.amazonaws.com"
    instance_public_ip : "xx.xx.xx.xx"
    pgadmin_url       : "http://xx.xx.xx.xx:5050"
    subnet_id         : "subnet-xxxxxxxxxxxxxxxxx"
    vpc_id            : "vpc-xxxxxxxxxxxxxxxxx"
```

During the deployment, Pulumi will:

1. Create the VPC, subnet, internet gateway, and route table
2. Set up the security group with the appropriate rules
3. Launch an EC2 instance with our user data script
4. Output the URLs to access our application

After a few minutes (while the EC2 instance initializes and runs the user data script), your JWT authentication system should be available at the provided URLs.

## Updating Infrastructure

If you need to make changes to your infrastructure (e.g., changing the instance type or adding resources), simply edit the `__main__.py` file and run:

```bash
pulumi up
```

Pulumi will analyze the changes and apply only what's necessary, preserving existing resources when possible. You can also run:

```bash
pulumi refresh
```

This will synchronize Pulumi's state with the actual infrastructure in AWS, which is useful if you've made changes manually.

## Destroying Infrastructure

When you're done with your infrastructure, you can tear it down to avoid incurring further AWS charges:

```bash
pulumi destroy
```

This will remove all AWS resources created by Pulumi. Pulumi will ask for confirmation before deleting any resources.

## Best Practices

Here are some best practices to follow when using Pulumi for infrastructure automation:

1. **Version Control**: Keep your Pulumi code in a version control system like Git
2. **Environment Separation**: Use different stacks for development, staging, and production
3. **Secret Management**: Use Pulumi's secret management to protect sensitive data
4. **Modularization**: Break down complex infrastructure into reusable modules
5. **Tagging**: Always tag resources for better organization and cost tracking
6. **Documentation**: Document your infrastructure code and keep it updated
7. **Testing**: Test your infrastructure code before applying changes to production

## Conclusion

Congratulations! You've completed all three chapters of our JWT Authentication System course. Let's summarize what you've learned:

1. **Chapter 1**: Built a JWT authentication system with Flask and PostgreSQL, and containerized it with Docker and Docker Compose
2. **Chapter 2**: Manually deployed the application to AWS by creating a VPC, subnet, security group, and EC2 instance
3. **Chapter 3**: Automated the entire AWS deployment process using Pulumi, making it repeatable and consistent

You now have a fully functional JWT authentication system that is:

- **Secure**: Uses JWT tokens for authentication with refresh capabilities
- **Containerized**: Packaged in Docker containers for easy deployment
- **Cloud-hosted**: Running on AWS for high availability
- **Automated**: Infrastructure defined as code with Pulumi

This knowledge and experience will serve you well in building and deploying secure, scalable applications in the future. The combination of Docker for containerization and Pulumi for infrastructure automation is a powerful approach that's increasingly used in modern DevOps practices.

Keep exploring, learning, and building amazing things!

---

## Next Steps

If you'd like to further enhance your project, consider:

1. Adding HTTPS support with AWS Certificate Manager
2. Setting up a CI/CD pipeline with GitHub Actions
3. Implementing monitoring and logging with AWS CloudWatch
4. Adding auto-scaling capabilities for high availability
5. Creating a more sophisticated token management system
6. Implementing OAuth 2.0 for third-party authentication

Happy coding!
