import { Controller, Get, Param, Req, Res, UseGuards } from '@nestjs/common';
import { Response } from 'express';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { ReportsService } from './reports.service';

@Controller('reports')
@UseGuards(JwtAuthGuard)
export class ReportsController {
  constructor(private readonly reportsService: ReportsService) {}

  @Get('history/:id.pdf')
  async downloadHistoryPdf(
    @Req() req,
    @Param('id') id: string,
    @Res() res: Response,
  ) {
    const userId = String(req.user.userId);
    const report = await this.reportsService.buildHistoryPdf(userId, id);
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${report.fileName}"`,
    );
    res.setHeader('Content-Length', report.bytes.length.toString());
    res.send(report.bytes);
  }
}

