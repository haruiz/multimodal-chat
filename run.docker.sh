IMAGE_NAME="picasso:latest"
CONTAINER_NAME="picasso"
RUN_INTERACTIVE=false
RUN_MODE="run"
PORT=8000

if docker inspect -f '{{.Config.Image}}' $CONTAINER_NAME >/dev/null 2>&1; then
    echo "Stopping running containers..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# check if image exists and remove it
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" != "" ]]; then
  echo "Image $IMAGE_NAME exists. Removing image..."
  docker rmi $IMAGE_NAME
fi

# create docker image
docker build --file "Dockerfile"  -t $IMAGE_NAME .

if [[ $RUN_MODE == "shell" ]]; then
  echo "Running container in shell mode..."
  docker run \
    -it \
    --name $CONTAINER_NAME \
    --env GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/credentials.json \
    --volume $(pwd)/credentials.json:/tmp/keys/credentials.json:ro \
    $IMAGE_NAME \
    /bin/bash
  exit 0
else
  # run the container
  if $RUN_INTERACTIVE; then
    echo "Running container in interactive mode..."
    docker run -it  \
    --env GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/credentials.json \
    --volume $(pwd)/credentials.json:/tmp/keys/credentials.json:ro \
    --name $CONTAINER_NAME \
    --publish $PORT:8000 \
    $IMAGE_NAME
    exit 0
  else
      echo "Running container in detached mode..."
      docker run -d  \
      --name $CONTAINER_NAME \
      --env GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/credentials.json \
      --volume $(pwd)/credentials.json:/tmp/keys/credentials.json:ro \
      --publish $PORT:8000 \
      $IMAGE_NAME
      docker exec -it $CONTAINER_NAME /bin/bash
      exit 0
  fi
fi