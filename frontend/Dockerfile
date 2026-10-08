# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /app

# Install security updates and curl for health checks
RUN apk update && apk upgrade && apk add --no-cache curl

# Install dependencies for sharp
RUN apk add --no-cache build-base vips-dev

# Copy package files
COPY package*.json ./
# Install all dependencies (including dev) required for build
RUN npm ci && npm cache clean --force

# Stage 2: Builder
FROM node:18-alpine AS builder
WORKDIR /app

# Install security updates
RUN apk update && apk upgrade && apk add --no-cache curl

# Define build arguments
ARG NEXT_PUBLIC_BACKEND_BASE_URL
ARG NEXT_PUBLIC_SSO_PROJECT_ID
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID

# Set environment variables during build
ENV NEXT_PUBLIC_BACKEND_BASE_URL=$NEXT_PUBLIC_BACKEND_BASE_URL
ENV NEXT_PUBLIC_SSO_PROJECT_ID=$NEXT_PUBLIC_SSO_PROJECT_ID
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID

# Copy dependencies from the deps stage
COPY --from=deps /app/node_modules ./node_modules
# Copy package files
COPY package*.json ./
# Copy source code
COPY . .

# Build the application (environment variables will be used at runtime)
RUN npm run build

# Stage 3: Runner
FROM node:18-alpine
WORKDIR /app

# Install security updates and curl for health checks
RUN apk update && apk upgrade && apk add --no-cache curl

# Create non-root user with specific UID/GID for consistency
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# Copy built application from builder stage
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Define build arguments for runtime
ARG NEXT_PUBLIC_BACKEND_BASE_URL
ARG NEXT_PUBLIC_SSO_PROJECT_ID
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID

# Set environment variables at runtime
ENV NEXT_PUBLIC_BACKEND_BASE_URL=$NEXT_PUBLIC_BACKEND_BASE_URL
ENV NEXT_PUBLIC_SSO_PROJECT_ID=$NEXT_PUBLIC_SSO_PROJECT_ID
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID

# Create cache directory and set ownership
RUN mkdir -p .next/cache && chown -R nextjs:nodejs ./.next

# Set ownership for all files to non-root user
RUN chown -R nextjs:nodejs ./

# Switch to non-root user for security
USER nextjs

# Security: Remove unnecessary packages and files
RUN rm -rf /var/cache/apk/* && \
    rm -rf ~/.npm && \
    find . -name "*.map" -type f -delete || true

# Security: Set resource limits
ENV NODE_OPTIONS="--max-old-space-size=1024"

ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

EXPOSE 3000

# Health check with improved timeout and error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Use server.js as entrypoint
CMD ["node", "server.js"]
