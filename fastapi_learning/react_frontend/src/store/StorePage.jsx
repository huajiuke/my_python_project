import { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Minus,
  PackageOpen,
  Plus,
  Search,
  ShoppingCart,
  Store,
  Trash2,
  X,
} from "lucide-react";
import { api, API_BASE } from "../api";
import { formatDate } from "../utils";
import useCart from "./useCart";

const PRODUCT_IMAGES = {
  python: "/products/python.png",
  fastapi: "/products/fastapi.png",
  sqlalchemy: "/products/sqlalchemy.png",
  jwt: "/products/jwt.png",
  engineering: "/products/engineering.png",
  default: "/products/default.png",
};

const IMAGE_KEYS = ["python", "fastapi", "sqlalchemy", "jwt", "engineering"];

function imageFor(item, index) {
  const name = item.name.toLowerCase();
  if (name.includes("python")) return PRODUCT_IMAGES.python;
  if (name.includes("fastapi")) return PRODUCT_IMAGES.fastapi;
  if (name.includes("sqlalchemy")) return PRODUCT_IMAGES.sqlalchemy;
  if (name.includes("jwt")) return PRODUCT_IMAGES.jwt;
  if (name.includes("engineer") || name.includes("工程")) {
    return PRODUCT_IMAGES.engineering;
  }
  return PRODUCT_IMAGES[IMAGE_KEYS[index % IMAGE_KEYS.length]] || PRODUCT_IMAGES.default;
}

const CATEGORIES = [
  { key: "all", label: "全部" },
  { key: "python", label: "Python", match: (n) => n.includes("python") },
  { key: "fastapi", label: "FastAPI", match: (n) => n.includes("fastapi") },
  { key: "sqlalchemy", label: "SQLAlchemy", match: (n) => n.includes("sqlalchemy") },
  { key: "jwt", label: "JWT", match: (n) => n.includes("jwt") },
  {
    key: "other",
    label: "其他",
    match: (n) =>
      !["python", "fastapi", "sqlalchemy", "jwt"].some((key) =>
        n.includes(key),
      ),
  },
];

