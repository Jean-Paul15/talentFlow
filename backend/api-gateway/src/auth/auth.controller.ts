// Auth Controller

import { Controller, Post, Body, HttpCode } from '@nestjs/common';
import { AuthService } from './auth.service';

@Controller('auth')
export class AuthController {
  constructor(private authService: AuthService) {}

  @Post('register')
  async register(
    @Body()
    body: {
      email: string;
      password: string;
      name: string;
      acceptTerms?: boolean;
    },
  ) {
    return this.authService.register(
      body.email,
      body.password,
      body.name,
      Boolean(body.acceptTerms),
    );
  }

  @Post('login')
  @HttpCode(200)
  async login(@Body() body: { email: string; password: string }) {
    return this.authService.login(body.email, body.password);
  }

  @Post('refresh')
  @HttpCode(200)
  async refresh(@Body() body: { refreshToken?: string }) {
    return this.authService.refresh(String(body?.refreshToken || ''));
  }
}
