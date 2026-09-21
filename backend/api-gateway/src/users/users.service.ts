// Users Service

import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { RuntimeCacheService } from '../runtime/runtime-cache.service';

@Injectable()
export class UsersService {
  constructor(
    private prisma: PrismaService,
    private readonly runtimeCache: RuntimeCacheService,
  ) {}

  async findById(id: string) {
    const user = await this.prisma.user.findUnique({
      where: { id },
      select: {
        id: true,
        email: true,
        name: true,
        phone: true,
        location: true,
        headline: true,
        preferredRoles: true,
        preferredCountry: true,
      },
    });

    if (!user) throw new NotFoundException('Utilisateur non trouve');
    return user;
  }

  async updateProfile(userId: string, data: any) {
    const updated = await this.prisma.user.update({
      where: { id: userId },
      data: {
        name: data.name,
        phone: data.phone,
        location: data.location,
        headline: data.headline,
        preferredRoles: data.preferredRoles,
        preferredCountry: data.preferredCountry,
      },
    });

    await this.runtimeCache.bump('profile');
    return updated;
  }

  async getPreferences(userId: string) {
    return this.prisma.user.findUnique({
      where: { id: userId },
      select: {
        preferredRoles: true,
        preferredCountry: true,
        location: true,
      },
    });
  }
}
