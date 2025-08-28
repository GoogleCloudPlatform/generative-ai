# Use an official Node.js image. The 'lts' (Long Term Support) version is stable.
FROM node:18-alpine

# Set the working directory inside the container to /app
WORKDIR /app

# Copy package.json and package-lock.json first to leverage Docker's caching.
# This makes subsequent builds faster if you only change your source code.
COPY package*.json ./

# Install all project dependencies
RUN npm install

# Copy the rest of your application's source code into the container
COPY . .

# Expose port 8080 to the outside world
EXPOSE 8080

# The command to run when the container starts
CMD [ "node", "server.js" ]
