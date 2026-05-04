// @vitest-environment happy-dom

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mountCorpusSwitcher,
  promptUnsavedEdits,
} from "./corpus-switcher";
import type { CorpusEntry, CorpusListResponse, EditorApi } from "./api";

const SAMPLE_LIST: CorpusListResponse = {
  active: "help",
  corpora: [
    {
      id: "help",
      name: "Help docs",
      path: "/repo/help",
      kind: "source",
      warn_on_edit: false,
    },
    {
      id: "draft",
      name: "Draft templates",
      path: "/repo/drafts",
      kind: "ad-hoc",
      warn_on_edit: false,
    },
    {
      id: "gen",
      name: "Generated",
      path: "/repo/gen",
      kind: "generated",
      warn_on_edit: true,
    },
  ],
};

beforeEach(() => {
  document.body.innerHTML = "";
});

function makeApi(overrides: Partial<EditorApi> = {}): EditorApi {
  const api: Partial<EditorApi> = {
    listCorpora: vi.fn().mockResolvedValue(SAMPLE_LIST),
    setActiveCorpus: vi.fn().mockResolvedValue(SAMPLE_LIST.corpora[1]),
    registerCorpus: vi.fn().mockResolvedValue({
      id: "new",
      name: "New",
      path: "/new",
      kind: "source",
      warn_on_edit: false,
    } as CorpusEntry),
    ...overrides,
  };
  return api as EditorApi;
}

