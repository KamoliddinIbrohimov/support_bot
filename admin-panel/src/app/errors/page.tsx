"use client";
import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import { getErrors, createError, updateError, deleteError } from "@/lib/api";
import type { ErrorEntry } from "@/lib/types";
import { Plus, Pencil, Trash2, Search, X } from "lucide-react";

// ── Shared styles ─────────────────────────────────────────────────────────────

const inputCls =
  "w-full bg-card2 border border-rim rounded-lg px-3 py-2 text-sm text-ink placeholder:text-dim " +
  "focus:outline-none focus:ring-1 focus:ring-ac focus:border-ac transition-colors";

// ── Form state ────────────────────────────────────────────────────────────────

interface FormState {
  title_ru: string; title_uz: string;
  keywords_ru: string; keywords_uz: string;
  solution_ru: string; solution_uz: string;
  solution_video_file_id: string; solution_image_file_id: string;
}

const emptyForm = (): FormState => ({
  title_ru: "", title_uz: "", keywords_ru: "", keywords_uz: "",
  solution_ru: "", solution_uz: "", solution_video_file_id: "", solution_image_file_id: "",
});

function entryToForm(e: ErrorEntry): FormState {
  return {
    title_ru: e.title_ru ?? "", title_uz: e.title_uz ?? "",
    keywords_ru: (e.keywords_ru ?? []).join(", "),
    keywords_uz: (e.keywords_uz ?? []).join(", "),
    solution_ru: e.solution_ru ?? "", solution_uz: e.solution_uz ?? "",
    solution_video_file_id: e.solution_video_file_id ?? "",
    solution_image_file_id: e.solution_image_file_id ?? "",
  };
}

function parseKeywords(s: string): string[] {
  return s.split(",").map((k) => k.trim()).filter(Boolean);
}

// ── Field wrapper ─────────────────────────────────────────────────────────────

