# create key pair value - jwt-key-pair.pem
touch jwt-key-pair.pem
cat << EOF > jwt-key-pair.pem
    # paste the key pair value
EOF


chmod 400 "jwt-key-pair.pem"
ssh -i "jwt-key-pair.pem" ubuntu@18.142.250.50

# yes 
# you are on the ec2 instance

# clone the repo 
git clone https://github.com/Anawrulkabir/prosgres-flask-sqlalchemy-auth.git main
cd main

sudo apt-get update
sudo apt install docker.io docker-compose

touch .env .env.pgAdmin

cat << EOF > .env 
DATABASE_URL=postgresql://user:password@db:5432/auth_db
JWT_SECRET_KEY=your-secret-key
SECRET_KEY=your-flask-secret-key
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=auth_db
EOF
cat << EOF > .env.pgAdmin 
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin 
EOF

sudo docker-compose up -d 

sudo apt install net-tools

ping www.google.com
