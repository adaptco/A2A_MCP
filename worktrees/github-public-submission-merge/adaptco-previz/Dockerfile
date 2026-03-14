# adaptco-previz/Dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --chown=node:node . .

USER node
CMD ["node", "/app/src/cli.js", "--help"]