function Field({ label, hint, required, children }: {
  label: string; hint?: string; required?: boolean; children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-dim">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
        {hint && <span className="text-dim/60 font-normal ml-1">({hint})</span>}
      </label>
      {children}
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function ErrorModal({ editing, onClose, onSaved }: {
  editing: ErrorEntry | null; onClose: () => void; onSaved: () => void;
}) {
  const [form, setForm] = useState<FormState>(editing ? entryToForm(editing) : emptyForm());
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const set = (f: keyof FormState) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((prev) => ({ ...prev, [f]: e.target.value }));

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setSaving(true); setErr("");
    const payload = {
      title_ru: form.title_ru, title_uz: form.title_uz,
      keywords_ru: parseKeywords(form.keywords_ru),
      keywords_uz: parseKeywords(form.keywords_uz),
      solution_ru: form.solution_ru, solution_uz: form.solution_uz,
      solution_video_file_id: form.solution_video_file_id || null,
      solution_image_file_id: form.solution_image_file_id || null,
    };
    try {
      editing ? await updateError(editing.id, payload) : await createError(payload);
      onSaved();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(detail || "Ошибка при сохранении");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-rim rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-rim">
          <h2 className="text-base font-semibold text-ink">
            {editing ? "Xatoni tahrirlash" : "Yangi xato qo'shish"}
          </h2>
          <button onClick={onClose} className="text-dim hover:text-ink transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Sarlavha (RU)" required>
              <input className={inputCls} value={form.title_ru} onChange={set("title_ru")} required />
            </Field>
            <Field label="Sarlavha (UZ)" required>
              <input className={inputCls} value={form.title_uz} onChange={set("title_uz")} required />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Kalit so'zlar (RU)" hint="vergul bilan">
              <input className={inputCls} value={form.keywords_ru} onChange={set("keywords_ru")} />
            </Field>
            <Field label="Kalit so'zlar (UZ)" hint="vergul bilan">
              <input className={inputCls} value={form.keywords_uz} onChange={set("keywords_uz")} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Yechim (RU)" required>
              <textarea className={`${inputCls} resize-none`} rows={4} value={form.solution_ru} onChange={set("solution_ru")} required />
            </Field>
            <Field label="Yechim (UZ)" required>
              <textarea className={`${inputCls} resize-none`} rows={4} value={form.solution_uz} onChange={set("solution_uz")} required />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Video File ID" hint="ixtiyoriy">
              <input className={inputCls} value={form.solution_video_file_id} onChange={set("solution_video_file_id")} />
            </Field>
            <Field label="Rasm File ID" hint="ixtiyoriy">
              <input className={inputCls} value={form.solution_image_file_id} onChange={set("solution_image_file_id")} />
            </Field>
          </div>

          {err && (
            <p className="text-sm text-red-400 bg-red-900/20 border border-red-800/30 rounded-lg px-4 py-2">{err}</p>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-rim text-dim hover:bg-card2 hover:text-ink transition-colors">
              Bekor
            </button>
            <button type="submit" disabled={saving}
              className="px-4 py-2 text-sm rounded-lg bg-ac hover:bg-ac-h text-white disabled:opacity-50 transition-colors">
              {saving ? "Saqlanmoqda…" : "Saqlash"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Delete confirm ────────────────────────────────────────────────────────────

function DeleteConfirm({ entry, onClose, onDeleted }: {
  entry: ErrorEntry; onClose: () => void; onDeleted: () => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const handle = async () => { setDeleting(true); await deleteError(entry.id); onDeleted(); };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-rim rounded-2xl w-full max-w-sm p-6 space-y-4">
        <h2 className="text-base font-semibold text-ink">Xatoni o&apos;chirish</h2>
        <p className="text-sm text-dim">
          &ldquo;{entry.title_ru || entry.title_uz}&rdquo; o&apos;chirilsinmi?
        </p>
        <div className="flex justify-end gap-3">
          <button onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-rim text-dim hover:bg-card2 hover:text-ink transition-colors">
            Bekor
          </button>
          <button onClick={handle} disabled={deleting}
            className="px-4 py-2 text-sm rounded-lg bg-red-900/30 border border-red-800/30 text-red-400 hover:bg-red-900/50 disabled:opacity-50 transition-colors">
            {deleting ? "O'chirilmoqda…" : "O'chirish"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ErrorsPage() {
  const [items, setItems] = useState<ErrorEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [modalEntry, setModalEntry] = useState<ErrorEntry | "new" | null>(null);
  const [deleteEntry, setDeleteEntry] = useState<ErrorEntry | null>(null);
  const PAGE_SIZE = 20;

  const load = useCallback(() => {
    setLoading(true);
    getErrors(page, PAGE_SIZE, search)
      .then((r) => { setItems(r.data.items); setTotal(r.data.total); })
      .finally(() => setLoading(false));
  }, [page, search]);

  useEffect(() => { load(); }, [load]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault(); setPage(1); setSearch(searchInput);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-page">
        <Sidebar />
        <main className="flex-1 p-8 space-y-6 overflow-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-ink">Xatolar bazasi</h1>
              <p className="text-sm text-dim mt-0.5">Jami: {total} ta yozuv</p>
            </div>
            <button onClick={() => setModalEntry("new")}
              className="flex items-center gap-2 px-4 py-2 bg-ac hover:bg-ac-h text-white text-sm rounded-lg transition-colors">
              <Plus size={15} />
              Yangi xato
            </button>
          </div>

          <form onSubmit={handleSearch} className="flex gap-2 max-w-md">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dim" />
              <input
                className="w-full bg-card border border-rim rounded-lg pl-9 pr-3 py-2 text-sm text-ink placeholder:text-dim focus:outline-none focus:ring-1 focus:ring-ac focus:border-ac transition-colors"
                placeholder="Qidirish…"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>
            <button type="submit"
              className="px-4 py-2 text-sm bg-card border border-rim text-dim hover:text-ink hover:bg-card2 rounded-lg transition-colors">
              Qidirish
            </button>
            {search && (
              <button type="button" onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
                className="px-3 py-2 text-dim hover:text-ink transition-colors">
                <X size={14} />
              </button>
            )}
          </form>

          <div className="bg-card border border-rim rounded-xl overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-sm text-dim">Yuklanmoqda…</div>
            ) : items.length === 0 ? (
              <div className="p-8 text-center text-sm text-dim">Xatolar topilmadi</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b border-rim">
                  <tr className="text-left">
                    <th className="px-4 py-3 text-xs text-dim font-medium">ID</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Sarlavha (RU)</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Sarlavha (UZ)</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Kalit so&apos;zlar</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium">Media</th>
                    <th className="px-4 py-3 text-xs text-dim font-medium text-right">Amallar</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((e) => (
                    <tr key={e.id} className="border-b border-rim/40 last:border-0 hover:bg-card2 transition-colors">
                      <td className="px-4 py-3 text-dim text-xs">{e.id}</td>
                      <td className="px-4 py-3 text-ink font-medium max-w-[160px] truncate">{e.title_ru ?? "—"}</td>
                      <td className="px-4 py-3 text-dim max-w-[160px] truncate">{e.title_uz ?? "—"}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1 max-w-[180px]">
                          {(e.keywords_ru ?? []).slice(0, 3).map((kw, i) => (
                            <span key={i} className="bg-ac/10 text-ac text-xs px-2 py-0.5 rounded-full">{kw}</span>
                          ))}
                          {(e.keywords_ru ?? []).length > 3 && (
                            <span className="text-dim text-xs">+{(e.keywords_ru ?? []).length - 3}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-dim text-xs">
                        {e.solution_video_file_id ? "🎥 " : ""}
                        {e.solution_image_file_id ? "🖼" : ""}
                        {!e.solution_video_file_id && !e.solution_image_file_id ? "—" : ""}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => setModalEntry(e)}
                            className="p-1.5 text-dim hover:text-ac hover:bg-ac/10 rounded-lg transition-colors">
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => setDeleteEntry(e)}
                            className="p-1.5 text-dim hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-dim">{page} / {totalPages} sahifa</span>
              <div className="flex gap-2">
                <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1.5 border border-rim text-dim rounded-lg disabled:opacity-30 hover:bg-card2 hover:text-ink transition-colors">
                  ← Oldingi
                </button>
                <button disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1.5 border border-rim text-dim rounded-lg disabled:opacity-30 hover:bg-card2 hover:text-ink transition-colors">
                  Keyingi →
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {modalEntry !== null && (
        <ErrorModal
          editing={modalEntry === "new" ? null : modalEntry}
          onClose={() => setModalEntry(null)}
          onSaved={() => { setModalEntry(null); load(); }}
        />
      )}
      {deleteEntry && (
        <DeleteConfirm
          entry={deleteEntry}
          onClose={() => setDeleteEntry(null)}
          onDeleted={() => { setDeleteEntry(null); load(); }}
        />
      )}
    </AuthGuard>
  );
}
