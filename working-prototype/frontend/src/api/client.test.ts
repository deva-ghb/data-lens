import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiGet, apiSend, shouldRetry } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiGet", () => {
  it("apiGet throws ApiError with status and message on 403", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(403, { code: "forbidden", message: "You cannot see this." }),
      ),
    );

    const error = await apiGet("/api/people").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 403,
      code: "forbidden",
      message: "You cannot see this.",
    });
  });

  it("returns parsed JSON and sends cookies", async () => {
    const fetchStub = vi.fn().mockResolvedValue(jsonResponse(200, { status: "ok" }));
    vi.stubGlobal("fetch", fetchStub);

    const result = await apiGet<{ status: string }>("/api/health");

    expect(result).toEqual({ status: "ok" });
    expect(fetchStub).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("reads a plain detail string from the server error body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { detail: "Already approved." })),
    );

    await expect(apiGet("/api/permits/1")).rejects.toMatchObject({
      status: 409,
      code: "http_409",
      message: "Already approved.",
    });
  });

  it("throws ApiError invalid_response when a 2xx body is not valid JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>proxy page</html>", { status: 200 })),
    );

    const error = await apiGet("/api/health").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 200, code: "invalid_response" });
  });

  it("still throws ApiError when the error body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("Bad gateway", { status: 502, statusText: "Bad Gateway" }),
      ),
    );

    await expect(apiGet("/api/health")).rejects.toMatchObject({
      status: 502,
      code: "http_502",
      message: "Bad Gateway",
    });
  });
});

describe("apiSend", () => {
  it("sends the method, a JSON body and cookies", async () => {
    const fetchStub = vi.fn().mockResolvedValue(jsonResponse(200, { id: 7 }));
    vi.stubGlobal("fetch", fetchStub);

    const result = await apiSend<{ id: number }>("POST", "/api/things", { name: "a" });

    expect(result).toEqual({ id: 7 });
    expect(fetchStub).toHaveBeenCalledWith(
      "/api/things",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ name: "a" }),
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("sends no body when none is given and tolerates an empty 204", async () => {
    const fetchStub = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchStub);

    const result = await apiSend<undefined>("DELETE", "/api/things/7");

    expect(result).toBeUndefined();
    const init = fetchStub.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("DELETE");
    expect(init.body).toBeUndefined();
  });

  it("throws ApiError on an invalid state change", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(409, { code: "invalid_state", message: "Already approved." }),
      ),
    );

    await expect(apiSend("POST", "/api/swaps/1/decline", { reason: "x" })).rejects.toMatchObject({
      status: 409,
      code: "invalid_state",
    });
  });
});

describe("shouldRetry", () => {
  it("never retries an answer the server meant, like not found or forbidden", () => {
    expect(shouldRetry(0, new ApiError(404, "not_found", "x"))).toBe(false);
    expect(shouldRetry(0, new ApiError(403, "forbidden", "x"))).toBe(false);
    expect(shouldRetry(0, new ApiError(422, "invalid_input", "x"))).toBe(false);
  });

  it("retries a server or network failure at most twice", () => {
    expect(shouldRetry(0, new ApiError(503, "unavailable", "x"))).toBe(true);
    expect(shouldRetry(1, new TypeError("Failed to fetch"))).toBe(true);
    expect(shouldRetry(2, new ApiError(500, "error", "x"))).toBe(false);
  });
});
