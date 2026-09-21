import { useEffect, useMemo, useState } from "react";

const CART_KEY = "fastapi_shop_cart_v1";

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || {};
  } catch {
    return {};
  }
}

export default function useCart(items) {
  const [cart, setCart] = useState(readCart);

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  }, [cart]);

  const cartLines = useMemo(
    () =>
      items
        .filter((item) => cart[item.id])
        .map((item) => ({ item, qty: cart[item.id] })),
    [items, cart],
  );

  const count = cartLines.reduce((sum, line) => sum + line.qty, 0);
  const total = cartLines.reduce(
    (sum, line) => sum + line.item.price * line.qty,
    0,
  );

  function addToCart(id, qty = 1) {
    setCart((prev) => ({ ...prev, [id]: (prev[id] || 0) + qty }));
  }

  function changeQty(id, delta) {
    setCart((prev) => {
      const next = { ...prev, [id]: Math.max(0, (prev[id] || 0) + delta) };
      if (next[id] === 0) delete next[id];
      return next;
    });
  }

  function removeLine(id) {
    setCart((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  function clearCart() {
    setCart({});
  }

  return {
    cartLines,
    count,
    total,
    addToCart,
    changeQty,
    removeLine,
    clearCart,
  };
}
