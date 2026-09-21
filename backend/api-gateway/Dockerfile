# Dockerfile - NestJS API Gateway

# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Installer les dépendances de build pour bcrypt
RUN apk add --no-cache python3 make g++ openssl

# Copier les fichiers de dépendances
COPY package*.json ./
RUN npm install

# Copier le code source
COPY . .

# Générer Prisma Client
RUN npx prisma generate

# Build
RUN npm run build

# Stage 2: Production
FROM node:18-alpine

WORKDIR /app

# Installer les dépendances de build pour bcrypt
RUN apk add --no-cache python3 make g++ openssl

# Copier package.json et installer seulement les dépendances de production
COPY package*.json ./
RUN npm install --omit=dev

# Copier les fichiers buildés et Prisma
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma
COPY prisma ./prisma

# Exposer le port
EXPOSE 3000

# Santé check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "const req=require('http').get('http://127.0.0.1:3000/health', (r)=>process.exit(r.statusCode===200?0:1)); req.on('error',()=>process.exit(1));"

CMD ["npm", "run", "start:prod"]
