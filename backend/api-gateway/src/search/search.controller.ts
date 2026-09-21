// Search Controller

import {
  BadRequestException,
  Body,
  Controller,
  Post,
  Req,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { SearchService } from './search.service';

@Controller('search')
@UseGuards(JwtAuthGuard)
export class SearchController {
  constructor(private searchService: SearchService) {}

  @Post()
  async searchJobs(@Body() data: any) {
    return this.searchService.searchJobs(data.query, data.filters);
  }

  @Post('analyze')
  async analyzeCV(@Req() req, @Body() data: any) {
    const result = await this.searchService.analyzeCV(data.cvId, data.jobId);
    
    // Sauvegarder dans l'historique
    // (sera fait via le service history)
    
    return result;
  }

  @Post('improve-cv')
  async improveCv(@Req() req, @Body() data: any) {
    return this.searchService.improveCv(data.cvId, data.jobId);
  }

  @Post('extract-cv-text')
  @UseInterceptors(
    FileInterceptor('file', {
      limits: { fileSize: 5 * 1024 * 1024 },
    }),
  )
  async extractCvText(@UploadedFile() file?: Express.Multer.File) {
    if (!file) {
      throw new BadRequestException('Fichier CV requis.');
    }
    return this.searchService.extractCvText(file);
  }
}
