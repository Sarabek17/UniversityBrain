"use client";

// User / role management (S13). The role select writes straight through
// `PATCH /admin/users/{id}` — the backend refuses an admin demoting themselves,
// so the UI never has to guess who may do what.

import { useCallback, useEffect, useState } from "react";
import {
  adminApi,
  errorDetail,
  type AdminGroup,
  type AdminUser,
  type UserRole,
} from "@/lib/api";
import { formatDate } from "@/lib/labels";
import uz from "@/i18n/uz.json";

const ROLES: UserRole[] = ["student", "teacher", "tutor", "staff", "admin"];
const LANGUAGES = ["uz", "ru", "en"] as const;

const EMPTY_FORM = {
  username: "",
  full_name: "",
  role: "student" as UserRole,
  password: "",
  group_id: "",
  faculty_id: "",
  language: "uz",
};

export default function AdminUsersPanel({
  onChanged,
}: {
  onChanged: () => void;
}) {
  const [rows, setRows] = useState<AdminUser[] | null>(null);
  const [groups, setGroups] = useState<AdminGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [roleFilter, setRoleFilter] = useState<UserRole | "">("");
  const [search, setSearch] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [form, setForm] = useState(EMPTY_FORM);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      adminApi
        .users(roleFilter || null, search || null)
        .then((data) => {
          setRows(data);
          setError(null);
        })
        .catch(() => setError(uz.admin.loadError)),
    [roleFilter, search],
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    adminApi
      .groups()
      .then((data) => setGroups(data))
      .catch(() => setGroups([]));
  }, []);

  function changeRole(user: AdminUser, role: UserRole) {
    setSavingId(user.id);
    setNotice(null);
    setError(null);
    adminApi
      .updateUser(user.id, { role })
      .then(() => {
        setNotice(`${user.full_name}: ${uz.admin.roleChanged}`);
        onChanged();
        return load();
      })
      .catch((e: unknown) =>
        setError(errorDetail(e) ?? uz.admin.roleChangeError),
      )
      .finally(() => setSavingId(null));
  }

  function submitCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    setNotice(null);
    adminApi
      .createUser({
        username: form.username.trim(),
        full_name: form.full_name.trim(),
        role: form.role,
        password: form.password,
        group_id: form.group_id ? Number(form.group_id) : null,
        faculty_id: form.faculty_id ? Number(form.faculty_id) : null,
        language: form.language,
      })
      .then((created) => {
        setForm(EMPTY_FORM);
        setNotice(`${created.full_name}: ${uz.admin.createDone}`);
        onChanged();
        return load();
      })
      .catch((e: unknown) =>
        setCreateError(errorDetail(e) ?? uz.admin.createError),
      )
      .finally(() => setCreating(false));
  }

  const faculties = [
    ...new Set(
      groups
        .map((group) => group.faculty_id)
        .filter((id): id is number => id !== null),
    ),
  ].sort((a, b) => a - b);

  return (
    <section className="rounded-lg border border-line p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">
          {uz.admin.usersTitle}
          {rows && (
            <span className="ml-2 text-xs font-normal text-ink-faint">
              {rows.length} {uz.admin.usersCount}
            </span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={uz.admin.usersSearch}
            className="w-52 rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
          />
          <select
            value={roleFilter}
            onChange={(event) =>
              setRoleFilter(event.target.value as UserRole | "")
            }
            className="rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
          >
            <option value="">{uz.admin.usersAll}</option>
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {uz.roles[role]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {notice && (
        <p className="mt-2 text-xs text-ok">
          {notice}
        </p>
      )}
      {error && <p className="mt-2 text-xs text-bad">{error}</p>}

      <div className="mt-3 max-h-80 overflow-x-auto overflow-y-auto rounded-md border border-line">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-raised text-ink-faint">
            <tr>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colName}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colUsername}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colScope}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colCreated}</th>
              <th className="px-2 py-1.5 font-medium">{uz.admin.colRole}</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr
                key={row.id}
                className="border-t border-line"
              >
                <td className="px-2 py-1.5">{row.full_name}</td>
                <td className="px-2 py-1.5 text-ink-faint">
                  {row.username}
                </td>
                <td className="px-2 py-1.5 text-ink-faint">
                  {row.group_name ??
                    (row.faculty_id
                      ? `${uz.admin.facultyShort} ${row.faculty_id}`
                      : "—")}
                </td>
                <td className="px-2 py-1.5 text-ink-faint">
                  {formatDate(row.created_at)}
                </td>
                <td className="px-2 py-1.5">
                  <select
                    value={row.role}
                    disabled={savingId === row.id}
                    onChange={(event) =>
                      changeRole(row, event.target.value as UserRole)
                    }
                    className="rounded-md border border-line-strong bg-transparent px-1.5 py-0.5 text-xs"
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>
                        {uz.roles[role]}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {rows && rows.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-2 py-3 text-center text-ink-faint"
                >
                  {uz.admin.usersEmpty}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {!rows && !error && (
          <p className="px-2 py-3 text-xs text-ink-faint">{uz.common.loading}</p>
        )}
      </div>

      <form onSubmit={submitCreate} className="mt-4 border-t pt-3">
        <h3 className="text-xs font-semibold">{uz.admin.createTitle}</h3>
        <p className="mt-0.5 text-[11px] text-ink-faint">
          {uz.admin.createHint}
        </p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <label className="text-[11px] text-ink-soft">
            {uz.admin.createUsername}
            <input
              required
              value={form.username}
              onChange={(event) =>
                setForm({ ...form, username: event.target.value })
              }
              className="mt-0.5 w-full rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
            />
          </label>
          <label className="text-[11px] text-ink-soft">
            {uz.admin.createFullName}
            <input
              required
              value={form.full_name}
              onChange={(event) =>
                setForm({ ...form, full_name: event.target.value })
              }
              className="mt-0.5 w-full rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
            />
          </label>
          <label className="text-[11px] text-ink-soft">
            {uz.admin.createRole}
            <select
              value={form.role}
              onChange={(event) =>
                setForm({ ...form, role: event.target.value as UserRole })
              }
              className="mt-0.5 w-full rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
            >
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {uz.roles[role]}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[11px] text-ink-soft">
            {uz.admin.createPassword}
            <input
              required
              type="password"
              value={form.password}
              onChange={(event) =>
                setForm({ ...form, password: event.target.value })
              }
              className="mt-0.5 w-full rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
            />
          </label>
          <label className="text-[11px] text-ink-soft">
            {uz.admin.createGroup}
            <select
              value={form.group_id}
              onChange={(event) =>
                setForm({ ...form, group_id: event.target.value })
              }
              className="mt-0.5 w-full rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
            >
              <option value="">{uz.admin.createGroupNone}</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-[11px] text-ink-soft">
              {uz.admin.createFaculty}
              <select
                value={form.faculty_id}
                onChange={(event) =>
                  setForm({ ...form, faculty_id: event.target.value })
                }
                className="mt-0.5 w-full rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
              >
                <option value="">—</option>
                {faculties.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-[11px] text-ink-soft">
              {uz.admin.createLanguage}
              <select
                value={form.language}
                onChange={(event) =>
                  setForm({ ...form, language: event.target.value })
                }
                className="mt-0.5 w-full rounded-md border border-line-strong bg-transparent px-2 py-1 text-xs"
              >
                {LANGUAGES.map((code) => (
                  <option key={code} value={code}>
                    {uz.documents.languages[code]}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        {createError && (
          <p className="mt-2 text-xs text-bad">{createError}</p>
        )}
        <button
          type="submit"
          disabled={creating}
          className="mt-2 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-fg hover:bg-accent-hover disabled:bg-raised disabled:text-ink-faint"
        >
          {creating ? uz.admin.createLoading : uz.admin.createSubmit}
        </button>
      </form>
    </section>
  );
}
