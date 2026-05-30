FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Install tailwindcss-animate
RUN npm install tailwindcss-animate

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
