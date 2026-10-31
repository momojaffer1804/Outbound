# Stage 1: Build React Application
FROM node:20-alpine AS build

WORKDIR /app

# Install npm dependencies
COPY package.json ./
RUN npm install

# Build argument for API base URL (empty defaults to Nginx reverse proxy)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Copy source code and build production bundle
COPY . ./
RUN npm run build

# Stage 2: Serve with Production Nginx
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy build artifacts from previous stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
