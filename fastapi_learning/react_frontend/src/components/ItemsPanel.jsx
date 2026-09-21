import { useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  PackagePlus,
  Pencil,
  RefreshCw,
  Save,
  Trash2,
  X,
} from "lucide-react";
import { api } from "../api";
import { formatDate } from "../utils";

export default function ItemsPanel({ token, currentUser, onRequireAuth }) {
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [createForm, setCreateForm] = useState({ name: "", price: "" });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", price: "" });

  const canManage = Boolean(token && currentUser);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setItems(await api.listItems(page, 10));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [page]);

  function flashNotice(message) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2500);
  }

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    if (!canManage) {
      onRequireAuth();
      return;
    }
    try {
      const created = await api.createItem(token, {
        name: createForm.name.trim(),
        price: Number(createForm.price),
      });
      setCreateForm({ name: "", price: "" });
      flashNotice(`商品 #${created.id} 已创建`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(item) {
    setEditingId(item.id);
    setEditForm({ name: item.name, price: String(item.price) });
  }

  async function handleSave(id) {
    setError("");
    try {
      await api.updateItem(token, id, {
        name: editForm.name.trim(),
        price: Number(editForm.price),
      });
      setEditingId(null);
      flashNotice(`商品 #${id} 已更新`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm(`确认删除商品 #${id}？`)) return;
    setError("");
    try {
      await api.deleteItem(token, id);
      flashNotice(`商品 #${id} 已删除`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="panel stack">
      <header className="panel-head">
        <div>
          <h3>商品管理</h3>
          <p className="muted">第 {page} 页，每页 10 条</p>
        </div>
        <button className="btn secondary" onClick={load} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} size={16} />
          刷新
        </button>
      </header>

      <form className="create-bar" onSubmit={handleCreate}>
        <input
          value={createForm.name}
          onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="商品名称"
          maxLength={50}
          required
        />
        <input
          type="number"
          min="0"
          step="0.01"
          value={createForm.price}
          onChange={(e) => setCreateForm((f) => ({ ...f, price: e.target.value }))}
          placeholder="价格"
          required
        />
        <button className="btn primary" type="submit">
          {canManage ? <PackagePlus size={16} /> : <PackagePlus size={16} />}
          新建商品
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}
      {notice && <div className="alert ok">{notice}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>价格</th>
              <th>归属用户</th>
              <th>创建时间</th>
              <th className="actions-col">操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isOwner = canManage && item.user_id === currentUser.id;
              const isEditing = editingId === item.id;
              return (
                <tr key={item.id}>
                  <td>#{item.id}</td>
                  <td>
                    {isEditing ? (
                      <input
                        value={editForm.name}
                        onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                        maxLength={50}
                      />
                    ) : (
                      item.name
                    )}
                  </td>
                  <td>
                    {isEditing ? (
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={editForm.price}
                        onChange={(e) => setEditForm((f) => ({ ...f, price: e.target.value }))}
                      />
                    ) : (
                      `¥${Number(item.price).toFixed(2)}`
                    )}
                  </td>
                  <td>#{item.user_id}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td className="actions-col">
                    {isEditing ? (
                      <span className="row-actions">
                        <button className="icon-btn ok" title="保存" onClick={() => handleSave(item.id)}>
                          <Save size={16} />
                        </button>
                        <button className="icon-btn" title="取消" onClick={() => setEditingId(null)}>
                          <X size={16} />
                        </button>
                      </span>
                    ) : (
                      <span className="row-actions">
                        <button
                          className="icon-btn"
                          title="编辑"
                          disabled={!isOwner}
                          onClick={() => startEdit(item)}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="icon-btn danger"
                          title="删除"
                          disabled={!isOwner}
                          onClick={() => handleDelete(item.id)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
            {!items.length && !loading && (
              <tr>
                <td colSpan={6} className="empty-cell">
                  暂无商品
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          <ChevronLeft size={16} />
          上一页
        </button>
        <span className="page-label">{page}</span>
        <button
          className="btn secondary"
          disabled={items.length < 10}
          onClick={() => setPage((p) => p + 1)}
        >
          下一页
          <ChevronRight size={16} />
        </button>
      </div>
      {!canManage && (
        <p className="muted hint">仅登录用户可以新建、编辑和删除商品。</p>
      )}
    </section>
  );
}
