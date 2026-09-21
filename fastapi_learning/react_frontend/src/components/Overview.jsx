import { useEffect, useState } from "react";
import { Activity, BookOpen, Package, RefreshCw, Users } from "lucide-react";
import { api, API_BASE } from "../api";
import { formatDate } from "../utils";

export default function Overview({ user, onGoItems }) {
  const [health, setHealth] = useState(null);
  const [users, setUsers] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [healthData, usersData, itemsData] = await Promise.all([
        api.health(),
        api.listUsers(1, 5),
        api.listItems(1, 5),
      ]);
      setHealth(healthData);
      setUsers(usersData);
      setItems(itemsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const statCards = [
    {
      label: "API 状态",
      value: health ? "在线" : "离线",
      tone: health ? "ok" : "bad",
      icon: Activity,
    },
    { label: "用户数", value: users.length >= 5 ? `${users.length}+` : users.length, tone: "blue", icon: Users },
    { label: "商品数", value: items.length >= 5 ? `${items.length}+` : items.length, tone: "teal", icon: Package },
    { label: "接口文档", value: "Swagger UI", tone: "amber", icon: BookOpen, href: `${API_BASE}/docs` },
  ];

  return (
    <div className="overview">
      <div className="stat-grid">
        {statCards.map((card) => (
          <article key={card.label} className={`stat-card ${card.tone}`}>
            <span className="stat-icon">
              <card.icon size={18} />
            </span>
            <div>
              <p>{card.label}</p>
              {card.href ? (
                <a href={card.href} target="_blank" rel="noreferrer">
                  {card.value}
                </a>
              ) : (
                <strong>{card.value}</strong>
              )}
            </div>
          </article>
        ))}
      </div>

      <div className="overview-toolbar">
        <div>
          <h3>最近数据</h3>
          {user && <p className="muted">当前登录：{user.username}</p>}
        </div>
        <button className="btn secondary" onClick={load} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} size={16} />
          刷新
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="recent-grid">
        <section className="panel">
          <header className="panel-head">
            <h4>最新商品</h4>
            <button className="link-btn" onClick={onGoItems}>
              查看全部
            </button>
          </header>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>名称</th>
                  <th>价格</th>
                  <th>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>¥{Number(item.price).toFixed(2)}</td>
                    <td>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
                {!items.length && (
                  <tr>
                    <td colSpan={3} className="empty-cell">
                      暂无商品
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <header className="panel-head">
            <h4>最新用户</h4>
            <span className="muted">前 5 条</span>
          </header>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>用户名</th>
                  <th>年龄</th>
                  <th>注册时间</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>{u.age}</td>
                    <td>{formatDate(u.created_at)}</td>
                  </tr>
                ))}
                {!users.length && (
                  <tr>
                    <td colSpan={3} className="empty-cell">
                      暂无用户
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
