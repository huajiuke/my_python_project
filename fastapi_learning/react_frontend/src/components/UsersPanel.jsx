import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, RefreshCw } from "lucide-react";
import { api } from "../api";
import { formatDate } from "../utils";

export default function UsersPanel() {
  const [page, setPage] = useState(1);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setUsers(await api.listUsers(page, 10));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [page]);

  return (
    <section className="panel stack">
      <header className="panel-head">
        <div>
          <h3>用户列表</h3>
          <p className="muted">第 {page} 页，每页 10 条</p>
        </div>
        <button className="btn secondary" onClick={load} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} size={16} />
          刷新
        </button>
      </header>

      {error && <div className="alert error">{error}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>年龄</th>
              <th>邮箱</th>
              <th>注册时间</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>#{u.id}</td>
                <td>{u.username}</td>
                <td>{u.age}</td>
                <td>{u.email || "-"}</td>
                <td>{formatDate(u.created_at)}</td>
              </tr>
            ))}
            {!users.length && !loading && (
              <tr>
                <td colSpan={5} className="empty-cell">
                  暂无用户
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
          disabled={users.length < 10}
          onClick={() => setPage((p) => p + 1)}
        >
          下一页
          <ChevronRight size={16} />
        </button>
      </div>
    </section>
  );
}