export default function StorePage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState("default");
  const [cartOpen, setCartOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detailQty, setDetailQty] = useState(1);
  const [receipt, setReceipt] = useState(null);
  const {
    cartLines,
    count,
    total,
    addToCart,
    changeQty,
    removeLine,
    clearCart,
  } = useCart(items);

  useEffect(() => {
    api
      .listItems(1, 100)
      .then((data) => setItems(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const visibleItems = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    const activeCategory = CATEGORIES.find((c) => c.key === category);
    const filtered = items.filter((item) => {
      const name = item.name.toLowerCase();
      const matchesQuery = name.includes(keyword);
      const matchesCategory =
        !activeCategory?.match || activeCategory.match(name);
      return matchesQuery && matchesCategory;
    });
    const sorted = [...filtered];
    if (sort === "price-asc") {
      sorted.sort((a, b) => a.price - b.price);
    } else if (sort === "price-desc") {
      sorted.sort((a, b) => b.price - a.price);
    } else if (sort === "newest") {
      sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    }
    return sorted;
  }, [items, query, category, sort]);

  function openDetail(item) {
    setSelected(item);
    setDetailQty(1);
  }

  function handleCheckout() {
    const orderNo = `FP${Date.now().toString(36).toUpperCase()}`;
    setReceipt({
      orderNo,
      lines: cartLines,
      total,
      placedAt: new Date().toISOString(),
    });
    clearCart();
    setCartOpen(false);
  }

  return (
    <div className="store-root">
      <header className="store-header">
        <a className="store-brand" href="#top">
          <span className="store-logo">
            <Store size={20} />
          </span>
          <strong>FastAPI 优选</strong>
        </a>
        <nav className="store-nav">
          <a href="#products">全部商品</a>
          <a
            href="#products"
            onClick={() => {
              setSort("newest");
              setCategory("all");
            }}
          >
            新品
          </a>
          <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
            API 文档
          </a>
        </nav>
        <div className="store-actions">
          <label className="shop-search">
            <Search size={16} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索商品"
            />
          </label>
          <button className="btn primary cart-btn" onClick={() => setCartOpen(true)}>
            <ShoppingCart size={16} />
            购物车
            {count > 0 && <span className="cart-badge">{count}</span>}
          </button>
        </div>
      </header>

      <section className="store-hero" id="top">
        <img className="hero-bg" src="/store/hero.png" alt="" />
        <div className="hero-overlay" />
        <div className="hero-content">
          <h1>FastAPI 优选商城</h1>
          <p>精选技术学习资料与工具</p>
          <a className="btn hero-cta" href="#products">
            <ShoppingCart size={16} />
            开始选购
          </a>
        </div>
      </section>

      <section className="store-section" id="products">
        <div className="section-head">
          <h2>全部商品</h2>
          <span>{visibleItems.length} 件</span>
        </div>
        <div className="shop-toolbar">
          <div className="category-chips">
            {CATEGORIES.map((c) => (
              <button
                key={c.key}
                className={`chip ${category === c.key ? "active" : ""}`}
                onClick={() => setCategory(c.key)}
              >
                {c.label}
              </button>
            ))}
          </div>
          <select
            className="sort-select"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="default">默认排序</option>
            <option value="price-asc">价格从低到高</option>
            <option value="price-desc">价格从高到低</option>
            <option value="newest">最新上架</option>
          </select>
        </div>
      </section>

      {error && (
        <div className="store-grid">
          <div className="alert error">{error}</div>
        </div>
      )}
      {loading && (
        <div className="store-grid">
          <div className="loading-block">加载商品</div>
        </div>
      )}

      {!loading && visibleItems.length === 0 && (
        <div className="store-grid">
          <div className="shop-empty">
            <PackageOpen size={34} />
            <p>没有找到匹配的商品</p>
          </div>
        </div>
      )}

      <div className="store-grid">
        <div className="product-grid">
          {visibleItems.map((item, index) => (
            <article
              key={item.id}
              className="product-card"
              onClick={() => openDetail(item)}
            >
              <div className="product-image">
                <img src={imageFor(item, index)} alt={item.name} loading="lazy" />
              </div>
              <div className="product-info">
                <h3>{item.name}</h3>
                <p className="product-date">上架 {formatDate(item.created_at)}</p>
                <div className="product-foot">
                  <strong className="product-price">
                    ¥{Number(item.price).toFixed(2)}
                  </strong>
                  <button
                    className="btn secondary add-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      addToCart(item.id);
                    }}
                  >
                    <Plus size={15} />
                    加入购物车
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>

      <footer className="store-footer">
        <span>FastAPI 优选商城 · 数据来自 FastAPI 实训台</span>
        <a href="/">管理后台</a>
      </footer>

      {selected && (
        <div
          className="modal-overlay"
          onClick={() => setSelected(null)}
          role="presentation"
        >
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close"
              title="关闭"
              onClick={() => setSelected(null)}
            >
              <X size={18} />
            </button>
            <div className="detail-grid">
              <img
                src={imageFor(selected, selected.id)}
                alt={selected.name}
                className="detail-image"
              />
              <div className="detail-body">
                <h3>{selected.name}</h3>
                <p className="muted">上架 {formatDate(selected.created_at)}</p>
                <strong className="detail-price">
                  ¥{Number(selected.price).toFixed(2)}
                </strong>
                <div className="qty-row">
                  <span>数量</span>
                  <span className="qty-stepper">
                    <button
                      className="icon-btn"
                      title="减少"
                      onClick={() => setDetailQty((q) => Math.max(1, q - 1))}
                    >
                      <Minus size={15} />
                    </button>
                    <strong>{detailQty}</strong>
                    <button
                      className="icon-btn"
                      title="增加"
                      onClick={() => setDetailQty((q) => q + 1)}
                    >
                      <Plus size={15} />
                    </button>
                  </span>
                </div>
                <button
                  className="btn primary block"
                  onClick={() => {
                    addToCart(selected.id, detailQty);
                    setSelected(null);
                    setCartOpen(true);
                  }}
                >
                  <ShoppingCart size={16} />
                  加入购物车
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div
        className={`drawer-overlay ${cartOpen ? "open" : ""}`}
        onClick={() => setCartOpen(false)}
        role="presentation"
      >
        <aside
          className="cart-drawer"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
        >
          <header className="drawer-head">
            <h3>购物车</h3>
            <button
              className="icon-btn"
              title="关闭"
              onClick={() => setCartOpen(false)}
            >
              <X size={17} />
            </button>
          </header>

          {cartLines.length === 0 ? (
            <div className="cart-empty">
              <ShoppingCart size={34} />
              <p>购物车是空的</p>
            </div>
          ) : (
            <div className="cart-lines">
              {cartLines.map(({ item, qty }) => (
                <div key={item.id} className="cart-line">
                  <img src={imageFor(item, item.id)} alt={item.name} />
                  <div className="cart-line-body">
                    <strong>{item.name}</strong>
                    <span>¥{Number(item.price).toFixed(2)}</span>
                    <div className="qty-stepper small">
                      <button
                        className="icon-btn"
                        title="减少"
                        onClick={() => changeQty(item.id, -1)}
                      >
                        <Minus size={14} />
                      </button>
                      <strong>{qty}</strong>
                      <button
                        className="icon-btn"
                        title="增加"
                        onClick={() => changeQty(item.id, 1)}
                      >
                        <Plus size={14} />
                      </button>
                    </div>
                  </div>
                  <button
                    className="icon-btn danger"
                    title="移除"
                    onClick={() => removeLine(item.id)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <footer className="drawer-foot">
            <div className="drawer-total">
              <span>合计</span>
              <strong>¥{total.toFixed(2)}</strong>
            </div>
            <button
              className="btn primary block"
              disabled={cartLines.length === 0}
              onClick={handleCheckout}
            >
              去结算
            </button>
          </footer>
        </aside>
      </div>

      {receipt && (
        <div className="modal-overlay" role="presentation">
          <div className="modal receipt" role="dialog" aria-modal="true">
            <span className="receipt-check">
              <CheckCircle2 size={44} />
            </span>
            <h3>下单成功</h3>
            <p className="receipt-no">订单号 {receipt.orderNo}</p>
            <div className="receipt-lines">
              {receipt.lines.map(({ item, qty }) => (
                <div key={item.id} className="receipt-line">
                  <span>
                    {item.name} × {qty}
                  </span>
                  <span>¥{(item.price * qty).toFixed(2)}</span>
                </div>
              ))}
            </div>
            <div className="receipt-total">
              <span>实付</span>
              <strong>¥{receipt.total.toFixed(2)}</strong>
            </div>
            <button className="btn primary block" onClick={() => setReceipt(null)}>
              继续逛逛
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
