.PHONY: deploy
deploy:
	gcloud builds submit . --config=cloudbuild.yaml
