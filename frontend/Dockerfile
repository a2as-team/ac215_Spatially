# Development Dockerfile for Next.js
FROM node:20-alpine

# Add libc6-compat for better compatibility
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Disable telemetry
ENV NEXT_TELEMETRY_DISABLED=1

# Expose port 3000
EXPOSE 3000

# Run development server
CMD ["npm", "run", "dev"]
