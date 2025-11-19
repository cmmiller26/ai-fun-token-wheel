# Stage 1: Build the React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application for production
# The VITE_API_URL will be passed in as a build argument
ARG VITE_API_URL
RUN VITE_API_URL=${VITE_API_URL} npm run build

# Stage 2: Serve the static files
FROM node:20-alpine

WORKDIR /app

# Install a simple static server
RUN npm install -g serve

# Copy built files from the builder stage
COPY --from=builder /app/dist .

# Expose the port serve will run on
EXPOSE 3000

# Start the server
CMD ["serve", "-s", ".", "-l", "3000"]