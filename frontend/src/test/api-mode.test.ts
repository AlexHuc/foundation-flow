import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mode behavior is decided at module load from the environment, so each test
// re-imports the module with a fresh registry and a stubbed VITE_API_BASE_URL.

async function importApi(baseUrl?: string) {
  vi.resetModules();
  if (baseUrl === undefined) {
    vi.unstubAllEnvs();
  } else {
    vi.stubEnv("VITE_API_BASE_URL", baseUrl);
  }
  return await import("@/lib/api");
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("demo mode (no API base URL configured)", () => {
  it("serves clearly labeled illustrative data", async () => {
    const api = await importApi(undefined);
    expect(api.REAL_DATA_MODE).toBe(false);
    const result = await api.getCompanyData("CRDO");
    expect(result?.source).toBe("illustrative");
    const list = await api.listCompaniesData();
    expect(list.source).toBe("illustrative");
    expect(list.companies.length).toBeGreaterThan(0);
  });
});

describe("real-data mode (API base URL configured)", () => {
  it("rejects with ApiConnectionError when the backend is unreachable — never falls back to sample data", async () => {
    const api = await importApi("http://127.0.0.1:9"); // port 9: nothing listens
    expect(api.REAL_DATA_MODE).toBe(true);
    await expect(api.getCompanyData("CRDO")).rejects.toBeInstanceOf(api.ApiConnectionError);
    await expect(api.listCompaniesData()).rejects.toBeInstanceOf(api.ApiConnectionError);
  });

  it("rejects on HTTP 500 instead of substituting illustrative data", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("boom", { status: 500 })));
    const api = await importApi("http://api.test");
    await expect(api.getCompanyData("CRDO")).rejects.toThrow();
    await expect(api.listCompaniesData()).rejects.toThrow();
  });

  it("returns null for an unknown ticker (404) so the route can show not-found", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("not found", { status: 404 })));
    const api = await importApi("http://api.test");
    await expect(api.getCompanyData("NOPE")).resolves.toBeNull();
  });

  it("returns an empty company list as a valid empty state, not a fallback", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("[]", { status: 200 })));
    const api = await importApi("http://api.test");
    const list = await api.listCompaniesData();
    expect(list.source).toBe("api");
    expect(list.companies).toEqual([]);
  });
});
