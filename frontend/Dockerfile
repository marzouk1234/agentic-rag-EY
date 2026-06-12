FROM node:20-alpine

WORKDIR /app

# Copy package definition first for caching
COPY package.json package-lock.json* /app/

# Install dependencies
RUN npm install

# Copy application files
COPY . /app/

# Expose Vite dev server port
EXPOSE 5173

# Run Vite in development mode
CMD ["npm", "run", "dev"]
