FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . ./

ENV DANGEROUSLY_DISABLE_HOST_CHECK=true
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
