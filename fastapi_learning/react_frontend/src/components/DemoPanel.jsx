import { useState } from "react";
import { Braces, FileUp, Loader2, Mail, Play, Send } from "lucide-react";
import { api, API_BASE } from "../api";

export default function DemoPanel() {
  const [response, setResponse] = useState(null);
  const [demoLoading, setDemoLoading] = useState("");
  const [email, setEmail] = useState("");
  const [sendResult, setSendResult] = useState("");
  const [username, setUsername] = useState("");
  const [file, setFile] = useState(null);
  const [uploadResult, setUploadResult] = useState("");
  const [error, setError] = useState("");

  async function runDemo(key, path, label) {
    setError("");
    setDemoLoading(key);
    try {
      const res = await fetch(`${API_BASE}${path}`);
      const text = await res.text();
      setResponse({ label, status: res.status, text });
    } catch (err) {
      setError(err.message);
    } finally {
      setDemoLoading("");
    }
  }

  async function handleSend(event) {
    event.preventDefault();
    setError("");
    setSendResult("");
    try {
      const result = await api.sendEmail(email.trim());
      setSendResult(result.message);
      setEmail("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUpload(event) {
    event.preventDefault();
    setError("");
    setUploadResult("");
    if (!file) return;
    try {
      const result = await api.upload(username.trim() || "匿名用户", file);
      setUploadResult(`${result.filename}，${result.size} 字节`);
      setFile(null);
      event.target.reset();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="demo-grid">
      <section className="panel stack">
        <header className="panel-head">
          <div>
            <h3>响应演示</h3>
            <p className="muted">直接调用 files 路由的示例接口</p>
          </div>
        </header>
        <div className="demo-actions">
          <button className="btn secondary" onClick={() => runDemo("json", "/json", "GET /json")} disabled={Boolean(demoLoading)}>
            {demoLoading === "json" ? <Loader2 className="spin" size={16} /> : <Braces size={16} />}
            JSON
          </button>
          <button className="btn secondary" onClick={() => runDemo("html", "/html", "GET /html")} disabled={Boolean(demoLoading)}>
            {demoLoading === "html" ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
            HTML
          </button>
          <button className="btn secondary" onClick={() => runDemo("file", "/file", "GET /file")} disabled={Boolean(demoLoading)}>
            {demoLoading === "file" ? <Loader2 className="spin" size={16} /> : <FileUp size={16} />}
            文件
          </button>
          <button className="btn secondary" onClick={() => runDemo("redirect", "/redirect", "GET /redirect")} disabled={Boolean(demoLoading)}>
            {demoLoading === "redirect" ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
            重定向
          </button>
        </div>
        <div className="response-box">
          {response ? (
            <>
              <div className="response-head">
                <strong>{response.label}</strong>
                <span className={`status-pill ${response.status < 400 ? "ok" : "bad"}`}>{response.status}</span>
              </div>
              <pre>{response.text}</pre>
            </>
          ) : (
            <p className="muted">选择一个接口查看响应</p>
          )}
        </div>
      </section>

      <section className="panel stack">
        <header className="panel-head">
          <h3>后台任务</h3>
        </header>
        <form className="form-grid" onSubmit={handleSend}>
          <label className="field">
            <span>收件邮箱</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              required
            />
          </label>
          <button className="btn primary" type="submit">
            <Send size={16} />
            发送通知
          </button>
        </form>
        {sendResult && <div className="alert ok">{sendResult}</div>}
      </section>

      <section className="panel stack">
        <header className="panel-head">
          <h3>文件上传</h3>
        </header>
        <form className="form-grid" onSubmit={handleUpload}>
          <label className="field">
            <span>用户名</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="匿名用户"
            />
          </label>
          <label className="field">
            <span>文件</span>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
          </label>
          <button className="btn primary" type="submit" disabled={!file}>
            <Mail size={16} />
            上传
          </button>
        </form>
        {uploadResult && <div className="alert ok">{uploadResult}</div>}
      </section>

      {error && <div className="alert error">{error}</div>}
    </div>
  );
}
