import { useEffect, useState } from "react";
import {
  BookOpen,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Package,
  RefreshCw,
  Store,
  TerminalSquare,
  Users,
} from "lucide-react";
import { api, API_BASE, clearToken, getToken } from "./api";
import AuthPanel from "./components/AuthPanel";
import DemoPanel from "./components/DemoPanel";
import ItemsPanel from "./components/ItemsPanel";
import Overview from "./components/Overview";
import UsersPanel from "./components/UsersPanel";

const NAV_ITEMS = [
  { key: "overview", label: "概览", icon: LayoutDashboard },
  { key: "items", label: "商品", icon: Package },
  { key: "users", label: "用户", icon: Users },
  { key: "demo", label: "接口体验", icon: TerminalSquare },
];

const VIEW_TITLES = {
  overview: "概览",
  items: "商品管理",
  users: "用户列表",
  demo: "接口体验",
  auth: "登录 / 注册",
};

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("overview");
  const [online, setOnline] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }
    api
      .me(token)
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    let alive = true;
    async function check() {
      try {
        await api.health();
        if (alive) setOnline(true);
      } catch {
        if (alive) setOnline(false);
      }
    }
    check();
    const timer = window.setInterval(check, 20000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  function handleAuthed(nextUser) {
    setUser(nextUser);
    setView("items");
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setView("overview");
  }

  const navItems = user
    ? NAV_ITEMS
    : [...NAV_ITEMS, { key: "auth", label: "登录 / 注册", icon: KeyRound }];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Package size={20} />
          </span>
          <div>
            <strong>FastAPI 实训台</strong>
            <span>React + FastAPI</span>
          </div>
        </div>

        <nav className="nav">
          {navItems.map((item) => (
            <button
              key={item.key}
              className={view === item.key ? "active" : ""}
              onClick={() => setView(item.key)}
            >
              <item.icon size={17} />
              {item.label}
            </button>
          ))}
          <a
            className="nav-link"
            href={`${API_BASE}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            <BookOpen size={17} />
            API 文档
          </a>
        </nav>

        <div className="sidebar-foot">
          <span className={`dot ${online ? "ok" : "bad"}`} />
          {online ? "后端已连接" : "后端未连接"}
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{VIEW_TITLES[view]}</h1>
            <p className="muted">{API_BASE}</p>
          </div>
          <div className="topbar-actions">
            <a className="btn secondary" href="/store.html">
              <Store size={16} />
              用户端
            </a>
            {!authLoading && user && (
              <div className="user-chip">
                <span className="avatar">{user.username.slice(0, 1).toUpperCase()}</span>
                <span>{user.username}</span>
                <button className="icon-btn" title="退出登录" onClick={handleLogout}>
                  <LogOut size={16} />
                </button>
              </div>
            )}
            {!authLoading && !user && (
              <button className="btn primary" onClick={() => setView("auth")}>
                <KeyRound size={16} />
                登录 / 注册
              </button>
            )}
            {authLoading && (
              <span className="muted">
                <RefreshCw className="spin" size={16} />
                检查登录状态
              </span>
            )}
          </div>
        </header>

        <div className="content">
          {authLoading ? (
            <div className="loading-block">
              <RefreshCw className="spin" size={22} />
              加载中
            </div>
          ) : (
            <>
              {view === "overview" && (
                <Overview user={user} onGoItems={() => setView("items")} />
              )}
              {view === "items" && (
                <ItemsPanel
                  token={getToken()}
                  currentUser={user}
                  onRequireAuth={() => setView("auth")}
                />
              )}
              {view === "users" && <UsersPanel />}
              {view === "demo" && <DemoPanel />}
              {view === "auth" && <AuthPanel onAuthed={handleAuthed} />}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
