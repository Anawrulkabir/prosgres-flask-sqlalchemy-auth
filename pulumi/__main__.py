import pulumi
import pulumi_aws as aws

# create a vpc
vpc = aws.ec2.Vpc("jwt-vpc-1",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    tags={"Name": "jwt-auth-vpc"}
)

# Create an Internet Gateway
igw = aws.ec2.InternetGateway("jwt-igw-1",
    vpc_id=vpc.id,
    tags={"Name": "jwt-auth-igw"}
)

# Create a public subnet
subnet = aws.ec2.Subnet("jwt-subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True,
    availability_zone="ap-southeast-1a",  # Adjust for your region
    tags={"Name": "jwt-auth-subnet"}
)

# Create a route table
route_table = aws.ec2.RouteTable("flask-route-table",
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
security_group = aws.ec2.SecurityGroup("flask-security-group",
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
    tags={"Name": "flask-auth-security-group"}
)

# Create a key pair (replace <YOUR_PRIVATE_KEY_CONTENT> with your jwt-key-pair.pem content)
key_pair = aws.ec2.KeyPair("jwt-key-pair",
    key_name="jwt-key-pair",
    public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQColr1Lp53Z00fVmP0+2D0h0kG1tXtvjOKRjWe+khMlER0ejN/ZVIclAou/ldIMEWDpmkJePYRiZWXBhbowbg0AU+fbdMkuiHNRS3cy0QWZMD+7z19cSpGsT5nb9ZAE2yieJLe1iPjNgjybRBPjONG9MAMuEfuUZiyLmjHJw8dL7nW6lF15yssc0GPGI4ZaAtBV5tE4orcnM1lr+JQH7tZSYkDAok1PBjQdy5hMK86bx+2ZtCuAtBHMutN5kZxXuGlJn3+rvRJL8B+yQNnoG0Nf7fJxWBF8QUKLu+c1Irhtsg9V7ZcOtRb18IF6BiDm1Qs5yIxduuQKOPfBhDPkG5JX"
)

# Replace the current AMI lookup with the specific Ubuntu 24.04 AMI
ami = aws.ec2.get_ami(
    owners=["099720109477"],  # Canonical
    filters=[
        aws.ec2.GetAmiFilterArgs(
            name="image-id",
            values=["ami-01938df366ac2d954"]  # Ubuntu 24.04 LTS (64-bit x86)
        )
    ],
    most_recent=True
)


# FIXED User data script to ensure Docker Compose works correctly
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
git clone https://github.com/poridhioss/prosgres-flask-sqlalchemy-auth app
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
instance = aws.ec2.Instance("jwt-instance-2",
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