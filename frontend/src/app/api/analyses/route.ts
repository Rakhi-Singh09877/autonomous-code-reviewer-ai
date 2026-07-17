import { NextRequest, NextResponse } from "next/server";
import { AnalysisInitiateResponseSchema } from "@/contracts/analysis.contract";

export async function POST(request: NextRequest) {
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
    const formData = await request.formData();

    // Extract raw form parameters
    const gitUrlVal = formData.get("git_url");
    const fileVal = formData.get("file");
    const branchVal = formData.get("branch");
    const maxIssuesVal = formData.get("max_issues_per_file");

    let gitUrl: string | null = null;
    let file: File | null = null;
    let branch: string | null = null;
    let maxIssues: string | null = null;

    // 2. Validate and trim git_url
    if (gitUrlVal !== null) {
      if (typeof gitUrlVal !== "string") {
        return NextResponse.json({ message: "git_url must be a string." }, { status: 400 });
      }
      const trimmedGit = gitUrlVal.trim();
      if (trimmedGit) {
        try {
          new URL(trimmedGit);
          gitUrl = trimmedGit;
        } catch {
          return NextResponse.json({ message: "git_url must be a valid URL." }, { status: 400 });
        }
      }
    }

    // 3. Validate file type
    if (fileVal !== null) {
      if (!(fileVal instanceof File)) {
        return NextResponse.json({ message: "file must be a File upload." }, { status: 400 });
      }
      file = fileVal;
    }

    // Mutually exclusive checks
    if (!gitUrl && !file) {
      return NextResponse.json(
        { message: "Either git_url or file upload must be provided." },
        { status: 400 }
      );
    }

    if (gitUrl && file) {
      return NextResponse.json(
        { message: "Provide either git_url or file upload, not both." },
        { status: 400 }
      );
    }

    if (file) {
      if (!file.name.toLowerCase().endsWith(".zip")) {
        return NextResponse.json(
          { message: "Only ZIP archives are supported." },
          { status: 400 }
        );
      }
    }

    // 4. Validate and trim branch
    if (branchVal !== null) {
      if (typeof branchVal !== "string") {
        return NextResponse.json({ message: "branch must be a string." }, { status: 400 });
      }
      const trimmedBranch = branchVal.trim();
      if (!trimmedBranch) {
        return NextResponse.json({ message: "branch cannot be empty." }, { status: 400 });
      }
      branch = trimmedBranch;
    }

    // 5. Validate, normalize, and trim focus_areas
    const focusAreasVals = formData.getAll("focus_areas");
    let normalizedFocusAreas: string | null = null;
    if (focusAreasVals.length > 0) {
      const areasList: string[] = [];
      for (const val of focusAreasVals) {
        if (typeof val !== "string") {
          return NextResponse.json({ message: "focus_areas must contain strings." }, { status: 400 });
        }
        const trimmed = val.trim();
        if (trimmed) {
          trimmed.split(",").forEach((item) => {
            const itemTrimmed = item.trim();
            if (itemTrimmed) {
              areasList.push(itemTrimmed);
            }
          });
        }
      }
      if (areasList.length > 0) {
        normalizedFocusAreas = areasList.join(",");
      }
    }

    // 6. Validate max_issues_per_file
    if (maxIssuesVal !== null) {
      if (typeof maxIssuesVal !== "string") {
        return NextResponse.json({ message: "max_issues_per_file must be a string." }, { status: 400 });
      }
      const parsedIssues = Number(maxIssuesVal);
      if (isNaN(parsedIssues) || !Number.isInteger(parsedIssues) || parsedIssues <= 0) {
        return NextResponse.json(
          { message: "max_issues_per_file must be a positive integer." },
          { status: 400 }
        );
      }
      maxIssues = maxIssuesVal;
    }

    // 7. Rebuild a new FormData instance instead of forwarding original
    const outgoingFormData = new FormData();
    if (gitUrl) outgoingFormData.append("git_url", gitUrl);
    if (branch) outgoingFormData.append("branch", branch);
    if (file) outgoingFormData.append("file", file);
    if (normalizedFocusAreas) outgoingFormData.append("focus_areas", normalizedFocusAreas);
    if (maxIssues) outgoingFormData.append("max_issues_per_file", maxIssues);

    // 8. Forward to the FastAPI backend analyze route
    let response: Response;
    try {
      response = await fetch(`${backendApiUrl}/api/v1/analyze`, {
        method: "POST",
        body: outgoingFormData,
        headers: {
          "X-Request-ID": requestId,
        },
      });
    } catch (networkError) {
      console.error("BFF analysis submission network failure:", networkError);
      return NextResponse.json(
        { message: "Upstream analysis service is temporarily unavailable." },
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
      console.error(`BFF received ${statusCode} from backend during analysis submit.`);
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
    const parseResult = AnalysisInitiateResponseSchema.safeParse(jsonBody);
    if (!parseResult.success) {
      console.error("BFF failed to validate response against contract schema:", parseResult.error.format());
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
    console.error("BFF unhandled error in analysis submission route handler:", err);
    return NextResponse.json(
      { message: "Internal Server Error." },
      { status: 500 }
    );
  }
}