function tick(ms = 50): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function makeTrigger(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("mountCorpusSwitcher", () => {
  it("renders a button labelled with the active corpus name + path", async () => {
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api: makeApi(),
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      initialCorpusId: "help",
      initialPath: "tasks/use-help.md",
      onSwitchRequested: () => true,
      onSwitched: () => {},
    });
    await tick();
    const btn = trigger.querySelector(".attune-corpus-switcher") as HTMLButtonElement;
    expect(btn).toBeTruthy();
    expect(btn.textContent).toContain("Help docs");
    expect(btn.textContent).toContain("tasks/use-help.md");
  });

  it("opens the panel and lists every registered corpus", async () => {
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api: makeApi(),
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      initialCorpusId: "help",
      initialPath: "x",
      onSwitchRequested: () => true,
      onSwitched: () => {},
    });
    await tick();
    (trigger.querySelector(".attune-corpus-switcher") as HTMLElement).click();
    await tick();
    const items = document.querySelectorAll(".attune-corpus-item");
    expect(items.length).toBe(3);
    const active = document.querySelector(".attune-corpus-item-active");
    expect(active?.textContent).toContain("Help docs");
  });

  it("hides the search input below the SEARCH_THRESHOLD", async () => {
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api: makeApi(),
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      initialCorpusId: "help",
      initialPath: "x",
      onSwitchRequested: () => true,
      onSwitched: () => {},
    });
    await tick();
    (trigger.querySelector(".attune-corpus-switcher") as HTMLElement).click();
    await tick();
    expect(document.querySelector(".attune-corpus-search")).toBeNull();
  });

  it("shows the search input when there are more than 10 corpora and filters live", async () => {
    const many: CorpusListResponse = {
      active: "c0",
      corpora: Array.from({ length: 12 }, (_, i) => ({
        id: `c${i}`,
        name: i === 5 ? "needle-target" : `Corpus ${i}`,
        path: `/p/${i}`,
        kind: "source" as const,
        warn_on_edit: false,
      })),
    };
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api: makeApi({ listCorpora: vi.fn().mockResolvedValue(many) }),
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      initialCorpusId: "c0",
      initialPath: "x",
      onSwitchRequested: () => true,
      onSwitched: () => {},
    });
    await tick();
    (trigger.querySelector(".attune-corpus-switcher") as HTMLElement).click();
    await tick();
    const search = document.querySelector(".attune-corpus-search") as HTMLInputElement;
    expect(search).toBeTruthy();
    search.value = "needle";
    search.dispatchEvent(new Event("input"));
    await tick();
    const visible = document.querySelectorAll(".attune-corpus-item");
    expect(visible.length).toBe(1);
    expect(visible[0].textContent).toContain("needle-target");
  });

  it("calls setActiveCorpus and onSwitched when the user picks a different corpus", async () => {
    const api = makeApi();
    const onSwitched = vi.fn();
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api,
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      initialCorpusId: "help",
      initialPath: "x",
      onSwitchRequested: () => true,
      onSwitched,
    });
    await tick();
    (trigger.querySelector(".attune-corpus-switcher") as HTMLElement).click();
    await tick();
    const draftItem = [...document.querySelectorAll(".attune-corpus-item")].find(
      (e) => e.textContent?.includes("Draft templates"),
    ) as HTMLButtonElement;
    draftItem.click();
    await tick();
    expect(api.setActiveCorpus).toHaveBeenCalledWith("draft");
    expect(onSwitched).toHaveBeenCalledWith(
      expect.objectContaining({ id: "draft" }),
    );
  });

  it("aborts when onSwitchRequested returns false", async () => {
    const api = makeApi();
    const onSwitched = vi.fn();
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api,
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      initialCorpusId: "help",
      initialPath: "x",
      onSwitchRequested: () => false,
      onSwitched,
    });
    await tick();
    (trigger.querySelector(".attune-corpus-switcher") as HTMLElement).click();
    await tick();
    const draftItem = [...document.querySelectorAll(".attune-corpus-item")].find(
      (e) => e.textContent?.includes("Draft templates"),
    ) as HTMLButtonElement;
    draftItem.click();
    await tick();
    expect(api.setActiveCorpus).not.toHaveBeenCalled();
    expect(onSwitched).not.toHaveBeenCalled();
  });

  it("labels the trigger with the editing corpus even when the registry's active is different", async () => {
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api: makeApi(),
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      // Editor is on `draft` even though the registry's active is `help`.
      initialCorpusId: "draft",
      initialPath: "tasks/x.md",
      onSwitchRequested: () => true,
      onSwitched: () => {},
    });
    await tick();
    const btn = trigger.querySelector(".attune-corpus-switcher") as HTMLButtonElement;
    expect(btn.textContent).toContain("Draft templates");
    expect(btn.textContent).not.toContain("Help docs");
    btn.click();
    await tick();
    const items = [...document.querySelectorAll(".attune-corpus-item")];
    const draftItem = items.find((i) => i.textContent?.includes("Draft templates"))!;
    const helpItem = items.find((i) => i.textContent?.includes("Help docs"))!;
    // `help` is registry-active; `draft` is what we're editing.
    expect(helpItem.classList.contains("attune-corpus-item-active")).toBe(true);
    expect(helpItem.classList.contains("attune-corpus-item-current")).toBe(false);
    expect(draftItem.classList.contains("attune-corpus-item-current")).toBe(true);
    expect(draftItem.classList.contains("attune-corpus-item-active")).toBe(false);
  });

  it("opens the Add corpus modal and posts to /register", async () => {
    const api = makeApi();
    const trigger = makeTrigger();
    mountCorpusSwitcher({
      api,
      trigger,
      panelParent: document.body,
      modalParent: document.body,
      initialCorpusId: "help",
      initialPath: "x",
      onSwitchRequested: () => true,
      onSwitched: () => {},
    });
    await tick();
    (trigger.querySelector(".attune-corpus-switcher") as HTMLElement).click();
    await tick();
    (document.querySelector(".attune-corpus-add") as HTMLButtonElement).click();
    await tick();
    const modal = document.querySelector(".attune-modal-register");
    expect(modal).toBeTruthy();
    const inputs = modal!.querySelectorAll<HTMLInputElement>(".attune-fm-input");
    inputs[0].value = "My corpus";
    inputs[0].dispatchEvent(new Event("input"));
    inputs[1].value = "/tmp/templates";
    inputs[1].dispatchEvent(new Event("input"));
    const apply = modal!.querySelector(
      ".attune-modal-foot .attune-btn-primary",
    ) as HTMLButtonElement;
    expect(apply.disabled).toBe(false);
    apply.click();
    await tick();
    expect(api.registerCorpus).toHaveBeenCalledWith({
      name: "My corpus",
      path: "/tmp/templates",
      kind: "source",
    });
  });
});

describe("promptUnsavedEdits", () => {
  it("resolves to 'save' when Save is clicked", async () => {
    const promise = promptUnsavedEdits(document.body);
    await tick();
    const save = [...document.querySelectorAll(".attune-modal-unsaved button")].find(
      (b) => b.textContent === "Save…",
    ) as HTMLButtonElement;
    save.click();
    expect(await promise).toBe("save");
  });

  it("resolves to 'discard' when Discard is clicked", async () => {
    const promise = promptUnsavedEdits(document.body);
    await tick();
    const discard = [...document.querySelectorAll(".attune-modal-unsaved button")].find(
      (b) => b.textContent === "Discard",
    ) as HTMLButtonElement;
    discard.click();
    expect(await promise).toBe("discard");
  });

  it("resolves to null when Cancel is clicked", async () => {
    const promise = promptUnsavedEdits(document.body);
    await tick();
    const cancel = [...document.querySelectorAll(".attune-modal-unsaved button")].find(
      (b) => b.textContent === "Cancel",
    ) as HTMLButtonElement;
    cancel.click();
    expect(await promise).toBe(null);
  });
});
