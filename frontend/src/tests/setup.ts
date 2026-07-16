import { beforeAll, afterEach, afterAll } from "vitest";
import { server } from "./mocks/server";

// Mock matchMedia for responsive UI layout checks
if (typeof window !== "undefined") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  console.log("MSW Mock Server listening started successfully");
});

// Reset any runtime request handlers declared during tests
afterEach(() => {
  server.resetHandlers();
});

// Clean up after the tests are finished
afterAll(() => {
  server.close();
  console.log("MSW Mock Server closed successfully");
});
