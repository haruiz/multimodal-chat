SERVICE_NAME="picasso-service"
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --member="allUsers" \
  --role="roles/run.invoker"