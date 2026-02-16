import { sharedConfig as c, createRenderEffect as u, createSignal as T, createMemo as C, createComponent as v } from "solid-js";
function V(e, n, t) {
  let l = t.length, f = n.length, s = l, r = 0, i = 0, o = n[f - 1].nextSibling, a = null;
  for (; r < f || i < s; ) {
    if (n[r] === t[i]) {
      r++, i++;
      continue;
    }
    for (; n[f - 1] === t[s - 1]; )
      f--, s--;
    if (f === r) {
      const h = s < l ? i ? t[i - 1].nextSibling : t[s - i] : o;
      for (; i < s; ) e.insertBefore(t[i++], h);
    } else if (s === i)
      for (; r < f; )
        (!a || !a.has(n[r])) && n[r].remove(), r++;
    else if (n[r] === t[s - 1] && t[i] === n[f - 1]) {
      const h = n[--f].nextSibling;
      e.insertBefore(t[i++], n[r++].nextSibling), e.insertBefore(t[--s], h), n[f] = t[s];
    } else {
      if (!a) {
        a = /* @__PURE__ */ new Map();
        let d = i;
        for (; d < s; ) a.set(t[d], d++);
      }
      const h = a.get(n[r]);
      if (h != null)
        if (i < h && h < s) {
          let d = r, g = 1, y;
          for (; ++d < f && d < s && !((y = a.get(n[d])) == null || y !== h + g); )
            g++;
          if (g > h - i) {
            const S = n[r];
            for (; i < h; ) e.insertBefore(t[i++], S);
          } else e.replaceChild(t[i++], n[r++]);
        } else r++;
      else n[r++].remove();
    }
  }
}
const p = "_$DX_DELEGATE";
function $(e, n, t, l) {
  let f;
  const s = () => {
    const i = document.createElement("template");
    return i.innerHTML = e, i.content.firstChild;
  }, r = () => (f || (f = s())).cloneNode(!0);
  return r.cloneNode = r, r;
}
function H(e, n = window.document) {
  const t = n[p] || (n[p] = /* @__PURE__ */ new Set());
  for (let l = 0, f = e.length; l < f; l++) {
    const s = e[l];
    t.has(s) || (t.add(s), n.addEventListener(s, L));
  }
}
function b(e, n, t) {
  E(e) || (t == null ? e.removeAttribute(n) : e.setAttribute(n, t));
}
function j(e, n) {
  E(e) || (n == null ? e.removeAttribute("class") : e.className = n);
}
function m(e, n, t, l) {
  if (t !== void 0 && !l && (l = []), typeof n != "function") return A(e, n, l, t);
  u((f) => A(e, n(), f, t), l);
}
function E(e) {
  return !!c.context && !c.done && (!e || e.isConnected);
}
function L(e) {
  if (c.registry && c.events && c.events.find(([o, a]) => a === e))
    return;
  let n = e.target;
  const t = `$$${e.type}`, l = e.target, f = e.currentTarget, s = (o) => Object.defineProperty(e, "target", {
    configurable: !0,
    value: o
  }), r = () => {
    const o = n[t];
    if (o && !n.disabled) {
      const a = n[`${t}Data`];
      if (a !== void 0 ? o.call(n, a, e) : o.call(n, e), e.cancelBubble) return;
    }
    return n.host && typeof n.host != "string" && !n.host._$host && n.contains(e.target) && s(n.host), !0;
  }, i = () => {
    for (; r() && (n = n._$host || n.parentNode || n.host); ) ;
  };
  if (Object.defineProperty(e, "currentTarget", {
    configurable: !0,
    get() {
      return n || document;
    }
  }), c.registry && !c.done && (c.done = _$HY.done = !0), e.composedPath) {
    const o = e.composedPath();
    s(o[0]);
    for (let a = 0; a < o.length - 2 && (n = o[a], !!r()); a++) {
      if (n._$host) {
        n = n._$host, i();
        break;
      }
      if (n.parentNode === f)
        break;
    }
  } else i();
  s(l);
}
function A(e, n, t, l, f) {
  const s = E(e);
  if (s) {
    !t && (t = [...e.childNodes]);
    let o = [];
    for (let a = 0; a < t.length; a++) {
      const h = t[a];
      h.nodeType === 8 && h.data.slice(0, 2) === "!$" ? h.remove() : o.push(h);
    }
    t = o;
  }
  for (; typeof t == "function"; ) t = t();
  if (n === t) return t;
  const r = typeof n, i = l !== void 0;
  if (e = i && t[0] && t[0].parentNode || e, r === "string" || r === "number") {
    if (s || r === "number" && (n = n.toString(), n === t))
      return t;
    if (i) {
      let o = t[0];
      o && o.nodeType === 3 ? o.data !== n && (o.data = n) : o = document.createTextNode(n), t = x(e, t, l, o);
    } else
      t !== "" && typeof t == "string" ? t = e.firstChild.data = n : t = e.textContent = n;
  } else if (n == null || r === "boolean") {
    if (s) return t;
    t = x(e, t, l);
  } else {
    if (r === "function")
      return u(() => {
        let o = n();
        for (; typeof o == "function"; ) o = o();
        t = A(e, o, t, l);
      }), () => t;
    if (Array.isArray(n)) {
      const o = [], a = t && Array.isArray(t);
      if (N(o, n, t, f))
        return u(() => t = A(e, o, t, l, !0)), () => t;
      if (s) {
        if (!o.length) return t;
        if (l === void 0) return t = [...e.childNodes];
        let h = o[0];
        if (h.parentNode !== e) return t;
        const d = [h];
        for (; (h = h.nextSibling) !== l; ) d.push(h);
        return t = d;
      }
      if (o.length === 0) {
        if (t = x(e, t, l), i) return t;
      } else a ? t.length === 0 ? _(e, o, l) : V(e, t, o) : (t && x(e), _(e, o));
      t = o;
    } else if (n.nodeType) {
      if (s && n.parentNode) return t = i ? [n] : n;
      if (Array.isArray(t)) {
        if (i) return t = x(e, t, l, n);
        x(e, t, null, n);
      } else t == null || t === "" || !e.firstChild ? e.appendChild(n) : e.replaceChild(n, e.firstChild);
      t = n;
    }
  }
  return t;
}
function N(e, n, t, l) {
  let f = !1;
  for (let s = 0, r = n.length; s < r; s++) {
    let i = n[s], o = t && t[e.length], a;
    if (!(i == null || i === !0 || i === !1)) if ((a = typeof i) == "object" && i.nodeType)
      e.push(i);
    else if (Array.isArray(i))
      f = N(e, i, o) || f;
    else if (a === "function")
      if (l) {
        for (; typeof i == "function"; ) i = i();
        f = N(e, Array.isArray(i) ? i : [i], Array.isArray(o) ? o : [o]) || f;
      } else
        e.push(i), f = !0;
    else {
      const h = String(i);
      o && o.nodeType === 3 && o.data === h ? e.push(o) : e.push(document.createTextNode(h));
    }
  }
  return f;
}
function _(e, n, t = null) {
  for (let l = 0, f = n.length; l < f; l++) e.insertBefore(n[l], t);
}
function x(e, n, t, l) {
  if (t === void 0) return e.textContent = "";
  const f = l || document.createTextNode("");
  if (n.length) {
    let s = !1;
    for (let r = n.length - 1; r >= 0; r--) {
      const i = n[r];
      if (f !== i) {
        const o = i.parentNode === e;
        !s && !r ? o ? e.replaceChild(f, i) : e.insertBefore(f, t) : o && i.remove();
      } else s = !0;
    }
  } else e.insertBefore(f, t);
  return [f];
}
var M = /* @__PURE__ */ $("<span class=esm-operator-layout><span class=esm-operator-name></span><span class=esm-operator-args>(<!>)"), B = /* @__PURE__ */ $("<span class=esm-num>"), P = /* @__PURE__ */ $("<span class=esm-var>"), R = /* @__PURE__ */ $("<span class=esm-unknown>?"), I = /* @__PURE__ */ $("<span tabindex=0 role=button>");
function O(e) {
  return e.replace(/(\d+)/g, (n) => {
    const t = "₀₁₂₃₄₅₆₇₈₉";
    return n.split("").map((l) => t[parseInt(l, 10)]).join("");
  });
}
function D(e) {
  return (() => {
    var n = M(), t = n.firstChild, l = t.nextSibling, f = l.firstChild, s = f.nextSibling;
    return s.nextSibling, m(t, () => e.node.op), m(l, () => {
      var r;
      return (r = e.node.args) == null ? void 0 : r.map((i, o) => v(G, {
        expr: i,
        get path() {
          return [...e.path, "args", o];
        },
        get highlightedVars() {
          return e.highlightedVars;
        },
        get onHoverVar() {
          return e.onHoverVar;
        },
        get onSelect() {
          return e.onSelect;
        },
        get onReplace() {
          return e.onReplace;
        }
      })).join(", ");
    }, s), u(() => b(n, "data-operator", e.node.op)), n;
  })();
}
const G = (e) => {
  const [n, t] = T(!1), l = C(() => typeof e.expr == "string" && !q(e.expr)), f = C(() => l() && e.highlightedVars().has(e.expr)), s = C(() => {
    const d = ["esm-expression-node"];
    return n() && d.push("hovered"), f() && d.push("highlighted"), l() && d.push("variable"), typeof e.expr == "number" && d.push("number"), typeof e.expr == "object" && d.push("operator"), d.join(" ");
  }), r = () => {
    t(!0), l() && e.onHoverVar(e.expr);
  }, i = () => {
    t(!1), l() && e.onHoverVar(null);
  }, o = (d) => {
    d.stopPropagation(), e.onSelect(e.path);
  }, a = () => typeof e.expr == "number" ? (() => {
    var d = B();
    return m(d, () => U(e.expr)), u(() => b(d, "title", `Number: ${e.expr}`)), d;
  })() : typeof e.expr == "string" ? (() => {
    var d = P();
    return m(d, () => O(e.expr)), u(() => b(d, "title", `Variable: ${e.expr}`)), d;
  })() : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? v(D, {
    get node() {
      return e.expr;
    },
    get path() {
      return e.path;
    },
    get highlightedVars() {
      return e.highlightedVars;
    },
    get onHoverVar() {
      return e.onHoverVar;
    },
    get onSelect() {
      return e.onSelect;
    },
    get onReplace() {
      return e.onReplace;
    }
  }) : R();
  return (() => {
    var d = I();
    return d.$$click = o, d.addEventListener("mouseleave", i), d.addEventListener("mouseenter", r), m(d, a), u((g) => {
      var y = s(), S = h(), w = e.path.join(".");
      return y !== g.e && j(d, g.e = y), S !== g.t && b(d, "aria-label", g.t = S), w !== g.a && b(d, "data-path", g.a = w), g;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), d;
  })();
  function h() {
    return typeof e.expr == "number" ? `Number: ${e.expr}` : typeof e.expr == "string" ? `Variable: ${e.expr}` : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? `Operator: ${e.expr.op}` : "Expression";
  }
};
function q(e) {
  return /^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(e);
}
function U(e) {
  return Math.abs(e) >= 1e6 || Math.abs(e) < 1e-3 && e !== 0 ? e.toExponential(3) : e.toString();
}
H(["click"]);
export {
  G as ExpressionNode
};
