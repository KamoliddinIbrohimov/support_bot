"use client";
import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AuthGuard } from "@/components/AuthGuard";
import { getErrors, createError, updateError, deleteError } from "@/lib/api";
import type { ErrorEntry } from "@/lib/types";
import { Plus, Pencil, Trash2, Search, X } from "lucide-react";

// ── Modal form state ──────────────────────────────────────────────────────────

interface FormState {
  title_ru: string;
  title_uz: string;
  keywords_ru: string;
  keywords_uz: string;
  solution_ru: string;
  solution_uz: string;
  solution_video_file_id: string;
  solution_image_file_id: string;
}

const emptyForm = (): FormState => ({
  title_ru: "",
  title_uz: "",
  keywords_ru: "",
  keywords_uz: "",
  solution_ru: "",
  solution_uz: "",
  solution_video_file_id: "",
  solution_image_file_id: "",
});

function entryToForm(e: ErrorEntry): FormState {
  return {
    title_ru: e.title_ru ?? "",
    title_uz: e.title_uz ?? "",
    keywords_ru: (e.keywords_ru ?? []).join(", "),
    keywords_uz: (e.keywords_uz ?? []).join(", "),
    solution_ru: e.solution_ru ?? "",
    solution_uz: e.solution_uz ?? "",
    solution_video_file_id: e.solution_video_file_id ?? "",
    solution_image_file_id: e.solution_image_file_id ?? "",
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function parseKeywords(s: string): string[] {
  return s
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function ErrorModal({
  editing,
  onClose,
  onSaved,
}: {
  editing: ErrorEntry | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<FormState>(
    editing ? entryToForm(editing) : emptyForm()
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const set = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      title_ru: form.title_ru,
      title_uz: form.title_uz,
      keywords_ru: parseKeywords(form.keywords_ru),
      keywords_uz: parseKeywords(form.keywords_uz),
      solution_ru: form.solution_ru,
      solution_uz: form.solution_uz,
      solution_video_file_id: form.solution_video_file_id || null,
      solution_image_file_id: form.solution_image_file_id || null,
    };
    try {
      if (editing) {
        await updateError(editing.id, payload);
      } else {
        await createError(payload);
      }
      onSaved();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Xato saqlashda muammo");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">
            {editing ? "Xatoni tahrirlash" : "Yangi xato qo'shish"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Sarlavha (RU)" required>
              <input className={inputCls} value={form.title_ru} onChange={set("title_ru")} required />
            </Field>
            <Field label="Sarlavha (UZ)" required>
              <input className={inputCls} value={form.title_uz} onChange={set("title_uz")} required />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Kalit so'zlar (RU)" hint="vergul bilan ajrating">
              <input className={inputCls} value={form.keywords_ru} onChange={set("keywords_ru")} />
            </Field>
            <Field label="Kalit so'zlar (UZ)" hint="vergul bilan ajrating">
              <input className={inputCls} value={form.keywords_uz} onChange={set("keywords_uz")} />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Yechim (RU)" required>
              <textarea
                className={`${inputCls} resize-none`}
                rows={4}
                value={form.solution_ru}
                onChange={set("solution_ru")}
                required
              />
            </Field>
            <Field label="Yechim (UZ)" required>
              <textarea
                className={`${inputCls} resize-none`}
                rows={4}
                value={form.solution_uz}
                onChange={set("solution_uz")}
                required
              />
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

          {error && (
            <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-lg">{error}</p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Bekor
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saqlanmoqda…" : "Saqlash"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const inputCls =
  "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-gray-600">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
        {hint && <span className="text-gray-400 font-normal ml-1">({hint})</span>}
      </label>
      {children}
    </div>
  );
}

// ── Delete confirm ────────────────────────────────────────────────────────────

function DeleteConfirm({
  entry,
  onClose,
  onDeleted,
}: {
  entry: ErrorEntry;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    await deleteError(entry.id);
    onDeleted();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="text-base font-semibold">Xatoni o&apos;chirish</h2>
        <p className="text-sm text-gray-600">
          &ldquo;{entry.title_ru || entry.title_uz}&rdquo; o&apos;chirilsinmi? Bu amalni qaytarib bo&apos;lmaydi.
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50"
          >
            Bekor
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          >
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
      .then((r) => {
        setItems(r.data.items);
        setTotal(r.data.total);
      })
      .finally(() => setLoading(false));
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 space-y-6 overflow-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Xatolar bazasi</h1>
              <p className="text-sm text-gray-500 mt-1">Jami: {total} ta yozuv</p>
            </div>
            <button
              onClick={() => setModalEntry("new")}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus size={16} />
              Yangi xato
            </button>
          </div>

          <form onSubmit={handleSearch} className="flex gap-2 max-w-md">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="w-full border border-gray-200 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Qidirish…"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 text-sm bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Qidirish
            </button>
            {search && (
              <button
                type="button"
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
                className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                <X size={15} />
              </button>
            )}
          </form>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-sm text-gray-400">Yuklanmoqda…</div>
            ) : items.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">Xatolar topilmadi</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3">ID</th>
                    <th className="px-4 py-3">Sarlavha (RU)</th>
                    <th className="px-4 py-3">Sarlavha (UZ)</th>
                    <th className="px-4 py-3">Kalit so&apos;zlar</th>
                    <th className="px-4 py-3">Media</th>
                    <th className="px-4 py-3 text-right">Amallar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {items.map((e) => (
                    <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-gray-400 text-xs">{e.id}</td>
                      <td className="px-4 py-3 font-medium max-w-[180px] truncate">
                        {e.title_ru ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">
                        {e.title_uz ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1 max-w-[200px]">
                          {(e.keywords_ru ?? []).slice(0, 3).map((kw, i) => (
                            <span
                              key={i}
                              className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full"
                            >
                              {kw}
                            </span>
                          ))}
                          {(e.keywords_ru ?? []).length > 3 && (
                            <span className="text-gray-400 text-xs">
                              +{(e.keywords_ru ?? []).length - 3}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {e.solution_video_file_id ? "🎥" : ""}
                        {e.solution_image_file_id ? " 🖼" : ""}
                        {!e.solution_video_file_id && !e.solution_image_file_id ? "—" : ""}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setModalEntry(e)}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => setDeleteEntry(e)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
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
              <span className="text-gray-500">
                {page} / {totalPages} sahifa
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
                >
                  ← Oldingi
                </button>
                <button
                  disabled={page === totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
                >
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
