// Users Controller

import { Controller, Get, Patch, Body, UseGuards, Req } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { UsersService } from './users.service';

@Controller('users')
@UseGuards(JwtAuthGuard)
export class UsersController {
  constructor(private usersService: UsersService) {}

  @Get('me')
  async getProfile(@Req() req) {
    return this.usersService.findById(req.user.userId);
  }

  @Patch('me')
  async updateProfile(@Req() req, @Body() data: any) {
    return this.usersService.updateProfile(req.user.userId, data);
  }

  @Get('preferences')
  async getPreferences(@Req() req) {
    return this.usersService.getPreferences(req.user.userId);
  }
}
