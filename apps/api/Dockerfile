FROM node:20-alpine
WORKDIR /app
COPY ../../package.json ../../pnpm-workspace.yaml ../../turbo.json ./
COPY ../../packages ./packages
COPY ./package.json ./
COPY ./tsconfig.json ./
COPY ./src ./src
COPY ./prisma ./prisma
RUN npm install -g pnpm@9.7.1
RUN pnpm install --ignore-scripts
RUN pnpm prisma generate
CMD ["pnpm", "dev"]
