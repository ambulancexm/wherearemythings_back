# wherearemythings_back

docker build -t agent-ia-back .
docker run --rm -p 8000:8000 --env-file .env agent-ia-back
