import {
  BadRequestException,
  Body,
  Controller,
  Get,
  Param,
  Post,
  Query,
  Req,
  UnprocessableEntityException,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { CvJobsService } from './cv-jobs.service';
import { SearchService } from '../search/search.service';

@Controller('cv-jobs')
@UseGuards(JwtAuthGuard)
export class CvJobsController {
  constructor(
    private readonly jobs: CvJobsService,
    private readonly search: SearchService,
  ) {}

  @Post('text')
  async createTextJob(
    @Req() req,
    @Body() body: { cvText?: string; fileName?: string; topK?: number; location?: string; contractType?: string },
  ) {
    const cvText = String(body?.cvText ?? '').trim();
    if (cvText.length < 10) throw new BadRequestException('CV texte trop court');
    const assessment = await this.search.assessCvTextWithModel(cvText, {
      useLlm: true,
    });
    if (assessment.documentKind === 'non_cv') {
      throw new UnprocessableEntityException({
        code: 'NOT_A_CV',
        message: assessment.userMessage,
        documentKind: assessment.documentKind,
        cvConfidence: assessment.cvConfidence,
      });
    }
    return this.jobs.createTextJob(String(req.user.userId), {
      cvText,
      fileName: body?.fileName,
      topK: Number(body?.topK ?? 5),
      location: body?.location,
      contractType: body?.contractType,
    });
  }

  @Post('upload')
  @UseInterceptors(FileInterceptor('file', { limits: { fileSize: 8 * 1024 * 1024 } }))
  async createUploadJob(
    @Req() req,
    @UploadedFile() file?: Express.Multer.File,
    @Body() body?: { topK?: string | number; location?: string; contractType?: string },
  ) {
    if (!file?.buffer?.length) throw new BadRequestException('Fichier requis');
    return this.jobs.createUploadJob(String(req.user.userId), {
      fileName: file.originalname || 'cv.pdf',
      mimeType: file.mimetype || 'application/octet-stream',
      bytes: file.buffer,
      topK: Number(body?.topK ?? 5),
      location: body?.location,
      contractType: body?.contractType,
    });
  }

  @Get(':id')
  async getJob(@Req() req, @Param('id') id: string) {
    return this.jobs.getJob(String(req.user.userId), id);
  }

  @Get()
  async listJobs(@Req() req, @Query('status') status?: string, @Query('limit') limit?: string) {
    return this.jobs.listJobs(
      String(req.user.userId),
      status?.trim() || undefined,
      Number(limit || '20'),
    );
  }
}
