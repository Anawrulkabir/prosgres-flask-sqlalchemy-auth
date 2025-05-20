#!/bin/bash

# ANSI color codes for better visual appearance
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print banner
echo -e "${BLUE}${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║       FLASK JWT AUTHENTICATION - AWS DEPLOYMENT          ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to validate AWS access key format (basic check)
validate_access_key() {
  if [[ ! $1 =~ ^[A-Z0-9]{20}$ ]]; then
    echo -e "${RED}Invalid AWS Access Key format. It should be 20 characters.${NC}"
    return 1
  fi
  return 0
}

# Function to validate AWS secret key format (basic check)
validate_secret_key() {
  if [[ ${#1} -lt 40 ]]; then
    echo -e "${RED}Invalid AWS Secret Key format. It should be at least 40 characters.${NC}"
    return 1
  fi
  return 0
}

# Function to securely get user input
get_secure_input() {
  local prompt=$1
  local validate_func=$2
  local input
  local valid=false
  
  while [ "$valid" = false ]; do
    echo -en "${YELLOW}$prompt${NC} "
    if [[ $3 == "secure" ]]; then
      read -s input
      echo # Add newline after hidden input
    else
      read input
    fi
    
    if [[ -z $validate_func ]]; then
      valid=true
    else
      $validate_func "$input"
      if [[ $? -eq 0 ]]; then
        valid=true
      fi
    fi
  done
  
  echo "$input"
}

# Function to get AWS region with validation and dropdown
select_region() {
  local regions=("us-east-1" "us-east-2" "us-west-1" "us-west-2" "eu-west-1" "eu-central-1" "ap-south-1" "ap-southeast-1" "ap-southeast-2" "ap-northeast-1")
  
  echo -e "${YELLOW}Available AWS regions:${NC}"
  for i in "${!regions[@]}"; do
    echo "  $((i+1)). ${regions[$i]}"
  done
  
  local selection
  local valid=false
  
  while [ "$valid" = false ]; do
    echo -en "${YELLOW}Select region (1-${#regions[@]}):${NC} "
    read selection
    
    if [[ "$selection" =~ ^[0-9]+$ && "$selection" -ge 1 && "$selection" -le "${#regions[@]}" ]]; then
      valid=true
    else
      echo -e "${RED}Invalid selection. Please enter a number between 1 and ${#regions[@]}.${NC}"
    fi
  done
  
  echo "${regions[$((selection-1))]}"
}

# Get AWS credentials
echo -e "${BOLD}Please provide your AWS credentials:${NC}"

# Get Access Key
AWS_ACCESS_KEY_ID=$(get_secure_input "Enter AWS Access Key ID:" validate_access_key)

# Get Secret Access Key
AWS_SECRET_ACCESS_KEY=$(get_secure_input "Enter AWS Secret Access Key:" validate_secret_key secure)

# Optionally ask for session token
echo -en "${YELLOW}Do you need to provide a session token? (y/N):${NC} "
read need_token
if [[ "$need_token" =~ ^[Yy]$ ]]; then
  AWS_SESSION_TOKEN=$(get_secure_input "Enter AWS Session Token:" "" secure)
else
  AWS_SESSION_TOKEN=""
fi

# Select region
AWS_REGION=$(select_region)

# Display summary
echo
echo -e "${BLUE}${BOLD}Deployment Summary:${NC}"
echo -e "  ${BOLD}Access Key:${NC} ${AWS_ACCESS_KEY_ID:0:4}...${AWS_ACCESS_KEY_ID: -4}"
echo -e "  ${BOLD}Secret Key:${NC} ${AWS_SECRET_ACCESS_KEY:0:4}...${AWS_SECRET_ACCESS_KEY: -4}"
if [[ -n "$AWS_SESSION_TOKEN" ]]; then
  echo -e "  ${BOLD}Session Token:${NC} Provided"
else
  echo -e "  ${BOLD}Session Token:${NC} Not provided"
fi
echo -e "  ${BOLD}Region:${NC} $AWS_REGION"

# Confirmation
echo
echo -en "${GREEN}Do you want to proceed with the deployment? (y/N):${NC} "
read confirmation
if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
  echo -e "${RED}Deployment cancelled.${NC}"
  exit 0
fi

# Export AWS credentials
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN
export AWS_REGION

# Show spinner function for visual feedback
spinner() {
  local pid=$1
  local delay=0.1
  local spinstr='|/-\'
  while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
    local temp=${spinstr#?}
    printf " [%c]  " "$spinstr"
    local spinstr=$temp${spinstr%"$temp"}
    sleep $delay
    printf "\b\b\b\b\b\b"
  done
  printf "    \b\b\b\b"
}

# Deploy with Pulumi
echo -e "${BLUE}${BOLD}Starting deployment...${NC}"
echo -e "${YELLOW}Running: pulumi up --yes${NC}"

cd "$(dirname "$0")" # Navigate to script directory

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
  echo -e "${YELLOW}Setting up virtual environment...${NC}"
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

# Run Pulumi with progress indicator
pulumi up --yes &
PID=$!
spinner $PID

# Check deployment status
if [ $? -eq 0 ]; then
  echo -e "${GREEN}${BOLD}Deployment completed successfully!${NC}"
  # Display outputs
  echo -e "${BLUE}${BOLD}Deployment Outputs:${NC}"
  pulumi stack output
else
  echo -e "${RED}${BOLD}Deployment failed. Check the logs above for details.${NC}"
fi

# Deactivate virtual environment
deactivate