# Instructions

1. Set up a new virtual environment: `python3 -m venv env`
2. Activate that environment: `source env/bin/activate`
3. Install the required packages: `pip install -r requirements.txt`
4. Start up a local server: `python index.py`
5. Navigate to the app in a browser (the address will be printed in the console)

# Instructions for building and running locally with docker
[Guide](https://towardsdatascience.com/how-to-use-docker-to-deploy-a-dashboard-app-on-aws-8df5fb322708)

0. Start docker? `sudo systemctl restart docker`
1. Build the docker image: `sudo docker-compose build`
2. Build and start the container: `sudo docker-compose up`
3. Navigate to the app in a browser (the address will be printed in the console)

# Instructions for pushing to Amazon ECR and deploying on EC2
[Guide](https://hackernoon.com/running-docker-on-aws-ec2-83a14b780c56)

1. Authenticate your Docker client to the Amazon ECR registry:
    `aws configure set aws_access_key_id <YOUR_ACCESS_KEY>`
    `aws configure set aws_secret_access_key <YOUR_SECRET_KEY>`
    `aws configure set default.region <YOUR_REGION>`
    `aws configure set default.output json`
    `aws ecr get-login-password --region <YOUR_REGION> | sudo docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com`
2. Push the repository to the Amazon ECR registry:
    `sudo docker tag tube-map-dash:<VERSION> <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/dashboard`
    `sudo docker push <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/dashboard`
3. SSH into the EC2 instance:
    `ssh -i <CREDENTIAL_FILE>.pem ec2-user@<PUBLIC_DNS_FOR_YOUR_EC2>`
4. Repeat step 1, but on the EC2 instance
5. Pull the docker image:
    `docker pull <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/dashboard:latest`
6. Stop the current container, and start a new one:
    `docker ps`
    `docker stop <CONTAINER_NAME>`
    `docker run -d -t -i -p 8050:8050 <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/dashboard`

# Instructions for running on EC2 without an ECR image

1. SSH into the EC2 instance:
    `ssh -i <CREDENTIAL_FILE>.pem ec2-user@<PUBLIC_DNS_FOR_YOUR_EC2>`
2. Setup GitHub (skip if already done)
    `ssh-keygen -t rsa -b 4096 -C "your_email@example.com"`
    `<SAVE TO DEFAULT LOCATION>`
    `eval "$(ssh-agent -s)"`
    `ssh-add ~/.ssh/id_rsa`
    `cat ~/.ssh/id_rsa.pub`
    `<ADD SSH KEY TO GITHUB ACCOUNT>`
    `sudo yum install git -y`
    `git clone <REPOSITORY>`
3. Pull latest version of repository
    `git pull`
4. Copy the graph file to the repository (from outside the instance) and SSH back in
    `logout`
    `scp -i <CREDENTIAL_FILE>.pem <FILE TO COPY> ec2-user@<PUBLIC_DNS_FOR_YOUR_EC2>:~<PATH TO COPY TO>`
    `ssh -i <CREDENTIAL_FILE>.pem ec2-user@<PUBLIC_DNS_FOR_YOUR_EC2>`
5. Setup docker and docker-dompose (skip if already done)
    `sudo yum install docker`
    `sudo curl -L https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose`
    `sudo chmod +x /usr/local/bin/docker-compose`
6. Build the docker image, terminate existing containers, run the new one (detach so I can log out)
    `docker-compose build`
    `docker ps`
    `docker stop <CONTAINER_NAME>`
    `docker-compose up --detach`