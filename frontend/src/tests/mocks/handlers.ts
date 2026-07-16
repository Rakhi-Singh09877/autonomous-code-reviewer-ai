import { http, HttpResponse } from "msw";

export const handlers = [
  // Intercept backend-for-frontend health checks for the test suite
  http.get("*/api/health", () => {
    return HttpResponse.json({ status: "healthy" });
  }),
];
export default handlers;
