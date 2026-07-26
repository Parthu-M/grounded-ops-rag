import { describe, expect, it } from "vitest";
import { demoQuery } from "./data";

describe("demoQuery", () => {
  it("returns a cited grounded answer for a known question", () => {
    const result = demoQuery(
      "How quickly is a Priority One incident acknowledged?",
    );
    expect(result.answer).toContain("within 15 minutes");
    expect(result.citations).toHaveLength(1);
    expect(result.contexts[0].metadata.source).toBe("reliability.md");
  });

  it("abstains when the demo corpus has no relevant context", () => {
    const result = demoQuery("What is the cafeteria lunch menu?");
    expect(result.citations).toHaveLength(0);
    expect(result.contexts).toHaveLength(0);
    expect(result.answer).toContain("enough relevant context");
  });
});
