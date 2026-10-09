import Dexie, { type EntityTable } from "dexie";
export type Draft = {
  id: string;
  kind: "inspection" | "observation";
  session: Record<string, unknown>;
  body: Record<string, unknown>;
  photo?: Blob;
  evidenceId?: string;
  createdAt: string;
  error?: string;
};
const db = new Dexie("binmap-field-v1") as Dexie & {
  drafts: EntityTable<Draft, "id">;
};
db.version(1).stores({ drafts: "id,createdAt" });
export { db };
export async function api(path: string, options: RequestInit = {}) {
  const response = await fetch("/api" + path, options);
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const value = await response.json();
      detail =
        typeof value.detail === "string"
          ? value.detail
          : JSON.stringify(value.detail);
    } catch {
      detail = await response.text().catch(() => detail);
    }
    throw new Error(detail);
  }
  return response.json();
}
export async function syncDrafts(key: string) {
  let count = 0;
  for (const draft of await db.drafts.orderBy("createdAt").toArray()) {
    try {
      const headers = {
        "Content-Type": "application/json",
        Authorization: "Bearer " + key,
      };
      await api("/sessions", {
        method: "POST",
        headers,
        body: JSON.stringify(draft.session),
      });
      if (draft.photo && draft.evidenceId) {
        const form = new FormData();
        form.append("file", draft.photo, "evidence.jpg");
        await api("/evidence/" + draft.evidenceId, {
          method: "PUT",
          headers: { Authorization: "Bearer " + key },
          body: form,
        });
      }
      await api(
        "/" + (draft.kind === "inspection" ? "inspections" : "observations"),
        { method: "POST", headers, body: JSON.stringify(draft.body) },
      );
      await db.drafts.delete(draft.id);
      count++;
    } catch (error) {
      await db.drafts.update(draft.id, { error: String(error) });
      throw new Error(`${count} synced. Draft retained: ${String(error)}`);
    }
  }
  return count;
}
