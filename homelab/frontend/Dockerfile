# Stage 1: Build the React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source and config
COPY tsconfig.json tsconfig.node.json vite.config.ts tailwind.config.js postcss.config.js index.html ./
COPY src ./src

# Build production assets
RUN npm run build

# Stage 2: Serve with Nginx reverse proxy
FROM nginx:alpine

# Remove default nginx configs
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom reverse proxy config and built static files
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
