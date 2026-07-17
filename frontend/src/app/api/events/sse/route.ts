import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const uuidSchema = z.string().uuid();

export async function GET(request: NextRequest) {
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

  const searchParams = request.nextUrl.searchParams;
  const analysisId = searchParams.get("analysis_id");

  if (!analysisId) {
    return NextResponse.json(
      { message: "analysis_id query parameter is required." },
      { status: 400 }
    );
  }

  const uuidValidation = uuidSchema.safeParse(analysisId);
  if (!uuidValidation.success) {
    return NextResponse.json(
      { message: "analysis_id must be a valid UUID." },
      { status: 400 }
    );
  }

  try {
    const upstreamUrl = `${backendApiUrl}/api/v1/events/sse?analysis_id=${analysisId}`;
    const response = await fetch(upstreamUrl, {
      method: "GET",
      headers: {
        "X-Request-ID": requestId,
        "Accept": "text/event-stream",
      },
    });

    const statusCode = response.status;

    if (statusCode === 400 || statusCode === 422 || statusCode === 404) {
      const errorJson = await response.json().catch(() => ({}));
      return NextResponse.json(errorJson, { status: statusCode });
    }

    if (statusCode >= 500) {
      console.error(`BFF received ${statusCode} from backend during SSE connection.`);
      return NextResponse.json(
        { message: "Bad Gateway. The upstream service encountered an internal error." },
        { status: 502 }
      );
    }

    // Stream the response body directly to prevent buffering
    return new Response(response.body, {
      status: statusCode,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });

  } catch (networkError) {
    console.error("BFF SSE stream query network failure:", networkError);
    return NextResponse.json(
      { message: "Upstream events service is temporarily unavailable." },
      { status: 503 }
    );
  }
}
