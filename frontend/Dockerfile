FROM node:20-alpine

# Create app directory and set ownership to the built-in 'node' user
WORKDIR /app
RUN chown node:node /app

# Switch to the unprivileged user
USER node

# Copy package files and install production dependencies
COPY --chown=node:node package*.json ./
RUN npm ci --omit=dev

# Copy application code
COPY --chown=node:node . .

EXPOSE 3000
CMD ["node", "server.js"]
