# Use an official Node.js runtime as a parent image
FROM node:20-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package.json package-lock.json* ./
# If you are using yarn, uncomment the next line and comment out the npm install line
# COPY yarn.lock ./

# Install dependencies
RUN npm install
# If you are using yarn, uncomment the next line and comment out the npm install line
# RUN yarn install

# Copy the rest of the application code
COPY . .

# Expose port 5173 for the Vite dev server
EXPOSE 5173

# Start the Vite development server
CMD ["npm", "run", "dev", "--", "--host"]
# If you are using yarn, uncomment the next line and comment out the npm run dev line
# CMD ["yarn", "dev", "--host"]
