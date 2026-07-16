import { AnalysisStatusResponseDTO } from "../../../contracts/analysis.contract";
import { Analysis } from "../../../domain/entities/analysis.entity";

export class AnalysisMapper {
  public static toDomain(dto: AnalysisStatusResponseDTO): Analysis {
    return new Analysis(
      dto.analysis_id,
      dto.status,
      dto.progress_percentage,
      dto.current_file,
      dto.total_files,
      dto.errors
    );
  }
}
