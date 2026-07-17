import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { RepositoryReviewReportSchema } from "@/contracts/reports.contract";

const uuidSchema = z.string().uuid();

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const requestId = request.headers.get("x-request-id") || crypto.randomUUID();

  // 1. Require BACKEND_API_URL environment variable
  const backendApiUrl = process.env.BACKEND_API_URL;
  if (!backendApiUrl) {
    console.error("BFF Error: BACKEND_API_URL environment variable is missing.");
    return NextResponse.json(
      { message: "BACKEND_API_URL is not configured." },
      { status: 500 }
    );
  }

  try {
    // 2. Validate id parameter using Next.js 15 async params contract
    const { id } = await context.params;
    if (!id) {
      return NextResponse.json({ message: "analysis_id is required." }, { status: 400 });
    }

    const uuidValidation = uuidSchema.safeParse(id);
    if (!uuidValidation.success) {
      return NextResponse.json(
        { message: "analysis_id must be a valid UUID." },
        { status: 400 }
      );
    }

    // 3. Forward request to FastAPI backend report endpoint
    let response: Response;
    try {
      response = await fetch(`${backendApiUrl}/api/v1/analysis/${id}/report`, {
        method: "GET",
        headers: {
          "X-Request-ID": requestId,
        },
      });
    } catch (networkError) {
      console.error("BFF report query network failure:", networkError);
      return NextResponse.json(
        { message: "Upstream report service is temporarily unavailable." },
        { status: 503 }
      );
    }

    const statusCode = response.status;
    const responseHeaders: Record<string, string> = {};
    const contentType = response.headers.get("content-type");
    if (contentType) {
      responseHeaders["content-type"] = contentType;
    }

    // Handle specific status code groups
    if (statusCode === 400 || statusCode === 422 || statusCode === 404) {
      const errorJson = await response.json().catch(() => ({}));
      return NextResponse.json(errorJson, { status: statusCode, headers: responseHeaders });
    }

    if (statusCode >= 500) {
      console.error(`BFF received ${statusCode} from backend during report check.`);
      return NextResponse.json(
        { message: "Bad Gateway. The upstream service encountered an internal error." },
        { status: 502 }
      );
    }

    // Read and parse successful responses
    let jsonBody: unknown;
    try {
      jsonBody = await response.json();
    } catch (parseError) {
      console.error("BFF failed to parse successful backend JSON response:", parseError);
      return NextResponse.json(
        { message: "Bad Gateway. Invalid response format from upstream service." },
        { status: 502 }
      );
    }

    // Validate utilizing the existing Zod contract schema
    const parseResult = RepositoryReviewReportSchema.safeParse(jsonBody);
    if (!parseResult.success) {
      console.error("BFF failed to validate report against contract schema:", parseResult.error.format());
      return NextResponse.json(
        { message: "Bad Gateway. Upstream response failed validation contract verification." },
        { status: 502 }
      );
    }

    return NextResponse.json(parseResult.data, {
      status: statusCode,
      headers: responseHeaders,
    });

  } catch (err) {
    console.error("BFF unhandled error in report query route handler:", err);
    return NextResponse.json(
      { message: "Internal Server Error." },
      { status: 500 }
    );
  }
}
