// @vitest-environment happy-dom

import { describe, it, expect, vi, beforeEach } from "vitest";
import { openRenameModal } from "./rename-modal";
import { ApiError, type EditorApi, type RenamePlan } from "./api";

beforeEach(() => {
  document.body.innerHTML = "";
});

function tick(ms = 300): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const samplePlan: RenamePlan = {
  old: "foo",
  new: "bar",
  kind: "alias",
  edits: [
    {
      path: "concepts/foo.md",
      old_text: "old",
      new_text: "new",
      hunks: [
        { hunk_id: "h1", header: "@@ -1,1 +1,1 @@", lines: ["-foo", "+bar"] },
      ],
    },
  ],
};

function makeApi(overrides: Partial<EditorApi> = {}): EditorApi {
  const base: Partial<EditorApi> = {
    renamePreview: vi.fn().mockResolvedValue(samplePlan),
    renameApply: vi.fn().mockResolvedValue({ affected_files: ["concepts/foo.md"], plan: samplePlan }),
    ...overrides,
  };
  return base as EditorApi;
}

describe("openRenameModal", () => {
  it("renders the modal with prefilled current name and disabled apply", () => {
    openRenameModal({
      api: makeApi(),
      corpusId: "c1",
      kind: "alias",
      currentName: "foo",
      parent: document.body,
      onSuccess: () => {},
    });
    const overlay = document.querySelector(".attune-modal-rename");
    expect(overlay).toBeTruthy();
    const fromInput = overlay!.querySelector(
      ".attune-rename-inputs input:first-of-type",
    ) as HTMLInputElement;
    expect(fromInput.value).toBe("foo");
    expect(fromInput.disabled).toBe(true);
    const apply = overlay!.querySelector(
      ".attune-modal-foot .attune-btn-primary",
    ) as HTMLButtonElement;
    expect(apply.disabled).toBe(true);
  });

  it("debounces preview, renders the plan, and enables apply", async () => {
    const api = makeApi();
    openRenameModal({
      api,
      corpusId: "c1",
      kind: "alias",
      currentName: "foo",
      parent: document.body,
      onSuccess: () => {},
    });
    const toInput = document.querySelectorAll(
      ".attune-rename-inputs input",
    )[1] as HTMLInputElement;
    toInput.value = "bar";
    toInput.dispatchEvent(new Event("input"));
    await tick();
    expect(api.renamePreview).toHaveBeenCalledWith("c1", {
      old: "foo",
      new: "bar",
      kind: "alias",
    });
    const summary = document.querySelector(".attune-rename-summary");
    expect(summary?.textContent).toMatch(/affects 1 file/);
    const fileHead = document.querySelector(".attune-rename-file-head");
    expect(fileHead?.textContent).toBe("concepts/foo.md");
    const apply = document.querySelector(
      ".attune-modal-foot .attune-btn-primary",
    ) as HTMLButtonElement;
    expect(apply.disabled).toBe(false);
  });

  it("treats an empty plan as a no-op and keeps apply disabled", async () => {
    const api = makeApi({
      renamePreview: vi.fn().mockResolvedValue({
        old: "foo",
        new: "bar",
        kind: "alias",
        edits: [],
      } as RenamePlan),
    });
    openRenameModal({
      api,
      corpusId: "c1",
      kind: "alias",
      currentName: "foo",
      parent: document.body,
      onSuccess: () => {},
    });
    const toInput = document.querySelectorAll(
      ".attune-rename-inputs input",
    )[1] as HTMLInputElement;
    toInput.value = "bar";
    toInput.dispatchEvent(new Event("input"));
    await tick();
    expect(document.querySelector(".attune-rename-summary")?.textContent).toMatch(
      /no-op/,
    );
    const apply = document.querySelector(
      ".attune-modal-foot .attune-btn-primary",
    ) as HTMLButtonElement;
    expect(apply.disabled).toBe(true);
  });

  it("renders a 409 collision banner with the owning path", async () => {
    const api = makeApi({
      renamePreview: vi.fn().mockRejectedValue(
        new ApiError("HTTP 409", 409, {
          detail: {
            code: "name_collision",
            message: "duplicate alias 'bar'",
            owning_path: "concepts/baz.md",
          },
        }),
      ),
    });
    openRenameModal({
      api,
      corpusId: "c1",
      kind: "alias",
      currentName: "foo",
      parent: document.body,
      onSuccess: () => {},
    });
    const toInput = document.querySelectorAll(
      ".attune-rename-inputs input",
    )[1] as HTMLInputElement;
    toInput.value = "bar";
    toInput.dispatchEvent(new Event("input"));
    await tick();
    const banner = document.querySelector(".attune-modal-lint");
    expect(banner?.textContent).toMatch(/collision/i);
    expect(banner?.textContent).toMatch(/concepts\/baz\.md/);
  });

  it("calls onSuccess after a successful apply and reports affected files", async () => {
    const onSuccess = vi.fn();
    const api = makeApi();
    openRenameModal({
      api,
      corpusId: "c1",
      kind: "alias",
      currentName: "foo",
      parent: document.body,
      onSuccess,
    });
    const toInput = document.querySelectorAll(
      ".attune-rename-inputs input",
    )[1] as HTMLInputElement;
    toInput.value = "bar";
    toInput.dispatchEvent(new Event("input"));
    await tick();
    const apply = document.querySelector(
      ".attune-modal-foot .attune-btn-primary",
    ) as HTMLButtonElement;
    apply.click();
    await tick(50);
    expect(api.renameApply).toHaveBeenCalledWith("c1", {
      old: "foo",
      new: "bar",
      kind: "alias",
    });
    expect(onSuccess).toHaveBeenCalledWith(
      ["concepts/foo.md"],
      expect.objectContaining({ old: "foo", new: "bar" }),
    );
    expect(document.querySelector(".attune-modal-rename")).toBeNull();
  });

  it("clears state when the new name matches the old name", async () => {
    const api = makeApi();
    openRenameModal({
      api,
      corpusId: "c1",
      kind: "tag",
      currentName: "skill",
      parent: document.body,
      onSuccess: () => {},
    });
    const toInput = document.querySelectorAll(
      ".attune-rename-inputs input",
    )[1] as HTMLInputElement;
    toInput.value = "skill";
    toInput.dispatchEvent(new Event("input"));
    await tick(60);
    expect(api.renamePreview).not.toHaveBeenCalled();
    const apply = document.querySelector(
      ".attune-modal-foot .attune-btn-primary",
    ) as HTMLButtonElement;
    expect(apply.disabled).toBe(true);
  });
});
