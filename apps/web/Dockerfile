FROM node:20-alpine
WORKDIR /app
COPY ../../package.json ../../pnpm-workspace.yaml ../../turbo.json ./
COPY ../../packages ./packages
COPY ./package.json ./
COPY ./tsconfig.json ./
COPY ./vite.config.ts ./
COPY ./tailwind.config.js ./
COPY ./postcss.config.js ./
COPY ./index.html ./
COPY ./src ./src
RUN npm install -g pnpm@9.7.1
RUN pnpm install --ignore-scripts
CMD ["pnpm", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
