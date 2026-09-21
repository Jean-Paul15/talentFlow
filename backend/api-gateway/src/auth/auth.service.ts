import { getJwtSecret } from './jwt-secret';
﻿// Auth Service - Register, Login, JWT

import {
  BadRequestException,
  ConflictException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from '../prisma/prisma.service';
import * as bcrypt from 'bcrypt';

type TokenPairResult = {
  access_token: string;
  refresh_token: string;
  user: { id: string; email: string; name?: string };
};

@Injectable()
export class AuthService {
  constructor(
    private prisma: PrismaService,
    private jwtService: JwtService,
  ) {}

  async register(
    email: string,
    password: string,
    name: string,
    acceptTerms: boolean,
  ) {
    if (!acceptTerms) {
      throw new BadRequestException(
        'Tu dois accepter les conditions d’utilisation pour créer un compte.',
      );
    }
    const existing = await this.prisma.user.findUnique({ where: { email } });
    if (existing) throw new ConflictException('Email existe deja');

    const hashed = await bcrypt.hash(password, 10);
    const user = await this.prisma.user.create({
      data: { email, password: hashed, name },
    });

    return this.generateTokens(user.id, user.email, user.name ?? undefined);
  }

  async login(email: string, password: string) {
    const user = await this.prisma.user.findUnique({ where: { email } });
    if (!user) throw new UnauthorizedException('Identifiants invalides');

    // Defensive guard: legacy/incomplete rows must never surface as 500.
    if (typeof user.password !== 'string' || !user.password.trim()) {
      throw new UnauthorizedException('Identifiants invalides');
    }

    const valid = await bcrypt.compare(password, user.password);
    if (!valid) throw new UnauthorizedException('Identifiants invalides');

    return this.generateTokens(user.id, user.email, user.name ?? undefined);
  }

  async refresh(refreshToken: string) {
    const token = String(refreshToken || '').trim();
    if (!token) throw new UnauthorizedException('Refresh token missing');

    const refreshSecret = process.env.JWT_REFRESH_SECRET || getJwtSecret();
    let payload: { sub?: string; email?: string; type?: string };
    try {
      payload = this.jwtService.verify(token, { secret: refreshSecret });
    } catch {
      throw new UnauthorizedException('Refresh token invalid');
    }

    if (payload?.type !== 'refresh' || !payload?.sub || !payload?.email) {
      throw new UnauthorizedException('Refresh token invalid');
    }

    const user = await this.prisma.user.findUnique({ where: { id: payload.sub } });
    if (!user || user.email !== payload.email) {
      throw new UnauthorizedException('User not found');
    }

    return this.generateTokens(user.id, user.email, user.name ?? undefined);
  }

  async validateUser(id: string, email: string) {
    return this.prisma.user.findUnique({ where: { id } });
  }

  private generateTokens(userId: string, email: string, name?: string): TokenPairResult {
    const accessSecret = getJwtSecret();
    const refreshSecret = process.env.JWT_REFRESH_SECRET || accessSecret;
    const accessExpiresIn = (process.env.JWT_ACCESS_EXPIRES_IN || '1h') as any;
    const refreshExpiresIn = (process.env.JWT_REFRESH_EXPIRES_IN || '30d') as any;

    const accessPayload = { sub: userId, email, type: 'access' };
    const refreshPayload = { sub: userId, email, type: 'refresh' };
    return {
      access_token: this.jwtService.sign(accessPayload, {
        secret: accessSecret,
        expiresIn: accessExpiresIn,
      }),
      refresh_token: this.jwtService.sign(refreshPayload, {
        secret: refreshSecret,
        expiresIn: refreshExpiresIn,
      }),
      user: { id: userId, email, ...(name ? { name } : {}) },
    };
  }
}

