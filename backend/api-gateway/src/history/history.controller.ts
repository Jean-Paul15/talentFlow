// History Controller

import { Controller, Get, Post, Delete, Body, Param, UseGuards, Req, Query } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { HistoryService } from './history.service';

@Controller('history')
@UseGuards(JwtAuthGuard)
export class HistoryController {
  constructor(private historyService: HistoryService) {}

  @Get()
  async getHistory(
    @Req() req,
    @Query('limit') limit = 50,
    @Query('offset') offset = 0,
  ) {
    return this.historyService.getHistory(req.user.userId, +limit, +offset);
  }

  @Post()
  async saveAnalysis(@Req() req, @Body() data: any) {
    return this.historyService.saveAnalysis(req.user.userId, data);
  }

  @Get(':id')
  async getHistoryEntry(@Req() req, @Param('id') historyId: string) {
    return this.historyService.getHistoryEntry(req.user.userId, historyId);
  }

  @Delete(':id')
  async deleteAnalysis(@Req() req, @Param('id') analysisId: string) {
    return this.historyService.deleteAnalysis(req.user.userId, analysisId);
  }
}
