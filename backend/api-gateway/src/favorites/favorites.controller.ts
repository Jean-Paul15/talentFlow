// Favorites Controller

import { Controller, Get, Post, Delete, Body, Param, UseGuards, Req, Query } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { FavoritesService } from './favorites.service';

@Controller('favorites')
@UseGuards(JwtAuthGuard)
export class FavoritesController {
  constructor(private favoritesService: FavoritesService) {}

  @Get()
  async getFavorites(
    @Req() req,
    @Query('limit') limit = 20,
    @Query('offset') offset = 0,
  ) {
    return this.favoritesService.getFavorites(req.user.userId, +limit, +offset);
  }

  @Post()
  async addFavorite(@Req() req, @Body() data: any) {
    return this.favoritesService.addFavorite(req.user.userId, data.jobId, data);
  }

  @Delete(':jobId')
  async removeFavorite(@Req() req, @Param('jobId') jobId: string) {
    return this.favoritesService.removeFavorite(req.user.userId, jobId);
  }

  @Get(':jobId')
  async isFavorite(@Req() req, @Param('jobId') jobId: string) {
    const isFav = await this.favoritesService.isFavorite(req.user.userId, jobId);
    return { isFavorite: isFav };
  }
}
