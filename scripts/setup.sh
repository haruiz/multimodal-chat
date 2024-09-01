PERFORM_RESET=0
PROJECT_ID="build-with-ai-project"
SERVICE_ACCOUNT_ID="vertex-ai-caller"
SERVICE_ACCOUNT_EMAIL=$SERVICE_ACCOUNT_ID@$PROJECT_ID.iam.gserviceaccount.com
KEY_FILE=./../credentials.json


# reset gcloud settings
if [ $PERFORM_RESET -eq 1 ]; then
    echo "Resetting gcloud"
    rm -rf ~/.config/gcloud
    gcloud auth login
fi

# set default project
gcloud config set project $PROJECT_ID

# enable billing
gcloud alpha billing accounts list
if [ $? -eq 0 ]; then
    echo "Billing account already exists"
else
    echo "Creating billing account"
    gcloud alpha billing accounts create --display-name=$PROJECT_ID-billing
fi

BILLING_ACCOUNT_ID=$(gcloud alpha billing accounts list --format=json | jq -r '.[0].name' | cut -d'/' -f2)
gcloud alpha billing projects link $PROJECT_ID --billing-account="$BILLING_ACCOUNT_ID"

# enabling services
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com


# create service account
gcloud iam service-accounts list | grep $SERVICE_ACCOUNT_ID
if [ $? -eq 0 ]; then
    echo "Service account $SERVICE_ACCOUNT_ID already exists"
else
    echo "Creating service account $SERVICE_ACCOUNT_ID"
    gcloud iam service-accounts create $SERVICE_ACCOUNT_ID \
        --description="$SERVICE_ACCOUNT_DESCRIPTION" \
        --display-name="$SERVICE_ACCOUNT_DISPLAY_NAME" \
        --quiet
fi


# delete all keys for service account if any
gcloud iam service-accounts keys list --iam-account="$SERVICE_ACCOUNT_EMAIL" | grep "$SERVICE_ACCOUNT_EMAIL"
if [ $? -eq 0 ]; then
    echo "Deleting all keys for service account $SERVICE_ACCOUNT_ID"
    # shellcheck disable=SC2086
    gcloud iam service-accounts keys list --iam-account=$SERVICE_ACCOUNT_EMAIL --format=json | jq -r '.[].name' | while read key; do
        gcloud iam service-accounts keys delete $key --iam-account=$SERVICE_ACCOUNT_EMAIL --quiet
    done
fi


# grant roles to service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:"$SERVICE_ACCOUNT_EMAIL" \
  --role=roles/aiplatform.user

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/artifactregistry.reader"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/iam.serviceAccountUser"

# cloud run admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/run.admin"

# cloud build admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudbuild.builds.editor"

# create key file
gcloud iam service-accounts keys create $KEY_FILE \
--iam-account=$SERVICE_ACCOUNT_ID@$PROJECT_ID.iam.gserviceaccount.com

# create docker images repository
REPO_NAME=build-with-ai-docker-repo
REPO_LOCATION=us-central1
REPO_DESCRIPTION="Build with AI docker repository"

gcloud artifacts repositories list --location=$REPO_LOCATION | grep $REPO_NAME
if [ $? -eq 0 ]; then
    echo "Repository $REPO_NAME already exists"
else
    echo "Creating repository $REPO_NAME"
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REPO_LOCATION \
        --description=$REPO_DESCRIPTION
fi