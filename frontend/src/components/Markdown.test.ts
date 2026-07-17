import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Markdown } from "@/components/Markdown";

function render(markdown: string): string {
  return renderToStaticMarkup(createElement(Markdown, null, markdown));
}

describe("Markdown", () => {
  it("renders plain bold as <strong>", () => {
    const html = render("Das ist **wichtig**.");
    expect(html).toContain("<strong");
    expect(html).toContain("wichtig");
    expect(html).not.toContain("**");
  });

  it("closes bold between CJK punctuation and a CJK letter", () => {
    // CommonMark alone leaves the ** literal here — remark-cjk-friendly fixes it.
    const html = render("向 **Familienkasse（家庭金辦公室）**申請。");
    expect(html).toContain("<strong");
    expect(html).toContain("家庭金辦公室");
    expect(html).not.toContain("**");
  });

  it("closes bold directly after a CJK full-width paren", () => {
    const html = render("**Familiengericht（家庭法院）**是主管機關。");
    expect(html).not.toContain("**");
    expect(html).toContain("<strong");
  });
});
