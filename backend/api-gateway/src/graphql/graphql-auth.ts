import { getJwtSecret } from '../auth/jwt-secret';
import { JwtService } from '@nestjs/jwt';
import { UnauthorizedException } from '@nestjs/common';

export function extractUserIdFromContext(context: any, jwtService: JwtService): string {
  const header =
    context?.req?.headers?.authorization ||
    context?.req?.headers?.Authorization ||
    '';
  if (!header || typeof header !== 'string' || !header.startsWith('Bearer ')) {
    throw new UnauthorizedException('Token Bearer requis');
  }

  const token = header.slice('Bearer '.length).trim();
  if (!token) {
    throw new UnauthorizedException('Token Bearer requis');
  }

  try {
    const payload = jwtService.verify(token, {
      secret: getJwtSecret(),
    }) as any;
    const userId = payload?.sub;
    if (!userId) throw new Error('Invalid payload');
    return String(userId);
  } catch {
    throw new UnauthorizedException('Token invalide');
  }
}
