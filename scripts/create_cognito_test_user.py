import boto3
import os
import sys
from botocore.exceptions import ClientError

def find_user_pool_id(user_pool_name):
    """Finds the User Pool ID by name."""
    try:
        cognito = boto3.client('cognito-idp')
        response = cognito.list_user_pools(MaxResults=60)
        
        for user_pool in response['UserPools']:
            if user_pool['Name'] == user_pool_name:
                return user_pool['Id']
        
        print(f"Error: Could not find User Pool with name '{user_pool_name}'.")
        sys.exit(1)

    except Exception as e:
        print(f"Failed to find User Pool: {e}")
        sys.exit(1)

def check_if_user_exists(user_pool_id, username):
    """Checks if a user already exists in the user pool."""
    try:
        cognito = boto3.client('cognito-idp')
        cognito.admin_get_user(UserPoolId=user_pool_id, Username=username)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            return False
        else:
            raise

def create_user_with_password(user_pool_id, username, password):
    """Creates a user and sets a permanent password."""
    try:
        cognito = boto3.client('cognito-idp')
        
        # Create the user
        cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            MessageAction='SUPPRESS',  # Prevents sending an email
        )
        
        # Set the password and confirm the user
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True
        )
        print("Successfully created and confirmed user.")
    
    except Exception as e:
        print(f"Failed to create user or set password: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Get project and environment variables from the environment
    project = os.environ.get('TF_VAR_project')
    env = os.environ.get('TF_VAR_env')

    if not project or not env:
        print("Error: Missing TF_VAR_project or TF_VAR_env environment variables.")
        sys.exit(1)

    # Construct the user pool name
    user_pool_name = f"{project}-{env}-users"
    
    # Define a consistent test username and hardcoded password
    # IMPORTANT: Change this password to a secure value!
    # Cognito requires a password with uppercase, lowercase, numbers, and symbols.
    test_username = "test-user"
    test_password = "MySecurePassword123!" 
    
    # Find the user pool ID
    user_pool_id = find_user_pool_id(user_pool_name)
    
    # Check if the user already exists
    if check_if_user_exists(user_pool_id, test_username):
        print(f"User '{test_username}' already exists. No action needed.")
        sys.exit(0)
    
    # Create the user if they don't exist
    create_user_with_password(user_pool_id, test_username, test_password)
    
    print("\n--- Test User Credentials ---")
    print(f"Username: {test_username}")
    print(f"Password: {test_password}")
    print("-----------------------------")
    print("\nUse these credentials to manually test the secure API endpoint.")
