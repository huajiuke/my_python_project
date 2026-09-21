import { useState } from "react";
import { KeyRound, Loader2, LogIn, UserPlus } from "lucide-react";
import { api, API_BASE, setToken } from "../api";

export default function AuthPanel({ onAuthed }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    username: "",
    password: "",
    age: "18",
    email: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const username = form.username.trim();
      if (mode === "register") {
        await api.register({
          username,
          password: form.password,
          age: Number(form.age || 18),
          email: form.email.trim() || null,
        });
      }
      const { access_token } = await api.login(username, form.password);
      setToken(access_token);
      const user = await api.me(access_token);
      onAuthed(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-layout">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="auth-heading">
          <span className="auth-icon">
            <KeyRound size={20} />
          </span>
          <div>
            <h2>账户</h2>
            <p>登录后可以创建和管理商品</p>
          </div>
        </div>

        <div className="segmented" role="tablist" aria-label="认证方式">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            <LogIn size={16} />
            登录
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            <UserPlus size={16} />
            注册
          </button>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>用户名</span>
            <input
              value={form.username}
              onChange={(e) => update("username", e.target.value)}
              minLength={3}
              maxLength={20}
              required
              autoComplete="username"
              placeholder="3-20 个字符"
            />
          </label>
          <label className="field">
            <span>密码</span>
            <input
              type="password"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              minLength={6}
              maxLength={72}
              required
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              placeholder="至少 6 位"
            />
          </label>
          {mode === "register" && (
            <>
              <label className="field">
                <span>年龄</span>
                <input
                  type="number"
                  min={0}
                  max={150}
                  value={form.age}
                  onChange={(e) => update("age", e.target.value)}
                  placeholder="18"
                />
              </label>
              <label className="field">
                <span>邮箱</span>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                  placeholder="可选"
                />
              </label>
            </>
          )}
        </div>

        {error && <div className="alert error">{error}</div>}

        <button className="btn primary block" type="submit" disabled={loading}>
          {loading ? <Loader2 className="spin" size={16} /> : mode === "login" ? <LogIn size={16} /> : <UserPlus size={16} />}
          {loading ? "处理中..." : mode === "login" ? "登录" : "注册并登录"}
        </button>
      </form>

      <aside className="auth-meta">
        <div className="meta-row">
          <span>API 地址</span>
          <code>{API_BASE}</code>
        </div>
        <div className="meta-row">
          <span>接口文档</span>
          <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
            打开 Swagger UI
          </a>
        </div>
        <div className="meta-note">
          商品列表、用户列表和演示接口无需登录即可访问。
        </div>
      </aside>
    </section>
  );
}
