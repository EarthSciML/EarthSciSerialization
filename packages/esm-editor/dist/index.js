import { sharedConfig as Z, createRenderEffect as M, createMemo as T, untrack as it, createContext as Ve, useContext as Oe, createSignal as I, createComponent as v, Show as S, For as L, onMount as wt, onCleanup as Te, mergeProps as fe, createEffect as rt, $PROXY as te, batch as St, $TRACK as je, getListener as De } from "solid-js";
import { validate as Ct } from "esm-format";
import { customElement as ge } from "solid-element";
const Et = /* @__PURE__ */ new Set(["innerHTML", "textContent", "innerText", "children"]), kt = /* @__PURE__ */ Object.assign(/* @__PURE__ */ Object.create(null), {
  className: "class",
  htmlFor: "for"
}), pt = /* @__PURE__ */ new Set(["beforeinput", "click", "dblclick", "contextmenu", "focusin", "focusout", "input", "keydown", "keyup", "mousedown", "mousemove", "mouseout", "mouseover", "mouseup", "pointerdown", "pointermove", "pointerout", "pointerover", "pointerup", "touchend", "touchmove", "touchstart"]), At = {
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace"
}, B = (e) => T(() => e());
function Pt(e, t, n) {
  let i = n.length, l = t.length, s = i, r = 0, o = 0, f = t[l - 1].nextSibling, g = null;
  for (; r < l || o < s; ) {
    if (t[r] === n[o]) {
      r++, o++;
      continue;
    }
    for (; t[l - 1] === n[s - 1]; )
      l--, s--;
    if (l === r) {
      const d = s < i ? o ? n[o - 1].nextSibling : n[s - o] : f;
      for (; o < s; ) e.insertBefore(n[o++], d);
    } else if (s === o)
      for (; r < l; )
        (!g || !g.has(t[r])) && t[r].remove(), r++;
    else if (t[r] === n[s - 1] && n[o] === t[l - 1]) {
      const d = t[--l].nextSibling;
      e.insertBefore(n[o++], t[r++].nextSibling), e.insertBefore(n[--s], d), t[l] = n[s];
    } else {
      if (!g) {
        g = /* @__PURE__ */ new Map();
        let c = o;
        for (; c < s; ) g.set(n[c], c++);
      }
      const d = g.get(t[r]);
      if (d != null)
        if (o < d && d < s) {
          let c = r, m = 1, h;
          for (; ++c < l && c < s && !((h = g.get(t[c])) == null || h !== d + m); )
            m++;
          if (m > d - o) {
            const u = t[r];
            for (; o < d; ) e.insertBefore(n[o++], u);
          } else e.replaceChild(n[o++], t[r++]);
        } else r++;
      else t[r++].remove();
    }
  }
}
const Le = "_$DX_DELEGATE";
function _(e, t, n, i) {
  let l;
  const s = () => {
    const o = i ? document.createElementNS("http://www.w3.org/1998/Math/MathML", "template") : document.createElement("template");
    return o.innerHTML = e, n ? o.content.firstChild.firstChild : i ? o.firstChild : o.content.firstChild;
  }, r = t ? () => it(() => document.importNode(l || (l = s()), !0)) : () => (l || (l = s())).cloneNode(!0);
  return r.cloneNode = r, r;
}
function Y(e, t = window.document) {
  const n = t[Le] || (t[Le] = /* @__PURE__ */ new Set());
  for (let i = 0, l = e.length; i < l; i++) {
    const s = e[i];
    n.has(s) || (n.add(s), t.addEventListener(s, Vt));
  }
}
function q(e, t, n) {
  de(e) || (n == null ? e.removeAttribute(t) : e.setAttribute(t, n));
}
function qt(e, t, n, i) {
  de(e) || (i == null ? e.removeAttributeNS(t, n) : e.setAttributeNS(t, n, i));
}
function Rt(e, t, n) {
  de(e) || (n ? e.setAttribute(t, "") : e.removeAttribute(t));
}
function U(e, t) {
  de(e) || (t == null ? e.removeAttribute("class") : e.className = t);
}
function K(e, t, n, i) {
  if (i)
    Array.isArray(n) ? (e[`$$${t}`] = n[0], e[`$$${t}Data`] = n[1]) : e[`$$${t}`] = n;
  else if (Array.isArray(n)) {
    const l = n[0];
    e.addEventListener(t, n[0] = (s) => l.call(e, n[1], s));
  } else e.addEventListener(t, n, typeof n != "function" && n);
}
function Dt(e, t, n = {}) {
  const i = Object.keys(t || {}), l = Object.keys(n);
  let s, r;
  for (s = 0, r = l.length; s < r; s++) {
    const o = l[s];
    !o || o === "undefined" || t[o] || (Ue(e, o, !1), delete n[o]);
  }
  for (s = 0, r = i.length; s < r; s++) {
    const o = i[s], f = !!t[o];
    !o || o === "undefined" || n[o] === f || !f || (Ue(e, o, !0), n[o] = f);
  }
  return n;
}
function lt(e, t, n) {
  if (!t) return n ? q(e, "style") : t;
  const i = e.style;
  if (typeof t == "string") return i.cssText = t;
  typeof n == "string" && (i.cssText = n = void 0), n || (n = {}), t || (t = {});
  let l, s;
  for (s in n)
    t[s] == null && i.removeProperty(s), delete n[s];
  for (s in t)
    l = t[s], l !== n[s] && (i.setProperty(s, l), n[s] = l);
  return n;
}
function He(e, t, n) {
  n != null ? e.style.setProperty(t, n) : e.style.removeProperty(t);
}
function me(e, t = {}, n, i) {
  const l = {};
  return M(() => l.children = ve(e, t.children, l.children)), M(() => typeof t.ref == "function" && Ie(t.ref, e)), M(() => Nt(e, t, n, !0, l, !0)), l;
}
function Ie(e, t, n) {
  return it(() => e(t, n));
}
function a(e, t, n, i) {
  if (n !== void 0 && !i && (i = []), typeof t != "function") return ve(e, t, i, n);
  M((l) => ve(e, t(), l, n), i);
}
function Nt(e, t, n, i, l = {}, s = !1) {
  t || (t = {});
  for (const r in l)
    if (!(r in t)) {
      if (r === "children") continue;
      l[r] = Ke(e, r, null, l[r], n, s, t);
    }
  for (const r in t) {
    if (r === "children")
      continue;
    const o = t[r];
    l[r] = Ke(e, r, o, l[r], n, s, t);
  }
}
function de(e) {
  return !!Z.context && !Z.done && (!e || e.isConnected);
}
function Mt(e) {
  return e.toLowerCase().replace(/-([a-z])/g, (t, n) => n.toUpperCase());
}
function Ue(e, t, n) {
  const i = t.trim().split(/\s+/);
  for (let l = 0, s = i.length; l < s; l++) e.classList.toggle(i[l], n);
}
function Ke(e, t, n, i, l, s, r) {
  let o, f, g, d;
  if (t === "style") return lt(e, n, i);
  if (t === "classList") return Dt(e, n, i);
  if (n === i) return i;
  if (t === "ref")
    s || n(e);
  else if (t.slice(0, 3) === "on:") {
    const c = t.slice(3);
    i && e.removeEventListener(c, i, typeof i != "function" && i), n && e.addEventListener(c, n, typeof n != "function" && n);
  } else if (t.slice(0, 10) === "oncapture:") {
    const c = t.slice(10);
    i && e.removeEventListener(c, i, !0), n && e.addEventListener(c, n, !0);
  } else if (t.slice(0, 2) === "on") {
    const c = t.slice(2).toLowerCase(), m = pt.has(c);
    if (!m && i) {
      const h = Array.isArray(i) ? i[0] : i;
      e.removeEventListener(c, h);
    }
    (m || n) && (K(e, c, n, m), m && Y([c]));
  } else if (t.slice(0, 5) === "attr:")
    q(e, t.slice(5), n);
  else if (t.slice(0, 5) === "bool:")
    Rt(e, t.slice(5), n);
  else if ((d = t.slice(0, 5) === "prop:") || (g = Et.has(t)) || (o = e.nodeName.includes("-") || "is" in r)) {
    if (d)
      t = t.slice(5), f = !0;
    else if (de(e)) return n;
    t === "class" || t === "className" ? U(e, n) : o && !f && !g ? e[Mt(t)] = n : e[t] = n;
  } else {
    const c = t.indexOf(":") > -1 && At[t.split(":")[0]];
    c ? qt(e, c, t, n) : q(e, kt[t] || t, n);
  }
  return n;
}
function Vt(e) {
  if (Z.registry && Z.events && Z.events.find(([f, g]) => g === e))
    return;
  let t = e.target;
  const n = `$$${e.type}`, i = e.target, l = e.currentTarget, s = (f) => Object.defineProperty(e, "target", {
    configurable: !0,
    value: f
  }), r = () => {
    const f = t[n];
    if (f && !t.disabled) {
      const g = t[`${n}Data`];
      if (g !== void 0 ? f.call(t, g, e) : f.call(t, e), e.cancelBubble) return;
    }
    return t.host && typeof t.host != "string" && !t.host._$host && t.contains(e.target) && s(t.host), !0;
  }, o = () => {
    for (; r() && (t = t._$host || t.parentNode || t.host); ) ;
  };
  if (Object.defineProperty(e, "currentTarget", {
    configurable: !0,
    get() {
      return t || document;
    }
  }), Z.registry && !Z.done && (Z.done = _$HY.done = !0), e.composedPath) {
    const f = e.composedPath();
    s(f[0]);
    for (let g = 0; g < f.length - 2 && (t = f[g], !!r()); g++) {
      if (t._$host) {
        t = t._$host, o();
        break;
      }
      if (t.parentNode === l)
        break;
    }
  } else o();
  s(i);
}
function ve(e, t, n, i, l) {
  const s = de(e);
  if (s) {
    !n && (n = [...e.childNodes]);
    let f = [];
    for (let g = 0; g < n.length; g++) {
      const d = n[g];
      d.nodeType === 8 && d.data.slice(0, 2) === "!$" ? d.remove() : f.push(d);
    }
    n = f;
  }
  for (; typeof n == "function"; ) n = n();
  if (t === n) return n;
  const r = typeof t, o = i !== void 0;
  if (e = o && n[0] && n[0].parentNode || e, r === "string" || r === "number") {
    if (s || r === "number" && (t = t.toString(), t === n))
      return n;
    if (o) {
      let f = n[0];
      f && f.nodeType === 3 ? f.data !== t && (f.data = t) : f = document.createTextNode(t), n = ne(e, n, i, f);
    } else
      n !== "" && typeof n == "string" ? n = e.firstChild.data = t : n = e.textContent = t;
  } else if (t == null || r === "boolean") {
    if (s) return n;
    n = ne(e, n, i);
  } else {
    if (r === "function")
      return M(() => {
        let f = t();
        for (; typeof f == "function"; ) f = f();
        n = ve(e, f, n, i);
      }), () => n;
    if (Array.isArray(t)) {
      const f = [], g = n && Array.isArray(n);
      if (Ne(f, t, n, l))
        return M(() => n = ve(e, f, n, i, !0)), () => n;
      if (s) {
        if (!f.length) return n;
        if (i === void 0) return n = [...e.childNodes];
        let d = f[0];
        if (d.parentNode !== e) return n;
        const c = [d];
        for (; (d = d.nextSibling) !== i; ) c.push(d);
        return n = c;
      }
      if (f.length === 0) {
        if (n = ne(e, n, i), o) return n;
      } else g ? n.length === 0 ? ze(e, f, i) : Pt(e, n, f) : (n && ne(e), ze(e, f));
      n = f;
    } else if (t.nodeType) {
      if (s && t.parentNode) return n = o ? [t] : t;
      if (Array.isArray(n)) {
        if (o) return n = ne(e, n, i, t);
        ne(e, n, null, t);
      } else n == null || n === "" || !e.firstChild ? e.appendChild(t) : e.replaceChild(t, e.firstChild);
      n = t;
    }
  }
  return n;
}
function Ne(e, t, n, i) {
  let l = !1;
  for (let s = 0, r = t.length; s < r; s++) {
    let o = t[s], f = n && n[e.length], g;
    if (!(o == null || o === !0 || o === !1)) if ((g = typeof o) == "object" && o.nodeType)
      e.push(o);
    else if (Array.isArray(o))
      l = Ne(e, o, f) || l;
    else if (g === "function")
      if (i) {
        for (; typeof o == "function"; ) o = o();
        l = Ne(e, Array.isArray(o) ? o : [o], Array.isArray(f) ? f : [f]) || l;
      } else
        e.push(o), l = !0;
    else {
      const d = String(o);
      f && f.nodeType === 3 && f.data === d ? e.push(f) : e.push(document.createTextNode(d));
    }
  }
  return l;
}
function ze(e, t, n = null) {
  for (let i = 0, l = t.length; i < l; i++) e.insertBefore(t[i], n);
}
function ne(e, t, n, i) {
  if (n === void 0) return e.textContent = "";
  const l = i || document.createTextNode("");
  if (t.length) {
    let s = !1;
    for (let r = t.length - 1; r >= 0; r--) {
      const o = t[r];
      if (l !== o) {
        const f = o.parentNode === e;
        !s && !r ? f ? e.replaceChild(l, o) : e.insertBefore(l, n) : f && o.remove();
      } else s = !0;
    }
  } else e.insertBefore(l, n);
  return [l];
}
var Ot = /* @__PURE__ */ _('<div class=structural-editing-menu style="position:absolute;background-color:white;border:1px solid #ccc;border-radius:4px;padding:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);z-index:1000;min-width:200px"><div class=menu-section><h4 class=menu-header>Wrap in Operator</h4><div class=wrap-operators></div></div><div class=menu-section><button class=close-menu-btn>Close'), Tt = /* @__PURE__ */ _("<button class=wrap-operator-btn>"), It = /* @__PURE__ */ _('<div class=menu-section><button class=unwrap-btn title="Remove the outer operator and keep its argument">Unwrap'), Ft = /* @__PURE__ */ _('<div class=menu-section><button class=delete-term-btn title="Remove this term from the operation">Delete Term'), jt = /* @__PURE__ */ _("<div class=draggable-expression>");
const Lt = [{
  op: "-",
  label: "Negate",
  arity: 1
}, {
  op: "abs",
  label: "Absolute Value",
  arity: 1
}, {
  op: "sqrt",
  label: "Square Root",
  arity: 1
}, {
  op: "exp",
  label: "Exponential",
  arity: 1
}, {
  op: "log",
  label: "Natural Log",
  arity: 1
}, {
  op: "sin",
  label: "Sine",
  arity: 1
}, {
  op: "cos",
  label: "Cosine",
  arity: 1
}, {
  op: "+",
  label: "Addition",
  arity: 2
}, {
  op: "*",
  label: "Multiplication",
  arity: 2
}, {
  op: "/",
  label: "Division",
  arity: 2
}, {
  op: "^",
  label: "Power",
  arity: 2
}], st = /* @__PURE__ */ new Set(["+", "*"]), at = Ve();
function Je(e) {
  return typeof e == "object" && e !== null && "op" in e && "args" in e && Array.isArray(e.args) && e.args.length === 1;
}
function be(e) {
  return typeof e == "object" && e !== null && "op" in e && st.has(e.op);
}
function xe(e, t) {
  let n = e;
  for (const i of t) {
    if (n == null) return null;
    if (i === "args" && typeof n == "object" && "args" in n)
      n = n.args;
    else if (typeof i == "number" && Array.isArray(n))
      n = n[i];
    else
      return null;
  }
  return n;
}
function Be(e, t) {
  if (t.length < 2)
    return {
      parent: null,
      parentPath: [],
      argIndex: null
    };
  const n = t.slice(0, -2), i = t[t.length - 1];
  return {
    parent: xe(e, n),
    parentPath: n,
    argIndex: typeof i == "number" ? i : null
  };
}
function ie(e, t, n) {
  if (t.length === 0)
    return n;
  let i = JSON.parse(JSON.stringify(e)), l = i;
  for (let r = 0; r < t.length - 1; r++) {
    const o = t[r];
    if (o === "args" && typeof l == "object" && "args" in l)
      l = l.args;
    else if (typeof o == "number" && Array.isArray(l))
      l = l[o];
    else
      throw new Error(`Invalid path segment: ${o}`);
  }
  const s = t[t.length - 1];
  if (typeof s == "number" && Array.isArray(l))
    l[s] = n;
  else
    throw new Error(`Invalid final path segment: ${s}`);
  return i;
}
function sl(e) {
  const [t, n] = I({
    isDragging: !1,
    dragPath: null,
    dragIndex: null,
    dropTarget: null
  }), m = {
    replaceNode: (h, u) => {
      const $ = e.rootExpression(), y = ie($, h, u);
      e.onRootReplace(y);
    },
    wrapNode: (h, u) => {
      const $ = e.rootExpression(), y = xe($, h);
      if (!y) return;
      const R = ie($, h, {
        op: u,
        args: [y]
      });
      e.onRootReplace(R);
    },
    unwrapNode: (h) => {
      const u = e.rootExpression(), $ = xe(u, h);
      if (!Je($))
        return !1;
      const y = $.args[0], p = ie(u, h, y);
      return e.onRootReplace(p), !0;
    },
    deleteTerm: (h) => {
      const u = e.rootExpression(), {
        parent: $,
        parentPath: y,
        argIndex: p
      } = Be(u, h);
      if (!$ || !be($) || p === null)
        return !1;
      const R = $;
      if (R.args.length <= 2) {
        const k = R.args[1 - p], b = ie(u, y, k);
        e.onRootReplace(b);
      } else {
        const k = [...R.args];
        k.splice(p, 1);
        const b = {
          ...R,
          args: k
        }, x = ie(u, y, b);
        e.onRootReplace(x);
      }
      return !0;
    },
    reorderArgs: (h, u, $) => {
      const y = e.rootExpression(), p = xe(y, h);
      if (!be(p))
        return !1;
      const R = p, k = [...R.args], [b] = k.splice(u, 1);
      k.splice($, 0, b);
      const x = {
        ...R,
        args: k
      }, A = ie(y, h, x);
      return e.onRootReplace(A), !0;
    },
    canUnwrap: (h) => Je(h),
    canDeleteTerm: (h, u) => {
      const $ = e.rootExpression(), {
        parent: y
      } = Be($, u);
      return y !== null && be(y);
    },
    canReorderArgs: (h) => be(h) && h.args.length > 1,
    getWrapOperators: () => [...Lt],
    dragState: t,
    setDragState: n
  };
  return v(at.Provider, {
    value: m,
    get children() {
      return e.children;
    }
  });
}
function Ae() {
  const e = Oe(at);
  if (!e)
    throw new Error("useStructuralEditingContext must be used within a StructuralEditingProvider");
  return e;
}
function Ht(e) {
  const t = Ae();
  if (!e.isVisible || !e.selectedPath || !e.selectedExpr)
    return null;
  const n = (o) => {
    e.selectedPath && (t.wrapNode(e.selectedPath, o), e.onClose());
  }, i = () => {
    e.selectedPath && t.unwrapNode(e.selectedPath) && e.onClose();
  }, l = () => {
    e.selectedPath && t.deleteTerm(e.selectedPath) && e.onClose();
  }, s = t.canUnwrap(e.selectedExpr), r = e.selectedPath && t.canDeleteTerm(e.selectedExpr, e.selectedPath);
  return (() => {
    var o = Ot(), f = o.firstChild, g = f.firstChild, d = g.nextSibling, c = f.nextSibling, m = c.firstChild;
    return a(d, () => t.getWrapOperators().map((h) => (() => {
      var u = Tt();
      return u.$$click = () => n(h.op), a(u, () => h.label), M(() => q(u, "title", h.label)), u;
    })())), a(o, s && (() => {
      var h = It(), u = h.firstChild;
      return u.$$click = i, h;
    })(), c), a(o, r && (() => {
      var h = Ft(), u = h.firstChild;
      return u.$$click = l, h;
    })(), c), K(m, "click", e.onClose, !0), M((h) => {
      var y, p;
      var u = `${((y = e.position) == null ? void 0 : y.x) || 0}px`, $ = `${((p = e.position) == null ? void 0 : p.y) || 0}px`;
      return u !== h.e && He(o, "left", h.e = u), $ !== h.t && He(o, "top", h.t = $), h;
    }, {
      e: void 0,
      t: void 0
    }), o;
  })();
}
function ot(e) {
  const t = Ae();
  if (!e.canDrag)
    return e.children;
  const n = (r) => {
    r.dataTransfer && (r.dataTransfer.effectAllowed = "move", r.dataTransfer.setData("text/plain", JSON.stringify({
      path: e.path,
      index: e.index,
      parentPath: e.parentPath
    }))), t.setDragState({
      isDragging: !0,
      dragPath: e.path,
      dragIndex: e.index,
      dropTarget: null
    });
  }, i = () => {
    t.setDragState({
      isDragging: !1,
      dragPath: null,
      dragIndex: null,
      dropTarget: null
    });
  }, l = (r) => {
    r.preventDefault(), r.dataTransfer && (r.dataTransfer.dropEffect = "move");
    const o = t.dragState();
    o.isDragging && o.dragIndex !== e.index && t.setDragState({
      ...o,
      dropTarget: {
        path: e.parentPath,
        index: e.index
      }
    });
  }, s = (r) => {
    var f;
    r.preventDefault();
    const o = (f = r.dataTransfer) == null ? void 0 : f.getData("text/plain");
    if (o)
      try {
        const g = JSON.parse(o);
        g.index !== e.index && g.parentPath.join(".") === e.parentPath.join(".") && t.reorderArgs(e.parentPath, g.index, e.index);
      } catch (g) {
        console.error("Failed to parse drag data:", g);
      }
  };
  return (() => {
    var r = jt();
    return r.addEventListener("drop", s), r.addEventListener("dragover", l), r.addEventListener("dragend", i), r.addEventListener("dragstart", n), q(r, "draggable", !0), a(r, () => e.children), M(() => q(r, "data-drag-index", e.index)), r;
  })();
}
Y(["click"]);
var Ut = /* @__PURE__ */ _("<span class=esm-infix-op>"), We = /* @__PURE__ */ _("<span class=esm-operator> <!> "), Kt = /* @__PURE__ */ _("<span class=esm-multiplication>"), zt = /* @__PURE__ */ _("<span class=esm-multiply>⋅"), Jt = /* @__PURE__ */ _("<span class=esm-fraction><span class=esm-fraction-numerator></span><span class=esm-fraction-denominator>"), Bt = /* @__PURE__ */ _("<span class=esm-exponentiation><span class=esm-base></span><span class=esm-exponent>"), Wt = /* @__PURE__ */ _("<span class=esm-derivative-wrt><span class=esm-d-operator>d</span><span class=esm-variable>"), Yt = /* @__PURE__ */ _("<span class=esm-derivative><span class=esm-d-operator>d</span><span class=esm-derivative-body>"), Gt = /* @__PURE__ */ _('<span class="esm-function esm-sqrt"><span class=esm-radical>√</span><span class=esm-sqrt-content>'), Xt = /* @__PURE__ */ _("<span class=esm-function><span class=esm-function-name></span><span class=esm-function-args>(<!>)"), Qt = /* @__PURE__ */ _("<span class=esm-comparison>"), Zt = /* @__PURE__ */ _("<span class=esm-generic-function><span class=esm-function-name></span><span class=esm-function-args>(<!>)"), en = /* @__PURE__ */ _("<span class=esm-num>"), tn = /* @__PURE__ */ _("<span class=esm-var>"), nn = /* @__PURE__ */ _("<span class=esm-unknown>?"), rn = /* @__PURE__ */ _("<span tabindex=0 role=button>");
function ln(e) {
  return e.replace(/(\d+)/g, (t) => {
    const n = "₀₁₂₃₄₅₆₇₈₉";
    return t.split("").map((i) => n[parseInt(i, 10)]).join("");
  });
}
function sn(e) {
  let t;
  try {
    t = Ae();
  } catch {
  }
  const n = st.has(e.node.op), {
    op: i,
    args: l
  } = e.node, s = (r, o) => {
    const f = [...e.path, "args", o], g = v(Se, {
      expr: r,
      path: f,
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
      },
      get selectedPath() {
        return e.selectedPath;
      },
      get parentPath() {
        return e.path;
      },
      indexInParent: o
    });
    return t && n && ((l == null ? void 0 : l.length) || 0) > 1 ? v(ot, {
      path: f,
      index: o,
      get parentPath() {
        return e.path;
      },
      canDrag: !0,
      children: g
    }) : g;
  };
  switch (i) {
    case "+":
    case "-":
      return (() => {
        var r = Ut();
        return q(r, "data-operator", i), a(r, () => l == null ? void 0 : l.map((o, f) => [v(S, {
          when: f > 0,
          get children() {
            var g = We(), d = g.firstChild, c = d.nextSibling;
            return c.nextSibling, a(g, i, c), g;
          }
        }), B(() => s(o, f))])), r;
      })();
    case "*":
      return (() => {
        var r = Kt();
        return q(r, "data-operator", i), a(r, () => l == null ? void 0 : l.map((o, f) => [v(S, {
          when: f > 0,
          get children() {
            return zt();
          }
        }), B(() => s(o, f))])), r;
      })();
    case "/":
      return (() => {
        var r = Jt(), o = r.firstChild, f = o.nextSibling;
        return q(r, "data-operator", i), a(o, () => l && s(l[0], 0)), a(f, () => l && s(l[1], 1)), r;
      })();
    case "^":
      return (() => {
        var r = Bt(), o = r.firstChild, f = o.nextSibling;
        return q(r, "data-operator", i), a(o, () => l && s(l[0], 0)), a(f, () => l && s(l[1], 1)), r;
      })();
    case "D":
      return (() => {
        var r = Yt(), o = r.firstChild, f = o.nextSibling;
        return q(r, "data-operator", i), a(f, () => l && s(l[0], 0)), a(r, v(S, {
          get when() {
            return e.node.wrt;
          },
          get children() {
            var g = Wt(), d = g.firstChild, c = d.nextSibling;
            return a(c, () => e.node.wrt), g;
          }
        }), null), r;
      })();
    case "sqrt":
      return (() => {
        var r = Gt(), o = r.firstChild, f = o.nextSibling;
        return q(r, "data-operator", i), a(f, () => l && s(l[0], 0)), r;
      })();
    case "exp":
    case "log":
    case "sin":
    case "cos":
    case "tan":
      return (() => {
        var r = Xt(), o = r.firstChild, f = o.nextSibling, g = f.firstChild, d = g.nextSibling;
        return d.nextSibling, q(r, "data-operator", i), a(o, i), a(f, () => l == null ? void 0 : l.map((c, m) => [v(S, {
          when: m > 0,
          children: ", "
        }), B(() => s(c, m))]), d), r;
      })();
    case ">":
    case "<":
    case ">=":
    case "<=":
    case "==":
    case "!=":
      return (() => {
        var r = Qt();
        return q(r, "data-operator", i), a(r, () => l == null ? void 0 : l.map((o, f) => [v(S, {
          when: f > 0,
          get children() {
            var g = We(), d = g.firstChild, c = d.nextSibling;
            return c.nextSibling, a(g, i, c), g;
          }
        }), B(() => s(o, f))])), r;
      })();
    default:
      return (() => {
        var r = Zt(), o = r.firstChild, f = o.nextSibling, g = f.firstChild, d = g.nextSibling;
        return d.nextSibling, q(r, "data-operator", i), a(o, i), a(f, () => l == null ? void 0 : l.map((c, m) => [v(S, {
          when: m > 0,
          children: ", "
        }), B(() => s(c, m))]), d), r;
      })();
  }
}
const Se = (e) => {
  const [t, n] = I(!1), [i, l] = I(!1), [s, r] = I({
    x: 0,
    y: 0
  });
  let o;
  try {
    o = Ae();
  } catch {
  }
  const f = T(() => typeof e.expr == "string" && !an(e.expr)), g = T(() => f() && e.highlightedVars().has(e.expr)), d = T(() => e.selectedPath && e.selectedPath.length === e.path.length && e.selectedPath.every((x, A) => x === e.path[A])), c = T(() => o && e.parentPath && typeof e.indexInParent == "number" && e.parentPath.length > 0), m = T(() => {
    const x = ["esm-expression-node"];
    return t() && x.push("hovered"), g() && x.push("highlighted"), d() && x.push("selected"), f() && x.push("variable"), typeof e.expr == "number" && x.push("number"), typeof e.expr == "object" && x.push("operator"), x.join(" ");
  }), h = () => {
    n(!0), f() && e.onHoverVar(e.expr);
  }, u = () => {
    n(!1), f() && e.onHoverVar(null);
  }, $ = (x) => {
    x.stopPropagation(), e.onSelect(e.path);
  }, y = (x) => {
    x.preventDefault(), x.stopPropagation(), o && (e.onSelect(e.path), r({
      x: x.clientX,
      y: x.clientY
    }), l(!0));
  }, p = () => {
    l(!1);
  }, R = () => typeof e.expr == "number" ? (() => {
    var x = en();
    return a(x, () => on(e.expr)), M(() => q(x, "title", `Number: ${e.expr}`)), x;
  })() : typeof e.expr == "string" ? (() => {
    var x = tn();
    return a(x, () => ln(e.expr)), M(() => q(x, "title", `Variable: ${e.expr}`)), x;
  })() : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? v(sn, {
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
    },
    get selectedPath() {
      return e.selectedPath;
    }
  }) : nn(), k = [(() => {
    var x = rn();
    return x.$$contextmenu = y, x.$$click = $, x.addEventListener("mouseleave", u), x.addEventListener("mouseenter", h), a(x, R), M((A) => {
      var V = m(), E = b(), D = e.path.join(".");
      return V !== A.e && U(x, A.e = V), E !== A.t && q(x, "aria-label", A.t = E), D !== A.a && q(x, "data-path", A.a = D), A;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), x;
  })(), v(S, {
    get when() {
      return i() && o;
    },
    get children() {
      return v(Ht, {
        get selectedPath() {
          return e.path;
        },
        get selectedExpr() {
          return e.expr;
        },
        get isVisible() {
          return i();
        },
        get position() {
          return s();
        },
        onClose: p
      });
    }
  })];
  if (c() && o && e.parentPath && typeof e.indexInParent == "number")
    return v(ot, {
      get path() {
        return e.path;
      },
      get index() {
        return e.indexInParent;
      },
      get parentPath() {
        return e.parentPath;
      },
      canDrag: !0,
      children: k
    });
  return k;
  function b() {
    return typeof e.expr == "number" ? `Number: ${e.expr}` : typeof e.expr == "string" ? `Variable: ${e.expr}` : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? `Operator: ${e.expr.op}` : "Expression";
  }
};
function an(e) {
  return /^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(e);
}
function on(e) {
  return Math.abs(e) >= 1e6 || Math.abs(e) < 1e-3 && e !== 0 ? e.toExponential(3) : e.toString();
}
Y(["click", "contextmenu"]);
var cn = /* @__PURE__ */ _("<div role=button tabindex=0><div class=template-label></div><div class=template-description>"), dn = /* @__PURE__ */ _("<div class=context-suggestions><h4 class=section-title><span class=section-icon>🧪</span>Model Context</h4><div class=suggestions-grid>"), un = /* @__PURE__ */ _("<div role=button tabindex=0><div class=item-type></div><div class=item-label>"), hn = /* @__PURE__ */ _(`<div class=palette-search><input type=text class=search-input placeholder="Search expressions... (type '/' to open)">`), fn = /* @__PURE__ */ _('<div class=no-results><div class=no-results-icon>🔍</div><div class=no-results-text>No expressions found for "<!>"</div><div class=no-results-hint>Try searching for operators, functions, or keywords'), gn = /* @__PURE__ */ _("<div class=quick-insert-help>Press <kbd>Escape</kbd> to close, click or drag to insert"), mn = /* @__PURE__ */ _("<div><div class=palette-content>"), $n = /* @__PURE__ */ _("<div class=palette-section><h4 class=section-title><span class=section-icon></span></h4><div class=templates-grid>");
const Ye = [
  // Calculus operators
  {
    id: "derivative",
    label: "D(_, t)",
    description: "Time derivative",
    expression: {
      op: "D",
      args: ["_placeholder_", "t"]
    },
    keywords: ["derivative", "time", "differential", "d", "dt"],
    category: "calculus"
  },
  {
    id: "gradient",
    label: "grad(_, x)",
    description: "Spatial gradient",
    expression: {
      op: "grad",
      args: ["_placeholder_", "x"]
    },
    keywords: ["gradient", "spatial", "grad", "nabla"],
    category: "calculus"
  },
  {
    id: "divergence",
    label: "div(_)",
    description: "Divergence operator",
    expression: {
      op: "div",
      args: ["_placeholder_"]
    },
    keywords: ["divergence", "div"],
    category: "calculus"
  },
  {
    id: "laplacian",
    label: "laplacian(_)",
    description: "Laplacian operator",
    expression: {
      op: "laplacian",
      args: ["_placeholder_"]
    },
    keywords: ["laplacian", "laplace", "del2"],
    category: "calculus"
  },
  // Arithmetic operators
  {
    id: "addition",
    label: "_ + _",
    description: "Addition",
    expression: {
      op: "+",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["add", "addition", "plus", "+"],
    category: "arithmetic"
  },
  {
    id: "subtraction",
    label: "_ - _",
    description: "Subtraction",
    expression: {
      op: "-",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["subtract", "subtraction", "minus", "-"],
    category: "arithmetic"
  },
  {
    id: "multiplication",
    label: "_ * _",
    description: "Multiplication",
    expression: {
      op: "*",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["multiply", "multiplication", "times", "*"],
    category: "arithmetic"
  },
  {
    id: "division",
    label: "_ / _",
    description: "Division",
    expression: {
      op: "/",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["divide", "division", "over", "/"],
    category: "arithmetic"
  },
  {
    id: "power",
    label: "_ ^ _",
    description: "Power/Exponentiation",
    expression: {
      op: "^",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["power", "exponent", "exp", "^", "**"],
    category: "arithmetic"
  },
  {
    id: "negate",
    label: "-_",
    description: "Unary negation",
    expression: {
      op: "-",
      args: ["_placeholder_"]
    },
    keywords: ["negate", "negative", "unary", "minus"],
    category: "arithmetic"
  },
  // Mathematical functions
  {
    id: "exponential",
    label: "exp(_)",
    description: "Exponential function (e^x)",
    expression: {
      op: "exp",
      args: ["_placeholder_"]
    },
    keywords: ["exponential", "exp", "e"],
    category: "functions"
  },
  {
    id: "logarithm",
    label: "log(_)",
    description: "Natural logarithm",
    expression: {
      op: "log",
      args: ["_placeholder_"]
    },
    keywords: ["logarithm", "log", "ln", "natural"],
    category: "functions"
  },
  {
    id: "sqrt",
    label: "sqrt(_)",
    description: "Square root",
    expression: {
      op: "sqrt",
      args: ["_placeholder_"]
    },
    keywords: ["sqrt", "square", "root"],
    category: "functions"
  },
  {
    id: "absolute",
    label: "abs(_)",
    description: "Absolute value",
    expression: {
      op: "abs",
      args: ["_placeholder_"]
    },
    keywords: ["absolute", "abs", "magnitude"],
    category: "functions"
  },
  {
    id: "sine",
    label: "sin(_)",
    description: "Sine function",
    expression: {
      op: "sin",
      args: ["_placeholder_"]
    },
    keywords: ["sine", "sin", "trigonometry"],
    category: "functions"
  },
  {
    id: "cosine",
    label: "cos(_)",
    description: "Cosine function",
    expression: {
      op: "cos",
      args: ["_placeholder_"]
    },
    keywords: ["cosine", "cos", "trigonometry"],
    category: "functions"
  },
  {
    id: "minimum",
    label: "min(_, _)",
    description: "Minimum of two values",
    expression: {
      op: "min",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["minimum", "min", "smaller"],
    category: "functions"
  },
  {
    id: "maximum",
    label: "max(_, _)",
    description: "Maximum of two values",
    expression: {
      op: "max",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["maximum", "max", "larger"],
    category: "functions"
  },
  // Logical operators
  {
    id: "ifelse",
    label: "ifelse(_, _, _)",
    description: "Conditional expression",
    expression: {
      op: "ifelse",
      args: ["_placeholder_", "_placeholder_", "_placeholder_"]
    },
    keywords: ["if", "ifelse", "conditional", "ternary"],
    category: "logic"
  },
  {
    id: "greater_than",
    label: "_ > _",
    description: "Greater than comparison",
    expression: {
      op: ">",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["greater", "than", ">", "compare"],
    category: "logic"
  },
  {
    id: "less_than",
    label: "_ < _",
    description: "Less than comparison",
    expression: {
      op: "<",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["less", "than", "<", "compare"],
    category: "logic"
  },
  {
    id: "equals",
    label: "_ == _",
    description: "Equality comparison",
    expression: {
      op: "==",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["equals", "equal", "==", "compare"],
    category: "logic"
  },
  {
    id: "logical_and",
    label: "_ && _",
    description: "Logical AND",
    expression: {
      op: "and",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["and", "logical", "&&", "both"],
    category: "logic"
  },
  {
    id: "logical_or",
    label: "_ || _",
    description: "Logical OR",
    expression: {
      op: "or",
      args: ["_placeholder_", "_placeholder_"]
    },
    keywords: ["or", "logical", "||", "either"],
    category: "logic"
  },
  {
    id: "logical_not",
    label: "!_",
    description: "Logical NOT",
    expression: {
      op: "not",
      args: ["_placeholder_"]
    },
    keywords: ["not", "logical", "!", "negate"],
    category: "logic"
  }
], vn = {
  calculus: {
    title: "Calculus",
    description: "Differential operators",
    icon: "∂"
  },
  arithmetic: {
    title: "Arithmetic",
    description: "Basic mathematical operations",
    icon: "±"
  },
  functions: {
    title: "Functions",
    description: "Mathematical functions",
    icon: "ƒ"
  },
  logic: {
    title: "Logic",
    description: "Logical operators and comparisons",
    icon: "∧"
  }
}, _n = (e) => {
  const [t, n] = I(!1), i = (r) => {
    r.dataTransfer && (r.dataTransfer.effectAllowed = "copy", r.dataTransfer.setData("application/json", JSON.stringify({
      type: "expression-template",
      expression: e.template.expression,
      templateId: e.template.id
    }))), n(!0);
  }, l = () => {
    n(!1);
  }, s = () => {
    e.onInsert(e.template.expression);
  };
  return (() => {
    var r = cn(), o = r.firstChild, f = o.nextSibling;
    return r.$$click = s, r.addEventListener("dragend", l), r.addEventListener("dragstart", i), q(r, "draggable", !0), a(o, () => e.template.label), a(f, () => e.template.description), M((g) => {
      var d = `expression-template ${t() ? "dragging" : ""}`, c = e.template.description, m = `Insert ${e.template.label}: ${e.template.description}`;
      return d !== g.e && U(r, g.e = d), c !== g.t && q(r, "title", g.t = c), m !== g.a && q(r, "aria-label", g.a = m), g;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), r;
  })();
}, bn = (e) => {
  const t = T(() => {
    if (!e.model) return [];
    const n = [];
    return e.model.variables && e.model.variables.forEach((i) => {
      n.push({
        label: i.name,
        expression: i.name,
        type: "variable"
      });
    }), e.model.reaction_systems && e.model.reaction_systems.forEach((i) => {
      i.species && i.species.forEach((l) => {
        n.push({
          label: l.name,
          expression: l.name,
          type: "species"
        });
      });
    }), n;
  });
  return v(S, {
    get when() {
      return t().length > 0;
    },
    get children() {
      var n = dn(), i = n.firstChild, l = i.nextSibling;
      return a(l, v(L, {
        get each() {
          return t();
        },
        children: (s) => (() => {
          var r = un(), o = r.firstChild, f = o.nextSibling;
          return r.$$click = () => e.onInsert(s.expression), a(o, () => s.type.charAt(0).toUpperCase()), a(f, () => s.label), M((g) => {
            var d = `context-item ${s.type}`, c = `${s.type}: ${s.label}`, m = `Insert ${s.type} ${s.label}`;
            return d !== g.e && U(r, g.e = d), c !== g.t && q(r, "title", g.t = c), m !== g.a && q(r, "aria-label", g.a = m), g;
          }, {
            e: void 0,
            t: void 0,
            a: void 0
          }), r;
        })()
      })), n;
    }
  });
}, yn = (e) => {
  const [t, n] = I(""), i = T(() => e.searchQuery || t()), l = T(() => {
    const d = i().toLowerCase().trim();
    return d ? Ye.filter((c) => c.label.toLowerCase().includes(d) || c.description.toLowerCase().includes(d) || c.keywords.some((m) => m.toLowerCase().includes(d))) : Ye;
  }), s = T(() => {
    const d = {};
    return l().forEach((c) => {
      d[c.category] || (d[c.category] = []), d[c.category].push(c);
    }), d;
  }), r = (d) => {
    var c, m;
    (c = e.onInsertExpression) == null || c.call(e, d), e.quickInsertMode && ((m = e.onCloseQuickInsert) == null || m.call(e));
  }, o = (d) => {
    e.onSearchQueryChange ? e.onSearchQueryChange(d) : n(d);
  }, f = (d) => {
    var c;
    e.quickInsertMode && d.key === "Escape" && ((c = e.onCloseQuickInsert) == null || c.call(e));
  }, g = () => {
    const d = ["expression-palette"];
    return e.quickInsertMode && d.push("quick-insert-mode"), e.visible === !1 && d.push("hidden"), e.class && d.push(e.class), d.join(" ");
  };
  return (() => {
    var d = mn(), c = d.firstChild;
    return d.$$keydown = f, a(d, v(S, {
      get when() {
        return e.quickInsertMode || i();
      },
      get children() {
        var m = hn(), h = m.firstChild;
        return h.$$input = (u) => o(u.currentTarget.value), M(() => h.autofocus = e.quickInsertMode), M(() => h.value = i()), m;
      }
    }), c), a(c, v(S, {
      get when() {
        return !i();
      },
      get children() {
        return v(bn, {
          get model() {
            return e.currentModel;
          },
          onInsert: r
        });
      }
    }), null), a(c, v(L, {
      get each() {
        return Object.entries(vn);
      },
      children: ([m, h]) => {
        const u = s()[m] || [];
        return v(S, {
          get when() {
            return u.length > 0;
          },
          get children() {
            var $ = $n(), y = $.firstChild, p = y.firstChild, R = y.nextSibling;
            return a(p, () => h.icon), a(y, () => h.title, null), a(R, v(L, {
              each: u,
              children: (k) => v(_n, {
                template: k,
                onInsert: r
              })
            })), $;
          }
        });
      }
    }), null), a(c, v(S, {
      get when() {
        return B(() => !!i())() && l().length === 0;
      },
      get children() {
        var m = fn(), h = m.firstChild, u = h.nextSibling, $ = u.firstChild, y = $.nextSibling;
        return y.nextSibling, a(u, i, y), m;
      }
    }), null), a(d, v(S, {
      get when() {
        return e.quickInsertMode;
      },
      get children() {
        return gn();
      }
    }), null), M(() => U(d, g())), d;
  })();
};
Y(["click", "keydown", "input"]);
var xn = /* @__PURE__ */ _('<div class=equation-description title="Equation description">'), wn = /* @__PURE__ */ _("<div><div class=equation-content><div class=equation-lhs></div><div class=equation-equals aria-label=equals>=</div><div class=equation-rhs>");
const ct = (e) => {
  const [t, n] = I(null), [i, l] = I(null), s = T(() => {
    const d = e.highlightedVars || /* @__PURE__ */ new Set(), c = i();
    return c && !d.has(c) ? /* @__PURE__ */ new Set([...d, c]) : d;
  }), r = (d) => {
    n(d);
  }, o = (d) => {
    l(d);
  }, f = (d, c) => {
    if (e.readonly || !e.onEquationChange) return;
    const m = structuredClone(e.equation);
    let h = m;
    for (let u = 0; u < d.length - 1; u++)
      h = h[d[u]];
    d.length > 0 && (h[d[d.length - 1]] = c), e.onEquationChange(m);
  }, g = () => {
    const d = ["equation-editor"];
    return e.readonly && d.push("readonly"), e.class && d.push(e.class), d.join(" ");
  };
  return (() => {
    var d = wn(), c = d.firstChild, m = c.firstChild, h = m.nextSibling, u = h.nextSibling;
    return a(m, v(Se, {
      get expr() {
        return e.equation.lhs;
      },
      path: ["lhs"],
      highlightedVars: () => s(),
      onHoverVar: o,
      onSelect: r,
      onReplace: f,
      get selectedPath() {
        return t();
      }
    })), a(u, v(Se, {
      get expr() {
        return e.equation.rhs;
      },
      path: ["rhs"],
      highlightedVars: () => s(),
      onHoverVar: o,
      onSelect: r,
      onReplace: f,
      get selectedPath() {
        return t();
      }
    })), a(d, v(S, {
      get when() {
        return e.equation.description;
      },
      get children() {
        var $ = xn();
        return a($, () => e.equation.description), $;
      }
    }), null), M(($) => {
      var y = g(), p = e.id;
      return y !== $.e && U(d, $.e = y), p !== $.t && q(d, "id", $.t = p), $;
    }, {
      e: void 0,
      t: void 0
    }), d;
  })();
};
var Sn = /* @__PURE__ */ _("<div class=variable-unit title=Unit>[<!>]"), Cn = /* @__PURE__ */ _('<div class=variable-default title="Default value">= '), En = /* @__PURE__ */ _("<div class=variable-description title=Description>"), kn = /* @__PURE__ */ _('<button class=variable-remove-btn title="Remove variable">×'), pn = /* @__PURE__ */ _("<div role=button tabindex=0><div class=variable-info><div class=variable-header><span class=variable-name></span><span>"), An = /* @__PURE__ */ _('<button class=add-btn title="Add new variable"aria-label="Add new variable">+'), Pn = /* @__PURE__ */ _("<button class=add-first-btn>Add first variable"), qn = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>📊</div><div class=empty-text>No variables defined"), Rn = /* @__PURE__ */ _("<div class=variables-content>"), Dn = /* @__PURE__ */ _("<div class=variables-panel><div class=panel-header><span>▶</span><h3>Variables (<!>)"), Nn = /* @__PURE__ */ _("<div class=variable-group><h4 class=group-title><span></span>s (<!>)</h4><div class=variables-list>"), Mn = /* @__PURE__ */ _('<button class=add-btn title="Add new equation"aria-label="Add new equation">+'), Vn = /* @__PURE__ */ _("<button class=add-first-btn>Add first equation"), On = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚖️</div><div class=empty-text>No equations defined"), Tn = /* @__PURE__ */ _("<div class=equations-content>"), In = /* @__PURE__ */ _("<div class=equations-panel><div class=panel-header><span>▶</span><h3>Equations (<!>)"), Fn = /* @__PURE__ */ _('<button class=equation-remove-btn title="Remove equation">×'), jn = /* @__PURE__ */ _("<div class=equation-item>"), Ln = /* @__PURE__ */ _('<div class=event-add-buttons><button class=add-btn title="Add continuous event">+ Continuous</button><button class=add-btn title="Add discrete event">+ Discrete'), Hn = /* @__PURE__ */ _("<div class=event-group><h4>Continuous Events"), Un = /* @__PURE__ */ _("<div class=event-group><h4>Discrete Events"), Kn = /* @__PURE__ */ _("<div class=empty-actions><button class=add-first-btn>Add continuous event</button><button class=add-first-btn>Add discrete event"), zn = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚡</div><div class=empty-text>No events defined"), Jn = /* @__PURE__ */ _("<div class=events-content>"), Bn = /* @__PURE__ */ _("<div class=events-panel><div class=panel-header><span>▶</span><h3>Events (<!>)"), Ge = /* @__PURE__ */ _("<div class=event-description>"), Wn = /* @__PURE__ */ _('<div class="event-item continuous"><div class=event-name>'), Yn = /* @__PURE__ */ _('<div class="event-item discrete"><div class=event-name>'), Gn = /* @__PURE__ */ _("<div class=model-description>"), Xn = /* @__PURE__ */ _("<div class=palette-sidebar>"), Qn = /* @__PURE__ */ _("<div><div class=model-editor-layout><div class=model-content><div class=model-header><h2 class=model-name></h2></div><div class=model-panels>");
const we = {
  state: {
    label: "State",
    color: "blue",
    description: "State variable"
  },
  parameter: {
    label: "Param",
    color: "green",
    description: "Parameter"
  },
  observed: {
    label: "Obs",
    color: "orange",
    description: "Observed variable"
  },
  other: {
    label: "Var",
    color: "gray",
    description: "Variable"
  }
}, Zn = (e) => {
  const [t, n] = I(!1), i = () => we[e.type], l = () => {
    var r;
    e.readonly || (r = e.onEdit) == null || r.call(e, e.variable);
  }, s = (r) => {
    var o;
    r.stopPropagation(), e.readonly || (o = e.onRemove) == null || o.call(e, e.variable.name);
  };
  return (() => {
    var r = pn(), o = r.firstChild, f = o.firstChild, g = f.firstChild, d = g.nextSibling;
    return r.$$click = l, r.addEventListener("mouseleave", () => n(!1)), r.addEventListener("mouseenter", () => n(!0)), a(g, () => e.variable.name), a(d, () => i().label), a(o, v(S, {
      get when() {
        return e.variable.unit;
      },
      get children() {
        var c = Sn(), m = c.firstChild, h = m.nextSibling;
        return h.nextSibling, a(c, () => e.variable.unit, h), c;
      }
    }), null), a(o, v(S, {
      get when() {
        return e.variable.default_value !== void 0;
      },
      get children() {
        var c = Cn();
        return c.firstChild, a(c, () => e.variable.default_value, null), c;
      }
    }), null), a(o, v(S, {
      get when() {
        return e.variable.description;
      },
      get children() {
        var c = En();
        return a(c, () => e.variable.description), c;
      }
    }), null), a(r, v(S, {
      get when() {
        return B(() => !e.readonly)() && t();
      },
      get children() {
        var c = kn();
        return c.$$click = s, M(() => q(c, "aria-label", `Remove variable ${e.variable.name}`)), c;
      }
    }), null), M((c) => {
      var m = `variable-item ${t() ? "hovered" : ""}`, h = `variable-type-badge ${i().color}`, u = i().description;
      return m !== c.e && U(r, c.e = m), h !== c.t && U(d, c.t = h), u !== c.a && q(d, "title", c.a = u), c;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), r;
  })();
}, ei = (e) => {
  const [t, n] = I(!0), i = T(() => {
    const l = e.variables || [], s = {
      state: [],
      parameter: [],
      observed: [],
      other: []
    };
    return l.forEach((r) => {
      let o = "other";
      r.name.startsWith("k_") || r.name.includes("rate") || r.name.includes("param") ? o = "parameter" : r.name.includes("obs") || r.name.includes("measured") ? o = "observed" : !r.name.includes("_const") && !r.name.includes("_param") && (o = "state"), s[o].push(r);
    }), s;
  });
  return (() => {
    var l = Dn(), s = l.firstChild, r = s.firstChild, o = r.nextSibling, f = o.firstChild, g = f.nextSibling;
    return g.nextSibling, s.$$click = () => n(!t()), a(o, () => (e.variables || []).length, g), a(s, v(S, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var d = An();
        return d.$$click = (c) => {
          var m;
          c.stopPropagation(), (m = e.onAddVariable) == null || m.call(e);
        }, d;
      }
    }), null), a(l, v(S, {
      get when() {
        return t();
      },
      get children() {
        var d = Rn();
        return a(d, v(L, {
          get each() {
            return Object.entries(i());
          },
          children: ([c, m]) => v(S, {
            get when() {
              return m.length > 0;
            },
            get children() {
              var h = Nn(), u = h.firstChild, $ = u.firstChild, y = $.nextSibling, p = y.nextSibling;
              p.nextSibling;
              var R = u.nextSibling;
              return a($, () => we[c].label), a(u, () => we[c].description, y), a(u, () => m.length, p), a(R, v(L, {
                each: m,
                children: (k) => v(Zn, {
                  variable: k,
                  type: c,
                  get onEdit() {
                    return e.onEditVariable;
                  },
                  get onRemove() {
                    return e.onRemoveVariable;
                  },
                  get readonly() {
                    return e.readonly;
                  }
                })
              })), M(() => U($, `group-badge ${we[c].color}`)), h;
            }
          })
        }), null), a(d, v(S, {
          get when() {
            return (e.variables || []).length === 0;
          },
          get children() {
            var c = qn(), m = c.firstChild;
            return m.nextSibling, a(c, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = Pn();
                return K(h, "click", e.onAddVariable, !0), h;
              }
            }), null), c;
          }
        }), null), d;
      }
    }), null), M(() => U(r, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, ti = (e) => {
  const [t, n] = I(!0);
  return (() => {
    var i = In(), l = i.firstChild, s = l.firstChild, r = s.nextSibling, o = r.firstChild, f = o.nextSibling;
    return f.nextSibling, l.$$click = () => n(!t()), a(r, () => (e.equations || []).length, f), a(l, v(S, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var g = Mn();
        return g.$$click = (d) => {
          var c;
          d.stopPropagation(), (c = e.onAddEquation) == null || c.call(e);
        }, g;
      }
    }), null), a(i, v(S, {
      get when() {
        return t();
      },
      get children() {
        var g = Tn();
        return a(g, v(L, {
          get each() {
            return e.equations || [];
          },
          children: (d, c) => (() => {
            var m = jn();
            return a(m, v(ct, {
              equation: d,
              get highlightedVars() {
                return e.highlightedVars;
              },
              onEquationChange: (h) => {
                var u;
                return (u = e.onEditEquation) == null ? void 0 : u.call(e, c(), h);
              },
              get readonly() {
                return e.readonly;
              },
              class: "model-equation"
            }), null), a(m, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = Fn();
                return h.$$click = () => {
                  var u;
                  return (u = e.onRemoveEquation) == null ? void 0 : u.call(e, c());
                }, M(() => q(h, "aria-label", `Remove equation ${c() + 1}`)), h;
              }
            }), null), m;
          })()
        }), null), a(g, v(S, {
          get when() {
            return (e.equations || []).length === 0;
          },
          get children() {
            var d = On(), c = d.firstChild;
            return c.nextSibling, a(d, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var m = Vn();
                return K(m, "click", e.onAddEquation, !0), m;
              }
            }), null), d;
          }
        }), null), g;
      }
    }), null), M(() => U(s, `expand-icon ${t() ? "expanded" : ""}`)), i;
  })();
}, ni = (e) => {
  const [t, n] = I(!0), i = () => (e.continuousEvents || []).length + (e.discreteEvents || []).length;
  return (() => {
    var l = Bn(), s = l.firstChild, r = s.firstChild, o = r.nextSibling, f = o.firstChild, g = f.nextSibling;
    return g.nextSibling, s.$$click = () => n(!t()), a(o, i, g), a(s, v(S, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var d = Ln(), c = d.firstChild, m = c.nextSibling;
        return c.$$click = (h) => {
          var u;
          h.stopPropagation(), (u = e.onAddContinuousEvent) == null || u.call(e);
        }, m.$$click = (h) => {
          var u;
          h.stopPropagation(), (u = e.onAddDiscreteEvent) == null || u.call(e);
        }, d;
      }
    }), null), a(l, v(S, {
      get when() {
        return t();
      },
      get children() {
        var d = Jn();
        return a(d, v(S, {
          get when() {
            return (e.continuousEvents || []).length > 0;
          },
          get children() {
            var c = Hn();
            return c.firstChild, a(c, v(L, {
              get each() {
                return e.continuousEvents || [];
              },
              children: (m) => (() => {
                var h = Wn(), u = h.firstChild;
                return a(u, () => m.name || "Unnamed Event"), a(h, v(S, {
                  get when() {
                    return m.description;
                  },
                  get children() {
                    var $ = Ge();
                    return a($, () => m.description), $;
                  }
                }), null), h;
              })()
            }), null), c;
          }
        }), null), a(d, v(S, {
          get when() {
            return (e.discreteEvents || []).length > 0;
          },
          get children() {
            var c = Un();
            return c.firstChild, a(c, v(L, {
              get each() {
                return e.discreteEvents || [];
              },
              children: (m) => (() => {
                var h = Yn(), u = h.firstChild;
                return a(u, () => m.name || "Unnamed Event"), a(h, v(S, {
                  get when() {
                    return m.description;
                  },
                  get children() {
                    var $ = Ge();
                    return a($, () => m.description), $;
                  }
                }), null), h;
              })()
            }), null), c;
          }
        }), null), a(d, v(S, {
          get when() {
            return i() === 0;
          },
          get children() {
            var c = zn(), m = c.firstChild;
            return m.nextSibling, a(c, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = Kn(), u = h.firstChild, $ = u.nextSibling;
                return K(u, "click", e.onAddContinuousEvent, !0), K($, "click", e.onAddDiscreteEvent, !0), h;
              }
            }), null), c;
          }
        }), null), d;
      }
    }), null), M(() => U(r, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, ii = (e) => {
  const [t, n] = I(/* @__PURE__ */ new Set()), i = (h) => {
    if (e.readonly || !e.onModelChange) return;
    const u = {
      ...e.model,
      ...h
    };
    e.onModelChange(u);
  }, l = () => {
    console.log("Add variable");
  }, s = (h) => {
    console.log("Edit variable:", h.name);
  }, r = (h) => {
    const u = (e.model.variables || []).filter(($) => $.name !== h);
    i({
      variables: u
    });
  }, o = () => {
    const h = {
      lhs: "_placeholder_",
      rhs: 0
    }, u = [...e.model.equations || [], h];
    i({
      equations: u
    });
  }, f = (h, u) => {
    const $ = [...e.model.equations || []];
    $[h] = u, i({
      equations: $
    });
  }, g = (h) => {
    const u = (e.model.equations || []).filter(($, y) => y !== h);
    i({
      equations: u
    });
  }, d = () => {
    console.log("Add continuous event");
  }, c = () => {
    console.log("Add discrete event");
  }, m = () => {
    const h = ["model-editor"];
    return e.readonly && h.push("readonly"), e.class && h.push(e.class), h.join(" ");
  };
  return (() => {
    var h = Qn(), u = h.firstChild, $ = u.firstChild, y = $.firstChild, p = y.firstChild, R = y.nextSibling;
    return a(p, () => e.model.name || "Untitled Model"), a(y, v(S, {
      get when() {
        return e.model.description;
      },
      get children() {
        var k = Gn();
        return a(k, () => e.model.description), k;
      }
    }), null), a(R, v(ei, {
      get variables() {
        return e.model.variables;
      },
      onAddVariable: l,
      onEditVariable: s,
      onRemoveVariable: r,
      get readonly() {
        return e.readonly;
      }
    }), null), a(R, v(ti, {
      get equations() {
        return e.model.equations;
      },
      get highlightedVars() {
        return t();
      },
      onAddEquation: o,
      onEditEquation: f,
      onRemoveEquation: g,
      get readonly() {
        return e.readonly;
      }
    }), null), a(R, v(ni, {
      get continuousEvents() {
        return e.model.continuous_events;
      },
      get discreteEvents() {
        return e.model.discrete_events;
      },
      onAddContinuousEvent: d,
      onAddDiscreteEvent: c,
      get readonly() {
        return e.readonly;
      }
    }), null), a(u, v(S, {
      get when() {
        return B(() => !!e.showPalette)() && !e.readonly;
      },
      get children() {
        var k = Xn();
        return a(k, v(yn, {
          get currentModel() {
            return e.model;
          },
          visible: !0
        })), k;
      }
    }), null), M(() => U(h, m())), h;
  })();
};
Y(["click"]);
var ri = /* @__PURE__ */ _('<span class=reaction-name title="Reaction name">'), li = /* @__PURE__ */ _('<button class=reaction-remove-btn title="Remove reaction">×'), si = /* @__PURE__ */ _('<div class=reaction-rate-editor><div class=rate-editor-header><span>Rate Expression:</span><button class=collapse-btn title="Collapse rate editor">▲</button></div><div class=rate-editor-content>'), ai = /* @__PURE__ */ _("<div class=reaction-description>"), oi = /* @__PURE__ */ _("<div class=reaction-item><div class=reaction-header><div class=reaction-equation><span class=reactants></span><span class=reaction-arrow>→<span>[<!>]</span></span><span class=products></span></div><div class=reaction-controls>"), ci = /* @__PURE__ */ _("<div class=no-rate-placeholder><span>No rate expression defined</span><button class=add-rate-btn>Add rate constant"), di = /* @__PURE__ */ _('<button class=add-btn title="Add new species"aria-label="Add new species">+'), ui = /* @__PURE__ */ _("<button class=add-first-btn>Add first species"), hi = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>🧪</div><div class=empty-text>No species defined"), fi = /* @__PURE__ */ _("<div class=species-content>"), gi = /* @__PURE__ */ _("<div class=species-panel><div class=panel-header><span>▶</span><h3>Species (<!>)"), mi = /* @__PURE__ */ _("<span class=species-name>(<!>)"), $i = /* @__PURE__ */ _("<div class=species-description>"), vi = /* @__PURE__ */ _('<button class=species-remove-btn title="Remove species">×'), _i = /* @__PURE__ */ _("<div class=species-item><div class=species-info><span class=species-formula>"), bi = /* @__PURE__ */ _('<button class=add-btn title="Add new parameter"aria-label="Add new parameter">+'), yi = /* @__PURE__ */ _("<button class=add-first-btn>Add first parameter"), xi = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚗️</div><div class=empty-text>No parameters defined"), wi = /* @__PURE__ */ _("<div class=parameters-content>"), Si = /* @__PURE__ */ _("<div class=parameters-panel><div class=panel-header><span>▶</span><h3>Parameters (<!>)"), Ci = /* @__PURE__ */ _("<span class=parameter-unit>[<!>]"), Ei = /* @__PURE__ */ _("<span class=parameter-value>= "), ki = /* @__PURE__ */ _("<div class=parameter-description>"), pi = /* @__PURE__ */ _('<button class=parameter-remove-btn title="Remove parameter">×'), Ai = /* @__PURE__ */ _("<div class=parameter-item><div class=parameter-info><span class=parameter-name>"), Pi = /* @__PURE__ */ _('<button class=add-reaction-btn title="Add new reaction">+ Add Reaction'), qi = /* @__PURE__ */ _("<button class=add-first-btn>Add first reaction"), Ri = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚛️</div><div class=empty-text>No reactions defined"), Di = /* @__PURE__ */ _("<div><div class=reaction-editor-layout><div class=reactions-main><div class=reactions-header><h2>Reactions (<!>)</h2></div><div class=reactions-list></div></div><div class=reaction-sidebar>");
const Me = (e) => e.replace(/(\d+)/g, (t) => {
  const n = "₀₁₂₃₄₅₆₇₈₉";
  return t.split("").map((i) => n[parseInt(i, 10)]).join("");
}), Ni = (e) => {
  const [t, n] = I(!1), [i, l] = I(null), [s, r] = I(null), o = T(() => {
    const u = /* @__PURE__ */ new Map();
    return e.species.forEach(($) => {
      u.set($.name, $);
    }), u;
  }), f = T(() => {
    const u = e.highlightedVars || /* @__PURE__ */ new Set(), $ = s();
    return $ && !u.has($) ? /* @__PURE__ */ new Set([...u, $]) : u;
  }), g = () => e.reaction.reactants ? e.reaction.reactants.map((u, $) => {
    const y = o().get(u.species), p = (y == null ? void 0 : y.formula) || u.species, R = u.stoichiometry !== void 0 ? u.stoichiometry : 1;
    return `${R > 1 ? R : ""}${Me(p)}`;
  }).join(" + ") : "", d = () => e.reaction.products ? e.reaction.products.map((u, $) => {
    const y = o().get(u.species), p = (y == null ? void 0 : y.formula) || u.species, R = u.stoichiometry !== void 0 ? u.stoichiometry : 1;
    return `${R > 1 ? R : ""}${Me(p)}`;
  }).join(" + ") : "", c = () => {
    e.readonly || n(!t());
  }, m = (u) => {
    if (e.readonly || !e.onEditReaction) return;
    const $ = {
      ...e.reaction,
      rate: u
    };
    e.onEditReaction(e.index, $);
  }, h = () => {
    var u;
    e.readonly || (u = e.onRemoveReaction) == null || u.call(e, e.index);
  };
  return (() => {
    var u = oi(), $ = u.firstChild, y = $.firstChild, p = y.firstChild, R = p.nextSibling, k = R.firstChild, b = k.nextSibling, x = b.firstChild, A = x.nextSibling;
    A.nextSibling;
    var V = R.nextSibling, E = y.nextSibling;
    return a(p, g), b.$$click = c, a(b, () => e.reaction.rate ? "k" : "?", A), a(V, d), a(E, v(S, {
      get when() {
        return e.reaction.name;
      },
      get children() {
        var D = ri();
        return a(D, () => e.reaction.name), D;
      }
    }), null), a(E, v(S, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var D = li();
        return D.$$click = h, M(() => q(D, "aria-label", `Remove reaction ${e.index + 1}`)), D;
      }
    }), null), a(u, v(S, {
      get when() {
        return t();
      },
      get children() {
        var D = si(), C = D.firstChild, w = C.firstChild, N = w.nextSibling, O = C.nextSibling;
        return N.$$click = () => n(!1), a(O, v(S, {
          get when() {
            return e.reaction.rate;
          },
          get fallback() {
            return (() => {
              var P = ci(), F = P.firstChild, H = F.nextSibling;
              return H.$$click = () => m("k_rate"), P;
            })();
          },
          get children() {
            return v(Se, {
              get expr() {
                return e.reaction.rate;
              },
              path: ["rate"],
              highlightedVars: () => f(),
              onHoverVar: r,
              onSelect: l,
              onReplace: (P, F) => {
                P.length === 1 && P[0] === "rate" && m(F);
              },
              get selectedPath() {
                return i();
              }
            });
          }
        })), D;
      }
    }), null), a(u, v(S, {
      get when() {
        return e.reaction.description;
      },
      get children() {
        var D = ai();
        return a(D, () => e.reaction.description), D;
      }
    }), null), M((D) => {
      var C = `rate-expression ${t() ? "expanded" : ""} ${e.readonly ? "" : "clickable"}`, w = e.readonly ? void 0 : "Click to edit rate expression";
      return C !== D.e && U(b, D.e = C), w !== D.t && q(b, "title", D.t = w), D;
    }, {
      e: void 0,
      t: void 0
    }), u;
  })();
}, Mi = (e) => {
  const [t, n] = I(!0);
  return (() => {
    var i = gi(), l = i.firstChild, s = l.firstChild, r = s.nextSibling, o = r.firstChild, f = o.nextSibling;
    return f.nextSibling, l.$$click = () => n(!t()), a(r, () => (e.species || []).length, f), a(l, v(S, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var g = di();
        return g.$$click = (d) => {
          var c;
          d.stopPropagation(), (c = e.onAddSpecies) == null || c.call(e);
        }, g;
      }
    }), null), a(i, v(S, {
      get when() {
        return t();
      },
      get children() {
        var g = fi();
        return a(g, v(L, {
          get each() {
            return e.species || [];
          },
          children: (d) => (() => {
            var c = _i(), m = c.firstChild, h = m.firstChild;
            return c.$$click = () => {
              var u;
              return (u = e.onEditSpecies) == null ? void 0 : u.call(e, d);
            }, a(h, () => Me(d.formula || d.name)), a(m, v(S, {
              get when() {
                return d.name !== d.formula;
              },
              get children() {
                var u = mi(), $ = u.firstChild, y = $.nextSibling;
                return y.nextSibling, a(u, () => d.name, y), u;
              }
            }), null), a(c, v(S, {
              get when() {
                return d.description;
              },
              get children() {
                var u = $i();
                return a(u, () => d.description), u;
              }
            }), null), a(c, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var u = vi();
                return u.$$click = ($) => {
                  var y;
                  $.stopPropagation(), (y = e.onRemoveSpecies) == null || y.call(e, d.name);
                }, M(() => q(u, "aria-label", `Remove species ${d.name}`)), u;
              }
            }), null), c;
          })()
        }), null), a(g, v(S, {
          get when() {
            return (e.species || []).length === 0;
          },
          get children() {
            var d = hi(), c = d.firstChild;
            return c.nextSibling, a(d, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var m = ui();
                return K(m, "click", e.onAddSpecies, !0), m;
              }
            }), null), d;
          }
        }), null), g;
      }
    }), null), M(() => U(s, `expand-icon ${t() ? "expanded" : ""}`)), i;
  })();
}, Vi = (e) => {
  const [t, n] = I(!0), i = T(() => (e.parameters || []).filter((l) => l.name.startsWith("k_") || l.name.includes("rate") || l.name.includes("const")));
  return (() => {
    var l = Si(), s = l.firstChild, r = s.firstChild, o = r.nextSibling, f = o.firstChild, g = f.nextSibling;
    return g.nextSibling, s.$$click = () => n(!t()), a(o, () => i().length, g), a(s, v(S, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var d = bi();
        return d.$$click = (c) => {
          var m;
          c.stopPropagation(), (m = e.onAddParameter) == null || m.call(e);
        }, d;
      }
    }), null), a(l, v(S, {
      get when() {
        return t();
      },
      get children() {
        var d = wi();
        return a(d, v(L, {
          get each() {
            return i();
          },
          children: (c) => (() => {
            var m = Ai(), h = m.firstChild, u = h.firstChild;
            return m.$$click = () => {
              var $;
              return ($ = e.onEditParameter) == null ? void 0 : $.call(e, c);
            }, a(u, () => c.name), a(h, v(S, {
              get when() {
                return c.unit;
              },
              get children() {
                var $ = Ci(), y = $.firstChild, p = y.nextSibling;
                return p.nextSibling, a($, () => c.unit, p), $;
              }
            }), null), a(h, v(S, {
              get when() {
                return c.default_value !== void 0;
              },
              get children() {
                var $ = Ei();
                return $.firstChild, a($, () => c.default_value, null), $;
              }
            }), null), a(m, v(S, {
              get when() {
                return c.description;
              },
              get children() {
                var $ = ki();
                return a($, () => c.description), $;
              }
            }), null), a(m, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var $ = pi();
                return $.$$click = (y) => {
                  var p;
                  y.stopPropagation(), (p = e.onRemoveParameter) == null || p.call(e, c.name);
                }, M(() => q($, "aria-label", `Remove parameter ${c.name}`)), $;
              }
            }), null), m;
          })()
        }), null), a(d, v(S, {
          get when() {
            return i().length === 0;
          },
          get children() {
            var c = xi(), m = c.firstChild;
            return m.nextSibling, a(c, v(S, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = yi();
                return K(h, "click", e.onAddParameter, !0), h;
              }
            }), null), c;
          }
        }), null), d;
      }
    }), null), M(() => U(r, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, Oi = (e) => {
  const t = (m) => {
    if (e.readonly || !e.onReactionSystemChange) return;
    const h = {
      ...e.reactionSystem,
      ...m
    };
    e.onReactionSystemChange(h);
  }, n = () => {
    const m = {
      reactants: [{
        species: "A",
        stoichiometry: 1
      }],
      products: [{
        species: "B",
        stoichiometry: 1
      }],
      rate: "k_rate"
    }, h = [...e.reactionSystem.reactions || [], m];
    t({
      reactions: h
    });
  }, i = (m, h) => {
    const u = [...e.reactionSystem.reactions || []];
    u[m] = h, t({
      reactions: u
    });
  }, l = (m) => {
    const h = (e.reactionSystem.reactions || []).filter((u, $) => $ !== m);
    t({
      reactions: h
    });
  }, s = () => {
    console.log("Add species");
  }, r = (m) => {
    console.log("Edit species:", m.name);
  }, o = (m) => {
    const h = (e.reactionSystem.species || []).filter((u) => u.name !== m);
    t({
      species: h
    });
  }, f = () => {
    console.log("Add parameter");
  }, g = (m) => {
    console.log("Edit parameter:", m.name);
  }, d = (m) => {
    console.log("Remove parameter:", m);
  }, c = () => {
    const m = ["reaction-editor"];
    return e.readonly && m.push("readonly"), e.class && m.push(e.class), m.join(" ");
  };
  return (() => {
    var m = Di(), h = m.firstChild, u = h.firstChild, $ = u.firstChild, y = $.firstChild, p = y.firstChild, R = p.nextSibling;
    R.nextSibling;
    var k = $.nextSibling, b = u.nextSibling;
    return a(y, () => (e.reactionSystem.reactions || []).length, R), a($, v(S, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var x = Pi();
        return x.$$click = n, x;
      }
    }), null), a(k, v(L, {
      get each() {
        return e.reactionSystem.reactions || [];
      },
      children: (x, A) => v(Ni, {
        reaction: x,
        get index() {
          return A();
        },
        get species() {
          return e.reactionSystem.species || [];
        },
        onEditReaction: i,
        onRemoveReaction: l,
        get highlightedVars() {
          return e.highlightedVars;
        },
        get readonly() {
          return e.readonly;
        }
      })
    }), null), a(k, v(S, {
      get when() {
        return (e.reactionSystem.reactions || []).length === 0;
      },
      get children() {
        var x = Ri(), A = x.firstChild;
        return A.nextSibling, a(x, v(S, {
          get when() {
            return !e.readonly;
          },
          get children() {
            var V = qi();
            return V.$$click = n, V;
          }
        }), null), x;
      }
    }), null), a(b, v(Mi, {
      get species() {
        return e.reactionSystem.species;
      },
      onAddSpecies: s,
      onEditSpecies: r,
      onRemoveSpecies: o,
      get readonly() {
        return e.readonly;
      }
    }), null), a(b, v(Vi, {
      parameters: [],
      onAddParameter: f,
      onEditParameter: g,
      onRemoveParameter: d,
      get readonly() {
        return e.readonly;
      }
    }), null), M(() => U(m, c())), m;
  })();
};
Y(["click"]);
var Ti = /* @__PURE__ */ _("<svg><rect width=50 height=30></svg>", !1, !0, !1), Ii = /* @__PURE__ */ _("<svg><ellipse rx=25 ry=15></svg>", !1, !0, !1), Fi = /* @__PURE__ */ _("<svg><polygon></svg>", !1, !0, !1), ji = /* @__PURE__ */ _("<svg><circle r=20></svg>", !1, !0, !1), Li = /* @__PURE__ */ _("<svg><line></svg>", !1, !0, !1), Hi = /* @__PURE__ */ _('<div class="absolute top-4 right-4 border border-gray-300 bg-white bg-opacity-90"><svg width=150 height=150><rect width=100% height=100% fill=white stroke=gray></rect><rect fill=none stroke=red stroke-width=1>'), Ui = /* @__PURE__ */ _("<svg><circle r=2></svg>", !1, !0, !1), Xe = /* @__PURE__ */ _('<p class="text-sm mt-2">'), Ki = /* @__PURE__ */ _("<div>Species: "), zi = /* @__PURE__ */ _('<div><h3 class="font-bold text-lg"></h3><p class="text-sm text-gray-600">Type: </p><div class="text-xs mt-2"><div>Variables: </div><div>Equations: '), Ji = /* @__PURE__ */ _('<div><h3 class="font-bold text-lg"></h3><p class="text-sm text-gray-600">Type: </p><p class=text-sm>From: <!> → To: '), Bi = /* @__PURE__ */ _('<div class="absolute bottom-4 left-4 p-4 bg-white border border-gray-300 rounded shadow-lg max-w-md"><button class="mt-2 px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded">Close'), Wi = /* @__PURE__ */ _('<div class="relative w-full h-full"><svg class="border border-gray-300"><defs><marker id=arrowhead markerWidth=10 markerHeight=7 refX=9 refY=3.5 orient=auto><polygon points="0 0, 10 3.5, 0 7"fill=#999></polygon></marker></defs><g class=edges></g><g class=nodes></g><g class=labels>'), Yi = /* @__PURE__ */ _("<svg><text text-anchor=middle font-size=12 fill=black pointer-events=none></svg>", !1, !0, !1);
const le = (e) => {
  let t = null, n = !1;
  const i = () => {
    if (n) return;
    const l = 400, s = 300, r = Math.min(200, Math.max(100, e.length * 15));
    e.forEach((o, f) => {
      const g = f / e.length * 2 * Math.PI;
      o.x = l + Math.cos(g) * r, o.y = s + Math.sin(g) * r;
    }), t == null || t();
  };
  return setTimeout(i, 10), {
    force: (l, s) => le(e),
    on: (l, s) => (l === "tick" && (t = s), le(e)),
    nodes: (l) => le(l),
    alpha: (l) => le(e),
    restart: () => (setTimeout(i, 10), le(e)),
    stop: () => {
      n = !0;
    }
  };
}, Gi = (e) => le(e), Xi = () => ({
  id: (e) => ({
    distance: () => ({
      strength: () => ({})
    })
  }),
  distance: (e) => ({
    strength: (t) => ({})
  }),
  strength: (e) => ({}),
  links: (e) => ({})
}), Qi = () => ({
  strength: (e) => ({})
}), Zi = (e, t) => ({}), er = () => ({
  radius: (e) => ({})
}), tr = (e) => {
  const t = () => e.width ?? 800, n = () => e.height ?? 600, i = T(() => [...e.graph.nodes]), l = T(() => e.graph.edges.map((C) => ({
    source: i().find((w) => w.id === C.source),
    target: i().find((w) => w.id === C.target),
    data: C.data
  }))), [s, r] = I(null), [o, f] = I(null), [g, d] = I(null), [c, m] = I({
    x: 0,
    y: 0,
    k: 1
  });
  let h, u;
  const $ = () => {
    const C = i();
    l(), u = Gi(C).force("link", Xi().id((w) => w.id).distance(100).strength(0.1)).force("charge", Qi().strength(-300)).force("center", Zi(t() / 2, n() / 2)).force("collision", er().radius(30)).on("tick", () => {
      y([...C]);
    }), C.forEach((w) => {
      w.x === void 0 && (w.x = t() / 2 + (Math.random() - 0.5) * 100), w.y === void 0 && (w.y = n() / 2 + (Math.random() - 0.5) * 100);
    });
  }, [, y] = I(i(), {
    equals: !1
  }), p = (C) => {
    var N;
    const w = {
      stroke: "#333",
      "stroke-width": ((N = s()) == null ? void 0 : N.id) === C.id ? 3 : 1,
      cursor: "pointer",
      filter: g() === C.id ? "brightness(1.2)" : "none"
    };
    switch (C.type) {
      case "model":
        return {
          ...w,
          fill: "#4CAF50",
          rx: 5,
          ry: 5
        };
      case "data_loader":
        return {
          ...w,
          fill: "#2196F3"
        };
      case "operator":
        return {
          ...w,
          fill: "#FF9800"
        };
      case "reaction_system":
        return {
          ...w,
          fill: "#9C27B0"
        };
      default:
        return {
          ...w,
          fill: "#607D8B"
        };
    }
  }, R = (C) => {
    var N;
    const w = {
      stroke: "#999",
      "stroke-width": ((N = o()) == null ? void 0 : N.id) === C.id ? 3 : 1,
      cursor: "pointer",
      "marker-end": "url(#arrowhead)",
      filter: g() === C.id ? "brightness(1.5)" : "none"
    };
    switch (C.type) {
      case "variable":
        return {
          ...w,
          "stroke-dasharray": "none"
        };
      case "temporal":
        return {
          ...w,
          "stroke-dasharray": "5,5"
        };
      case "spatial":
        return {
          ...w,
          "stroke-dasharray": "10,2"
        };
      default:
        return w;
    }
  }, k = (C) => {
    var w;
    r((N) => (N == null ? void 0 : N.id) === C.id ? null : C), f(null), (w = e.onNodeSelect) == null || w.call(e, C);
  }, b = (C) => {
    var w;
    f((N) => (N == null ? void 0 : N.id) === C.id ? null : C), r(null), (w = e.onEdgeSelect) == null || w.call(e, C);
  }, x = (C, w) => {
    u && (C.fx = w.offsetX, C.fy = w.offsetY, u.alpha(0.3).restart());
  }, A = (C) => {
    C.preventDefault();
    const w = C.deltaY > 0 ? 0.9 : 1.1, N = c();
    m({
      ...N,
      k: Math.max(0.1, Math.min(3, N.k * w))
    });
  };
  wt(() => {
    $(), h && h.addEventListener("wheel", A, {
      passive: !1
    });
  }), Te(() => {
    u == null || u.stop(), h && h.removeEventListener("wheel", A);
  }), T(() => {
    var C, w, N;
    u && (i() !== u.nodes() || l() !== ((C = u.force("link")) == null ? void 0 : C.links())) && (u.nodes(i()), (N = (w = u.force("link")) == null ? void 0 : w.links) == null || N.call(w, l()), u.alpha(0.3).restart());
  });
  const V = (C) => {
    const w = p(C), N = C.x ?? 0, O = C.y ?? 0;
    switch (C.type) {
      case "model":
      case "reaction_system":
        return (() => {
          var P = Ti();
          return q(P, "x", N - 25), q(P, "y", O - 15), me(P, fe(w, {
            onClick: () => k(C),
            onMouseEnter: () => d(C.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(C, F)
          }), !0), P;
        })();
      case "data_loader":
        return (() => {
          var P = Ii();
          return q(P, "cx", N), q(P, "cy", O), me(P, fe(w, {
            onClick: () => k(C),
            onMouseEnter: () => d(C.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(C, F)
          }), !0), P;
        })();
      case "operator":
        return (() => {
          var P = Fi();
          return q(P, "points", `${N},${O - 20} ${N + 20},${O} ${N},${O + 20} ${N - 20},${O}`), me(P, fe(w, {
            onClick: () => k(C),
            onMouseEnter: () => d(C.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(C, F)
          }), !0), P;
        })();
      default:
        return (() => {
          var P = ji();
          return q(P, "cx", N), q(P, "cy", O), me(P, fe(w, {
            onClick: () => k(C),
            onMouseEnter: () => d(C.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(C, F)
          }), !0), P;
        })();
    }
  }, E = (C) => {
    if (!C.source.x || !C.source.y || !C.target.x || !C.target.y) return null;
    const w = R(C.data);
    return (() => {
      var N = Li();
      return me(N, fe({
        get x1() {
          return C.source.x;
        },
        get y1() {
          return C.source.y;
        },
        get x2() {
          return C.target.x;
        },
        get y2() {
          return C.target.y;
        }
      }, w, {
        onClick: () => b(C.data),
        onMouseEnter: () => d(C.data.id),
        onMouseLeave: () => d(null)
      }), !0), N;
    })();
  }, D = () => {
    const w = Math.min(150 / t(), 150 / n());
    return (() => {
      var N = Hi(), O = N.firstChild, P = O.firstChild, F = P.nextSibling;
      return a(O, v(L, {
        get each() {
          return i();
        },
        children: (H) => (() => {
          var j = Ui();
          return M((z) => {
            var J = (H.x ?? 0) * w, W = (H.y ?? 0) * w, G = p(H).fill;
            return J !== z.e && q(j, "cx", z.e = J), W !== z.t && q(j, "cy", z.t = W), G !== z.a && q(j, "fill", z.a = G), z;
          }, {
            e: void 0,
            t: void 0,
            a: void 0
          }), j;
        })()
      }), F), M((H) => {
        var j = -c().x * w, z = -c().y * w, J = t() * w / c().k, W = n() * w / c().k;
        return j !== H.e && q(F, "x", H.e = j), z !== H.t && q(F, "y", H.t = z), J !== H.a && q(F, "width", H.a = J), W !== H.o && q(F, "height", H.o = W), H;
      }, {
        e: void 0,
        t: void 0,
        a: void 0,
        o: void 0
      }), N;
    })();
  };
  return (() => {
    var C = Wi(), w = C.firstChild, N = w.firstChild, O = N.nextSibling, P = O.nextSibling, F = P.nextSibling, H = h;
    return typeof H == "function" ? Ie(H, w) : h = w, a(O, v(L, {
      get each() {
        return l();
      },
      children: (j) => E(j)
    })), a(P, v(L, {
      get each() {
        return i();
      },
      children: (j) => V(j)
    })), a(F, v(L, {
      get each() {
        return i();
      },
      children: (j) => (() => {
        var z = Yi();
        return a(z, () => j.name), M((J) => {
          var W = j.x ?? 0, G = (j.y ?? 0) + 40;
          return W !== J.e && q(z, "x", J.e = W), G !== J.t && q(z, "y", J.t = G), J;
        }, {
          e: void 0,
          t: void 0
        }), z;
      })()
    })), a(C, v(S, {
      get when() {
        return e.showMinimap !== !1;
      },
      get children() {
        return v(D, {});
      }
    }), null), a(C, v(S, {
      get when() {
        return s() || o();
      },
      get children() {
        var j = Bi(), z = j.firstChild;
        return a(j, v(S, {
          get when() {
            return s();
          },
          get children() {
            var J = zi(), W = J.firstChild, G = W.nextSibling;
            G.firstChild;
            var ee = G.nextSibling, ue = ee.firstChild;
            ue.firstChild;
            var he = ue.nextSibling;
            return he.firstChild, a(W, () => s().name), a(G, () => s().type, null), a(J, v(S, {
              get when() {
                return s().description;
              },
              get children() {
                var X = Xe();
                return a(X, () => s().description), X;
              }
            }), ee), a(ue, () => s().metadata.var_count, null), a(he, () => s().metadata.eq_count, null), a(ee, v(S, {
              get when() {
                return s().metadata.species_count > 0;
              },
              get children() {
                var X = Ki();
                return X.firstChild, a(X, () => s().metadata.species_count, null), X;
              }
            }), null), J;
          }
        }), z), a(j, v(S, {
          get when() {
            return o();
          },
          get children() {
            var J = Ji(), W = J.firstChild, G = W.nextSibling;
            G.firstChild;
            var ee = G.nextSibling, ue = ee.firstChild, he = ue.nextSibling;
            return he.nextSibling, a(W, () => o().label), a(G, () => o().type, null), a(ee, () => o().from, he), a(ee, () => o().to, null), a(J, v(S, {
              get when() {
                return o().description;
              },
              get children() {
                var X = Xe();
                return a(X, () => o().description), X;
              }
            }), null), J;
          }
        }), z), z.$$click = () => {
          r(null), f(null);
        }, j;
      }
    }), null), M((j) => {
      var z = t(), J = n(), W = `transform: translate(${c().x}px, ${c().y}px) scale(${c().k})`;
      return z !== j.e && q(w, "width", j.e = z), J !== j.t && q(w, "height", j.t = J), j.a = lt(w, W, j.a), j;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), C;
  })();
};
Y(["click"]);
var nr = /* @__PURE__ */ _("<span class=error-badge>"), ir = /* @__PURE__ */ _("<span class=warning-badge>"), rr = /* @__PURE__ */ _('<span class=success-badge title="No errors found">✓'), lr = /* @__PURE__ */ _("<div class=validation-success><span class=success-icon>✓</span>No validation errors found. The ESM file is valid."), sr = /* @__PURE__ */ _('<div class=error-section><h4 class="error-section-title error-title">Schema Errors (<!>)</h4><div class=error-list>'), ar = /* @__PURE__ */ _('<div class=error-section><h4 class="error-section-title error-title">Structural Errors (<!>)</h4><div class=error-list>'), or = /* @__PURE__ */ _('<div class=error-section><h4 class="error-section-title warning-title">Warnings (<!>)</h4><div class=error-list>'), cr = /* @__PURE__ */ _("<div class=validation-content>"), dr = /* @__PURE__ */ _("<div><div class=validation-header><h3 class=validation-title>Validation Results</h3><button class=collapse-toggle>"), Pe = /* @__PURE__ */ _("<div class=error-details>"), Qe = /* @__PURE__ */ _('<div class="error-item error-severity clickable"role=button tabindex=0><div class=error-header><span class=error-icon>🔴</span><span class=error-code></span><span class=error-path></span></div><div class=error-message>'), qe = /* @__PURE__ */ _("<div class=error-detail><strong>:</strong> "), ur = /* @__PURE__ */ _('<div class="error-item warning-severity clickable"role=button tabindex=0><div class=error-header><span class=error-icon>🟡</span><span class=error-code></span><span class=error-path></span></div><div class=error-message>');
function hr(e) {
  return "error";
}
const al = (e) => {
  const t = T(() => Ct(e.esmFile)), n = T(() => {
    const d = t(), c = [];
    return d.schema_errors.forEach((m) => {
      c.push({
        ...m,
        severity: "error",
        type: "schema"
      });
    }), d.structural_errors.forEach((m) => {
      c.push({
        ...m,
        severity: hr(),
        type: "structural"
      });
    }), c;
  }), i = T(() => {
    const d = n();
    return {
      errors: d.filter((c) => c.severity === "error"),
      warnings: d.filter((c) => c.severity === "warning")
    };
  }), l = T(() => i().errors.length), s = T(() => i().warnings.length), r = T(() => t().is_valid), o = (d) => {
    e.onErrorClick && e.onErrorClick(d.path);
  }, f = () => {
    e.onToggleCollapsed && e.onToggleCollapsed(!e.collapsed);
  }, g = () => {
    const d = ["validation-panel"];
    return e.collapsed && d.push("collapsed"), r() ? d.push("valid") : d.push("invalid"), e.class && d.push(e.class), d.join(" ");
  };
  return (() => {
    var d = dr(), c = d.firstChild, m = c.firstChild;
    m.firstChild;
    var h = m.nextSibling;
    return c.$$click = f, a(m, v(S, {
      get when() {
        return l() > 0;
      },
      get children() {
        var u = nr();
        return a(u, l), M(() => q(u, "title", `${l()} error(s)`)), u;
      }
    }), null), a(m, v(S, {
      get when() {
        return s() > 0;
      },
      get children() {
        var u = ir();
        return a(u, s), M(() => q(u, "title", `${s()} warning(s)`)), u;
      }
    }), null), a(m, v(S, {
      get when() {
        return r();
      },
      get children() {
        return rr();
      }
    }), null), a(h, () => e.collapsed ? "▶" : "▼"), a(d, v(S, {
      get when() {
        return !e.collapsed;
      },
      get children() {
        var u = cr();
        return a(u, v(S, {
          get when() {
            return r();
          },
          get children() {
            return lr();
          }
        }), null), a(u, v(S, {
          get when() {
            return !r();
          },
          get children() {
            return [v(S, {
              get when() {
                return i().errors.filter(($) => $.type === "schema").length > 0;
              },
              get children() {
                var $ = sr(), y = $.firstChild, p = y.firstChild, R = p.nextSibling;
                R.nextSibling;
                var k = y.nextSibling;
                return a(y, () => i().errors.filter((b) => b.type === "schema").length, R), a(k, v(L, {
                  get each() {
                    return i().errors.filter((b) => b.type === "schema");
                  },
                  children: (b) => (() => {
                    var x = Qe(), A = x.firstChild, V = A.firstChild, E = V.nextSibling, D = E.nextSibling, C = A.nextSibling;
                    return x.$$keydown = (w) => {
                      (w.key === "Enter" || w.key === " ") && (w.preventDefault(), o(b));
                    }, x.$$click = () => o(b), a(E, () => b.code), a(D, () => b.path || "$"), a(C, () => b.message), a(x, v(S, {
                      get when() {
                        return Object.keys(b.details).length > 0;
                      },
                      get children() {
                        var w = Pe();
                        return a(w, v(L, {
                          get each() {
                            return Object.entries(b.details);
                          },
                          children: ([N, O]) => (() => {
                            var P = qe(), F = P.firstChild, H = F.firstChild;
                            return F.nextSibling, a(F, N, H), a(P, () => String(O), null), P;
                          })()
                        })), w;
                      }
                    }), null), M(() => q(D, "title", `Path: ${b.path}`)), x;
                  })()
                })), $;
              }
            }), v(S, {
              get when() {
                return i().errors.filter(($) => $.type === "structural").length > 0;
              },
              get children() {
                var $ = ar(), y = $.firstChild, p = y.firstChild, R = p.nextSibling;
                R.nextSibling;
                var k = y.nextSibling;
                return a(y, () => i().errors.filter((b) => b.type === "structural").length, R), a(k, v(L, {
                  get each() {
                    return i().errors.filter((b) => b.type === "structural");
                  },
                  children: (b) => (() => {
                    var x = Qe(), A = x.firstChild, V = A.firstChild, E = V.nextSibling, D = E.nextSibling, C = A.nextSibling;
                    return x.$$keydown = (w) => {
                      (w.key === "Enter" || w.key === " ") && (w.preventDefault(), o(b));
                    }, x.$$click = () => o(b), a(E, () => b.code), a(D, () => b.path || "$"), a(C, () => b.message), a(x, v(S, {
                      get when() {
                        return Object.keys(b.details).length > 0;
                      },
                      get children() {
                        var w = Pe();
                        return a(w, v(L, {
                          get each() {
                            return Object.entries(b.details);
                          },
                          children: ([N, O]) => (() => {
                            var P = qe(), F = P.firstChild, H = F.firstChild;
                            return F.nextSibling, a(F, N, H), a(P, () => String(O), null), P;
                          })()
                        })), w;
                      }
                    }), null), M(() => q(D, "title", `Path: ${b.path}`)), x;
                  })()
                })), $;
              }
            }), v(S, {
              get when() {
                return s() > 0;
              },
              get children() {
                var $ = or(), y = $.firstChild, p = y.firstChild, R = p.nextSibling;
                R.nextSibling;
                var k = y.nextSibling;
                return a(y, s, R), a(k, v(L, {
                  get each() {
                    return i().warnings;
                  },
                  children: (b) => (() => {
                    var x = ur(), A = x.firstChild, V = A.firstChild, E = V.nextSibling, D = E.nextSibling, C = A.nextSibling;
                    return x.$$keydown = (w) => {
                      (w.key === "Enter" || w.key === " ") && (w.preventDefault(), o(b));
                    }, x.$$click = () => o(b), a(E, () => b.code), a(D, () => b.path || "$"), a(C, () => b.message), a(x, v(S, {
                      get when() {
                        return Object.keys(b.details).length > 0;
                      },
                      get children() {
                        var w = Pe();
                        return a(w, v(L, {
                          get each() {
                            return Object.entries(b.details);
                          },
                          children: ([N, O]) => (() => {
                            var P = qe(), F = P.firstChild, H = F.firstChild;
                            return F.nextSibling, a(F, N, H), a(P, () => String(O), null), P;
                          })()
                        })), w;
                      }
                    }), null), M(() => q(D, "title", `Path: ${b.path}`)), x;
                  })()
                })), $;
              }
            })];
          }
        }), null), u;
      }
    }), null), M((u) => {
      var $ = g(), y = e.collapsed ? "Expand validation panel" : "Collapse validation panel";
      return $ !== u.e && U(d, u.e = $), y !== u.t && q(h, "aria-label", u.t = y), u;
    }, {
      e: void 0,
      t: void 0
    }), d;
  })();
};
Y(["click", "keydown"]);
var fr = /* @__PURE__ */ _("<div class=info-item><strong>Title:</strong> "), gr = /* @__PURE__ */ _("<div class=info-item><strong>Description:</strong> "), mr = /* @__PURE__ */ _("<div class=info-item><strong>Authors:</strong> "), $r = /* @__PURE__ */ _("<div class=info-item><strong>Created:</strong> "), vr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Models (<!>) →</h4><div class=section-content>'), _r = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Reaction Systems (<!>) →</h4><div class=section-content>'), br = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Data Loaders (<!>) →</h4><div class=section-content>'), yr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Operators (<!>) →</h4><div class=section-content>'), xr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Coupling Rules (<!>) →</h4><div class=section-content>'), wr = /* @__PURE__ */ _("<div class=info-item><strong>Time:</strong>Start: <!>, End: "), Sr = /* @__PURE__ */ _("<div class=info-item><strong>Spatial:</strong> "), Cr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Domain Configuration →</h4><div class=section-content>'), Er = /* @__PURE__ */ _("<div class=info-item><strong>Tolerances:"), kr = /* @__PURE__ */ _("<div class=info-item><strong>Max Steps:</strong> "), pr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Solver Configuration →</h4><div class=section-content><div class=info-item><strong>Type:</strong> '), Ar = /* @__PURE__ */ _("<div class=empty-state><p>This ESM file appears to be empty or contains no major components."), Pr = /* @__PURE__ */ _("<div class=summary-content><div class=summary-section><h4 class=section-title>Format Information</h4><div class=section-content><div class=info-item><strong>Version:</strong> "), qr = /* @__PURE__ */ _("<div><div class=summary-header><h3 class=summary-title>File Summary</h3><button class=collapse-toggle>"), Ze = /* @__PURE__ */ _('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong></strong> →</div><div class=system-summary>'), et = /* @__PURE__ */ _('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong></strong> →</div><div class=system-summary>Type: '), Rr = /* @__PURE__ */ _('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong>Rule </strong> →</div><div class=system-summary>');
function ye(e) {
  return e ? Object.keys(e).length : 0;
}
function Dr(e) {
  var t, n;
  switch (e.type) {
    case "operator_compose":
      return `Compose: ${((t = e.systems) == null ? void 0 : t.join(", ")) || "N/A"}`;
    case "couple2":
      return `Couple2: ${((n = e.systems) == null ? void 0 : n.join(", ")) || "N/A"}`;
    case "operator_apply":
      return `Apply operator: ${e.operator || "N/A"}`;
    default:
      return "Unknown coupling type";
  }
}
function tt(e) {
  const t = [];
  return "variables" in e && e.variables && t.push(`${Object.keys(e.variables).length} variables`), "species" in e && e.species && t.push(`${Object.keys(e.species).length} species`), "parameters" in e && e.parameters && t.push(`${Object.keys(e.parameters).length} parameters`), "equations" in e && e.equations && t.push(`${e.equations.length} equations`), "reactions" in e && e.reactions && t.push(`${e.reactions.length} reactions`), "subsystems" in e && e.subsystems && t.push(`${Object.keys(e.subsystems).length} subsystems`), t.join(", ") || "Empty system";
}
const Nr = (e) => {
  const t = T(() => ye(e.esmFile.models)), n = T(() => ye(e.esmFile.reaction_systems)), i = T(() => ye(e.esmFile.data_loaders)), l = T(() => ye(e.esmFile.operators)), s = T(() => {
    var g;
    return ((g = e.esmFile.coupling) == null ? void 0 : g.length) || 0;
  }), r = (g, d) => {
    e.onSectionClick && e.onSectionClick(g, d);
  }, o = () => {
    e.onToggleCollapsed && e.onToggleCollapsed(!e.collapsed);
  }, f = () => {
    const g = ["file-summary"];
    return e.collapsed && g.push("collapsed"), e.class && g.push(e.class), g.join(" ");
  };
  return (() => {
    var g = qr(), d = g.firstChild, c = d.firstChild, m = c.nextSibling;
    return d.$$click = o, a(m, () => e.collapsed ? "▶" : "▼"), a(g, v(S, {
      get when() {
        return !e.collapsed;
      },
      get children() {
        var h = Pr(), u = h.firstChild, $ = u.firstChild, y = $.nextSibling, p = y.firstChild, R = p.firstChild;
        return R.nextSibling, a(p, () => e.esmFile.esm_version || "Not specified", null), a(y, v(S, {
          get when() {
            return e.esmFile.metadata;
          },
          get children() {
            return [(() => {
              var k = fr(), b = k.firstChild;
              return b.nextSibling, a(k, () => e.esmFile.metadata.title || "Untitled", null), k;
            })(), v(S, {
              get when() {
                return e.esmFile.metadata.description;
              },
              get children() {
                var k = gr(), b = k.firstChild;
                return b.nextSibling, a(k, () => e.esmFile.metadata.description, null), k;
              }
            }), v(S, {
              get when() {
                return B(() => !!e.esmFile.metadata.authors)() && e.esmFile.metadata.authors.length > 0;
              },
              get children() {
                var k = mr(), b = k.firstChild;
                return b.nextSibling, a(k, () => e.esmFile.metadata.authors.join(", "), null), k;
              }
            }), v(S, {
              get when() {
                return e.esmFile.metadata.created_date;
              },
              get children() {
                var k = $r(), b = k.firstChild;
                return b.nextSibling, a(k, () => e.esmFile.metadata.created_date, null), k;
              }
            })];
          }
        }), null), a(h, v(S, {
          get when() {
            return t() > 0;
          },
          get children() {
            var k = vr(), b = k.firstChild, x = b.firstChild, A = x.nextSibling;
            A.nextSibling;
            var V = b.nextSibling;
            return b.$$keydown = (E) => {
              (E.key === "Enter" || E.key === " ") && (E.preventDefault(), r("models"));
            }, b.$$click = () => r("models"), a(b, t, A), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.models || {});
              },
              children: ([E, D]) => (() => {
                var C = Ze(), w = C.firstChild, N = w.firstChild, O = w.nextSibling;
                return w.$$keydown = (P) => {
                  (P.key === "Enter" || P.key === " ") && (P.preventDefault(), r("models", E));
                }, w.$$click = () => r("models", E), a(N, E), a(O, () => tt(D)), C;
              })()
            })), k;
          }
        }), null), a(h, v(S, {
          get when() {
            return n() > 0;
          },
          get children() {
            var k = _r(), b = k.firstChild, x = b.firstChild, A = x.nextSibling;
            A.nextSibling;
            var V = b.nextSibling;
            return b.$$keydown = (E) => {
              (E.key === "Enter" || E.key === " ") && (E.preventDefault(), r("reaction_systems"));
            }, b.$$click = () => r("reaction_systems"), a(b, n, A), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.reaction_systems || {});
              },
              children: ([E, D]) => (() => {
                var C = Ze(), w = C.firstChild, N = w.firstChild, O = w.nextSibling;
                return w.$$keydown = (P) => {
                  (P.key === "Enter" || P.key === " ") && (P.preventDefault(), r("reaction_systems", E));
                }, w.$$click = () => r("reaction_systems", E), a(N, E), a(O, () => tt(D)), C;
              })()
            })), k;
          }
        }), null), a(h, v(S, {
          get when() {
            return i() > 0;
          },
          get children() {
            var k = br(), b = k.firstChild, x = b.firstChild, A = x.nextSibling;
            A.nextSibling;
            var V = b.nextSibling;
            return b.$$keydown = (E) => {
              (E.key === "Enter" || E.key === " ") && (E.preventDefault(), r("data_loaders"));
            }, b.$$click = () => r("data_loaders"), a(b, i, A), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.data_loaders || {});
              },
              children: ([E, D]) => (() => {
                var C = et(), w = C.firstChild, N = w.firstChild, O = w.nextSibling;
                return O.firstChild, w.$$keydown = (P) => {
                  (P.key === "Enter" || P.key === " ") && (P.preventDefault(), r("data_loaders", E));
                }, w.$$click = () => r("data_loaders", E), a(N, E), a(O, () => D.type || "Unknown", null), a(O, (() => {
                  var P = B(() => !!D.source);
                  return () => P() && ` | Source: ${D.source}`;
                })(), null), a(O, (() => {
                  var P = B(() => !!D.description);
                  return () => P() && ` | ${D.description}`;
                })(), null), C;
              })()
            })), k;
          }
        }), null), a(h, v(S, {
          get when() {
            return l() > 0;
          },
          get children() {
            var k = yr(), b = k.firstChild, x = b.firstChild, A = x.nextSibling;
            A.nextSibling;
            var V = b.nextSibling;
            return b.$$keydown = (E) => {
              (E.key === "Enter" || E.key === " ") && (E.preventDefault(), r("operators"));
            }, b.$$click = () => r("operators"), a(b, l, A), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.operators || {});
              },
              children: ([E, D]) => (() => {
                var C = et(), w = C.firstChild, N = w.firstChild, O = w.nextSibling;
                return O.firstChild, w.$$keydown = (P) => {
                  (P.key === "Enter" || P.key === " ") && (P.preventDefault(), r("operators", E));
                }, w.$$click = () => r("operators", E), a(N, E), a(O, () => D.type || "Unknown", null), a(O, (() => {
                  var P = B(() => !!D.description);
                  return () => P() && ` | ${D.description}`;
                })(), null), C;
              })()
            })), k;
          }
        }), null), a(h, v(S, {
          get when() {
            return s() > 0;
          },
          get children() {
            var k = xr(), b = k.firstChild, x = b.firstChild, A = x.nextSibling;
            A.nextSibling;
            var V = b.nextSibling;
            return b.$$keydown = (E) => {
              (E.key === "Enter" || E.key === " ") && (E.preventDefault(), r("coupling"));
            }, b.$$click = () => r("coupling"), a(b, s, A), a(V, v(L, {
              get each() {
                return e.esmFile.coupling || [];
              },
              children: (E, D) => (() => {
                var C = Rr(), w = C.firstChild, N = w.firstChild;
                N.firstChild;
                var O = w.nextSibling;
                return w.$$keydown = (P) => {
                  (P.key === "Enter" || P.key === " ") && (P.preventDefault(), r("coupling", D().toString()));
                }, w.$$click = () => r("coupling", D().toString()), a(N, () => D() + 1, null), a(O, () => Dr(E)), C;
              })()
            })), k;
          }
        }), null), a(h, v(S, {
          get when() {
            return e.esmFile.domain;
          },
          get children() {
            var k = Cr(), b = k.firstChild, x = b.nextSibling;
            return b.$$keydown = (A) => {
              (A.key === "Enter" || A.key === " ") && (A.preventDefault(), r("domain"));
            }, b.$$click = () => r("domain"), a(x, v(S, {
              get when() {
                return e.esmFile.domain.time;
              },
              get children() {
                var A = wr(), V = A.firstChild, E = V.nextSibling, D = E.nextSibling;
                return D.nextSibling, a(A, () => e.esmFile.domain.time.start ?? "N/A", D), a(A, () => e.esmFile.domain.time.end ?? "N/A", null), a(A, (() => {
                  var C = B(() => !!e.esmFile.domain.time.step);
                  return () => C() && `, Step: ${e.esmFile.domain.time.step}`;
                })(), null), A;
              }
            }), null), a(x, v(S, {
              get when() {
                return e.esmFile.domain.spatial;
              },
              get children() {
                var A = Sr(), V = A.firstChild;
                return V.nextSibling, a(A, () => e.esmFile.domain.spatial.type || "Unknown type", null), A;
              }
            }), null), k;
          }
        }), null), a(h, v(S, {
          get when() {
            return e.esmFile.solver;
          },
          get children() {
            var k = pr(), b = k.firstChild, x = b.nextSibling, A = x.firstChild, V = A.firstChild;
            return V.nextSibling, b.$$keydown = (E) => {
              (E.key === "Enter" || E.key === " ") && (E.preventDefault(), r("solver"));
            }, b.$$click = () => r("solver"), a(A, () => e.esmFile.solver.type || "Not specified", null), a(x, v(S, {
              get when() {
                return e.esmFile.solver.tolerances;
              },
              get children() {
                var E = Er();
                return E.firstChild, a(E, (() => {
                  var D = B(() => !!e.esmFile.solver.tolerances.absolute);
                  return () => D() && ` Absolute: ${e.esmFile.solver.tolerances.absolute}`;
                })(), null), a(E, (() => {
                  var D = B(() => !!e.esmFile.solver.tolerances.relative);
                  return () => D() && ` Relative: ${e.esmFile.solver.tolerances.relative}`;
                })(), null), E;
              }
            }), null), a(x, v(S, {
              get when() {
                return e.esmFile.solver.max_steps;
              },
              get children() {
                var E = kr(), D = E.firstChild;
                return D.nextSibling, a(E, () => e.esmFile.solver.max_steps, null), E;
              }
            }), null), k;
          }
        }), null), a(h, v(S, {
          get when() {
            return B(() => t() === 0 && n() === 0 && i() === 0)() && s() === 0;
          },
          get children() {
            return Ar();
          }
        }), null), h;
      }
    }), null), M((h) => {
      var u = f(), $ = e.collapsed ? "Expand file summary" : "Collapse file summary";
      return u !== h.e && U(g, h.e = u), $ !== h.t && q(m, "aria-label", h.t = $), h;
    }, {
      e: void 0,
      t: void 0
    }), g;
  })();
};
Y(["click", "keydown"]);
var Mr = /* @__PURE__ */ _("<span role=math aria-label=fraction><span class=esm-fraction-numerator></span><span class=esm-fraction-bar></span><span class=esm-fraction-denominator>");
const ol = (e) => {
  const t = () => {
    const n = ["esm-fraction"];
    return e.inline !== !1 && n.push("esm-fraction-inline"), e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = Mr(), i = n.firstChild, l = i.nextSibling, s = l.nextSibling;
    return K(n, "mouseleave", e.onMouseLeave), K(n, "mouseenter", e.onMouseEnter), K(n, "click", e.onClick, !0), a(i, () => e.numerator), a(s, () => e.denominator), M(() => U(n, t())), n;
  })();
};
Y(["click"]);
var Vr = /* @__PURE__ */ _("<span role=math aria-label=exponentiation><span class=esm-superscript-base></span><span class=esm-superscript-exponent>");
const cl = (e) => {
  const t = () => {
    const n = ["esm-superscript"];
    return e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = Vr(), i = n.firstChild, l = i.nextSibling;
    return K(n, "mouseleave", e.onMouseLeave), K(n, "mouseenter", e.onMouseEnter), K(n, "click", e.onClick, !0), a(i, () => e.base), a(l, () => e.exponent), M(() => U(n, t())), n;
  })();
};
Y(["click"]);
var Or = /* @__PURE__ */ _("<span role=math><span class=esm-subscript-base></span><span class=esm-subscript-content>");
const dl = (e) => {
  const t = () => {
    const n = ["esm-subscript"];
    return e.chemical && n.push("esm-subscript-chemical"), e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = Or(), i = n.firstChild, l = i.nextSibling;
    return K(n, "mouseleave", e.onMouseLeave), K(n, "mouseenter", e.onMouseEnter), K(n, "click", e.onClick, !0), a(i, () => e.base), a(l, () => e.subscript), M((s) => {
      var r = t(), o = e.chemical ? "chemical subscript" : "subscript";
      return r !== s.e && U(n, s.e = r), o !== s.t && q(n, "aria-label", s.t = o), s;
    }, {
      e: void 0,
      t: void 0
    }), n;
  })();
};
Y(["click"]);
var Tr = /* @__PURE__ */ _("<span role=math><span class=esm-radical-symbol>√</span><span class=esm-radical-content>"), Ir = /* @__PURE__ */ _("<span class=esm-radical-index>");
const ul = (e) => {
  const t = () => {
    const n = ["esm-radical"];
    return e.index && n.push("esm-radical-with-index"), e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = Tr(), i = n.firstChild, l = i.nextSibling;
    return K(n, "mouseleave", e.onMouseLeave), K(n, "mouseenter", e.onMouseEnter), K(n, "click", e.onClick, !0), a(n, (() => {
      var s = B(() => !!e.index);
      return () => s() && (() => {
        var r = Ir();
        return a(r, () => e.index), r;
      })();
    })(), i), a(l, () => e.content), M((s) => {
      var r = t(), o = e.index ? "nth root" : "square root";
      return r !== s.e && U(n, s.e = r), o !== s.t && q(n, "aria-label", s.t = o), s;
    }, {
      e: void 0,
      t: void 0
    }), n;
  })();
};
Y(["click"]);
var Fr = /* @__PURE__ */ _("<span role=math><span class=esm-delimiters-left></span><span class=esm-delimiters-content></span><span class=esm-delimiters-right>");
const hl = (e) => {
  let t;
  const n = () => e.type || "parentheses", i = () => e.autoSize !== !1, l = () => e.size, s = () => {
    const g = ["esm-delimiters", `esm-delimiters-${n()}`];
    return i() && g.push("esm-delimiters-auto"), l() && g.push(`esm-delimiters-${l()}`), e.class && g.push(e.class), g.join(" ");
  }, r = () => {
    switch (n()) {
      case "parentheses":
        return {
          left: "(",
          right: ")"
        };
      case "brackets":
        return {
          left: "[",
          right: "]"
        };
      case "braces":
        return {
          left: "{",
          right: "}"
        };
      case "absolute":
        return {
          left: "|",
          right: "|"
        };
      case "angle":
        return {
          left: "⟨",
          right: "⟩"
        };
      default:
        return {
          left: "(",
          right: ")"
        };
    }
  };
  rt(() => {
    if (i() && t) {
      const g = () => {
        const m = t == null ? void 0 : t.querySelector(".esm-delimiters-content");
        if (m) {
          const h = m.offsetHeight, u = t == null ? void 0 : t.querySelector(".esm-delimiters-left"), $ = t == null ? void 0 : t.querySelector(".esm-delimiters-right");
          if (u && $) {
            let y = 1;
            h > 20 && (y = Math.min(h / 16, 4));
            const p = `scaleY(${y})`;
            u.style.transform = p, $.style.transform = p;
          }
        }
      };
      setTimeout(g, 0);
      const d = new ResizeObserver(g), c = t == null ? void 0 : t.querySelector(".esm-delimiters-content");
      return c && d.observe(c), () => d.disconnect();
    }
  });
  const {
    left: o,
    right: f
  } = r();
  return (() => {
    var g = Fr(), d = g.firstChild, c = d.nextSibling, m = c.nextSibling;
    K(g, "mouseleave", e.onMouseLeave), K(g, "mouseenter", e.onMouseEnter), K(g, "click", e.onClick, !0);
    var h = t;
    return typeof h == "function" ? Ie(h, g) : t = g, a(d, o), a(c, () => e.content), a(m, f), M((u) => {
      var $ = s(), y = `${n()} delimiters`;
      return $ !== u.e && U(g, u.e = $), y !== u.t && q(g, "aria-label", u.t = y), u;
    }, {
      e: void 0,
      t: void 0
    }), g;
  })();
};
Y(["click"]);
class jr {
  constructor() {
    this.parent = /* @__PURE__ */ new Map(), this.rank = /* @__PURE__ */ new Map();
  }
  // Make a new set with the given variable
  makeSet(t) {
    this.parent.has(t) || (this.parent.set(t, t), this.rank.set(t, 0));
  }
  // Find the root of the set containing the variable
  find(t) {
    this.parent.has(t) || this.makeSet(t);
    const n = this.parent.get(t);
    if (n !== t) {
      const i = this.find(n);
      return this.parent.set(t, i), i;
    }
    return t;
  }
  // Union two sets by rank
  union(t, n) {
    const i = this.find(t), l = this.find(n);
    if (i === l) return;
    const s = this.rank.get(i) || 0, r = this.rank.get(l) || 0;
    s < r ? this.parent.set(i, l) : s > r ? this.parent.set(l, i) : (this.parent.set(l, i), this.rank.set(i, s + 1));
  }
  // Get all variables in the same equivalence class
  getEquivalenceClass(t) {
    const n = this.find(t), i = /* @__PURE__ */ new Set();
    for (const [l, s] of this.parent.entries())
      this.find(l) === n && i.add(l);
    return i;
  }
  // Get all equivalence classes
  getAllEquivalenceClasses() {
    const t = /* @__PURE__ */ new Map();
    for (const n of this.parent.keys()) {
      const i = this.find(n);
      t.has(i) || t.set(i, this.getEquivalenceClass(n));
    }
    return t;
  }
}
function dt(e) {
  const t = new jr();
  if (e.couplings)
    for (const n of e.couplings)
      Lr(n, t);
  return t.getAllEquivalenceClasses();
}
function Lr(e, t) {
  var n;
  switch (e.type) {
    case "variable_map":
      t.union(e.from, e.to);
      break;
    case "operator_compose":
      if (e.translate)
        for (const [i, l] of Object.entries(e.translate)) {
          const s = typeof l == "string" ? l : l.var;
          t.union(i, s);
        }
      break;
    case "couple2":
      if ((n = e.connector) != null && n.equations)
        for (const i of e.connector.equations)
          t.union(i.from, i.to);
      break;
  }
}
function ut(e, t, n = "model") {
  const i = [];
  return n === "equation" ? (i.push(e), i) : (i.push(e), !e.includes(".") && t && n !== "file" && i.push(`${t}.${e}`), i);
}
const ht = Ve();
function fl(e) {
  const [t, n] = I(null), i = T(() => dt(e.file)), l = T(() => {
    const r = t();
    if (!r) return /* @__PURE__ */ new Set();
    const o = i(), f = e.scopingMode || "model", g = ut(r, e.currentModelContext, f), d = /* @__PURE__ */ new Set();
    for (const c of g)
      for (const [m, h] of o.entries())
        if (h.has(c)) {
          for (const u of h)
            Ce(u, r, f, e.currentModelContext) && d.add(u);
          break;
        }
    for (const c of g)
      Ce(c, r, f, e.currentModelContext) && d.add(c);
    return d;
  }), s = {
    hoveredVar: t,
    setHoveredVar: n,
    highlightedVars: l,
    equivalences: i
  };
  return v(ht.Provider, {
    value: s,
    get children() {
      return e.children;
    }
  });
}
function gl() {
  const e = Oe(ht);
  if (!e)
    throw new Error("useHighlightContext must be used within a HighlightProvider");
  return e;
}
function Ce(e, t, n, i) {
  switch (n) {
    case "equation":
      return e === t;
    case "model":
      return !0;
    case "file":
      return !0;
  }
}
function ml(e, t) {
  return t.has(e);
}
function $l(e, t, n = "model") {
  const [i, l] = I(null), s = T(() => dt(e)), r = T(() => {
    const o = i();
    if (!o) return /* @__PURE__ */ new Set();
    const f = s(), g = ut(o, t, n), d = /* @__PURE__ */ new Set();
    for (const c of g)
      for (const [, m] of f.entries())
        if (m.has(c)) {
          for (const h of m)
            Ce(h, o, n) && d.add(h);
          break;
        }
    for (const c of g)
      Ce(c, o, n) && d.add(c);
    return d;
  });
  return {
    hoveredVar: i,
    setHoveredVar: l,
    highlightedVars: r,
    equivalences: s
  };
}
const ft = Ve();
function Fe(e, t) {
  let n = e;
  for (const i of t) {
    if (n == null) return null;
    if (i === "args" && typeof n == "object" && "args" in n)
      n = n.args;
    else if (typeof i == "number" && Array.isArray(n))
      n = n[i];
    else
      return null;
  }
  return n;
}
function gt(e, t, n) {
  if (t.length === 0)
    return n;
  let i = JSON.parse(JSON.stringify(e)), l = i;
  for (let r = 0; r < t.length - 1; r++) {
    const o = t[r];
    if (o === "args" && typeof l == "object" && "args" in l)
      l = l.args;
    else if (typeof o == "number" && Array.isArray(l))
      l = l[o];
    else
      throw new Error(`Invalid path segment: ${o}`);
  }
  const s = t[t.length - 1];
  if (typeof s == "number" && Array.isArray(l))
    l[s] = n;
  else
    throw new Error(`Invalid final path segment: ${s}`);
  return i;
}
function mt(e, t) {
  if (t.length === 0)
    return {
      type: "root"
    };
  const n = t.slice(0, -2), i = t[t.length - 1];
  if (typeof i != "number")
    return {
      type: "root"
    };
  const l = Fe(e, n);
  return l && typeof l == "object" && "op" in l ? {
    type: "operator",
    operator: l.op,
    argIndex: i
  } : {
    type: "root"
  };
}
function $t(e) {
  const t = [];
  return typeof e == "number" ? t.push("Edit Value", "Convert to Variable", "Wrap in Operator") : typeof e == "string" ? t.push("Edit Variable", "Convert to Number", "Wrap in Operator") : typeof e == "object" && e !== null && "op" in e && t.push("Change Operator", "Add Argument", "Remove Argument", "Unwrap"), t;
}
function Hr(e) {
  if (!e) return [];
  const t = /* @__PURE__ */ new Set();
  if (e.models)
    for (const n of e.models) {
      if (n.variables)
        for (const i of n.variables)
          t.add(i.name);
      if (n.parameters)
        for (const i of n.parameters)
          t.add(i.name);
      if (n.species)
        for (const i of n.species)
          t.add(i.name);
    }
  return Array.from(t).sort();
}
function vl(e) {
  const [t, n] = I(null), [i, l] = I(!1), [s, r] = I(""), o = (u) => {
    const $ = t();
    return !$ || $.length !== u.length ? !1 : $.every((y, p) => y === u[p]);
  }, f = T(() => {
    const u = t();
    if (!u) return null;
    const $ = e.rootExpression(), y = Fe($, u);
    if (!y) return null;
    const p = typeof y == "number" ? "number" : typeof y == "string" ? "variable" : "operator", R = typeof y == "object" && "op" in y ? y.op : y;
    return {
      type: p,
      value: R,
      parentContext: mt($, u),
      availableActions: $t(y),
      path: [...u],
      expression: y
    };
  }), g = (u, $) => {
    const y = e.rootExpression(), p = gt(y, u, $);
    e.onRootReplace(p);
  }, d = () => {
    const u = f();
    u && (u.type === "number" || u.type === "variable") && (r(String(u.value)), l(!0));
  }, c = () => {
    l(!1), r("");
  }, h = {
    selectedPath: t,
    setSelectedPath: n,
    isSelected: o,
    selectedNodeDetails: f,
    onReplace: g,
    startInlineEdit: d,
    cancelInlineEdit: c,
    confirmInlineEdit: (u) => {
      const $ = t(), y = f();
      if (!$ || !y) return;
      let p;
      if (y.type === "number") {
        const R = parseFloat(u);
        if (isNaN(R)) return;
        p = R;
      } else if (y.type === "variable") {
        if (!u.trim()) return;
        p = u.trim();
      } else
        return;
      g($, p), c();
    },
    isInlineEditing: i,
    inlineEditValue: s,
    setInlineEditValue: r
  };
  return v(ft.Provider, {
    value: h,
    get children() {
      return e.children;
    }
  });
}
function _l() {
  const e = Oe(ft);
  if (!e)
    throw new Error("useSelectionContext must be used within a SelectionProvider");
  return e;
}
function bl(e, t) {
  const [n, i] = I(null), [l, s] = I(!1), [r, o] = I(""), f = (c) => {
    const m = n();
    return !m || m.length !== c.length ? !1 : m.every((h, u) => h === c[u]);
  }, g = T(() => {
    const c = n();
    if (!c) return null;
    const m = e(), h = Fe(m, c);
    if (!h) return null;
    const u = typeof h == "number" ? "number" : typeof h == "string" ? "variable" : "operator", $ = typeof h == "object" && "op" in h ? h.op : h;
    return {
      type: u,
      value: $,
      parentContext: mt(m, c),
      availableActions: $t(h),
      path: [...c],
      expression: h
    };
  }), d = (c, m) => {
    const h = e(), u = gt(h, c, m);
    t(u);
  };
  return {
    selectedPath: n,
    setSelectedPath: i,
    isSelected: f,
    selectedNodeDetails: g,
    onReplace: d,
    startInlineEdit: () => {
      const c = g();
      c && (c.type === "number" || c.type === "variable") && (o(String(c.value)), s(!0));
    },
    cancelInlineEdit: () => {
      s(!1), o("");
    },
    confirmInlineEdit: (c) => {
      const m = n(), h = g();
      if (!m || !h) return;
      let u;
      if (h.type === "number") {
        const $ = parseFloat(c);
        if (isNaN($)) return;
        u = $;
      } else if (h.type === "variable") {
        if (!c.trim()) return;
        u = c.trim();
      } else
        return;
      d(m, u), s(!1), o("");
    },
    isInlineEditing: l,
    inlineEditValue: r,
    setInlineEditValue: o
  };
}
function yl(e, t = "") {
  const n = Hr(e);
  if (!t) return n;
  const i = t.toLowerCase();
  return n.filter((l) => l.toLowerCase().includes(i));
}
function xl(e, t) {
  return e.length !== t.length ? !1 : e.every((n, i) => n === t[i]);
}
function wl(e) {
  return e.join(".");
}
function Sl(e) {
  return e ? e.split(".").map((t) => {
    const n = parseInt(t, 10);
    return isNaN(n) ? t : n;
  }) : [];
}
function re(e) {
  return JSON.parse(JSON.stringify(e));
}
function Ur(e, t, n = {}) {
  const {
    maxEntries: i = 100,
    debounceMs: l = 500,
    registerKeyboardShortcuts: s = !0
  } = n, [r, o] = I([]), [f, g] = I([]);
  let d = !1, c = null, m = null;
  function h(b) {
    d || (c !== null && clearTimeout(c), c = window.setTimeout(() => {
      const x = e();
      if (!x || m && JSON.stringify(x) === JSON.stringify(m))
        return;
      const A = {
        state: re(x),
        timestamp: Date.now(),
        description: b
      };
      o((V) => {
        const E = [...V, A];
        return E.length > i && E.splice(0, E.length - i), E;
      }), g([]), m = re(x), c = null;
    }, l));
  }
  function u() {
    const b = r();
    if (b.length === 0) return;
    const x = e();
    if (!x) return;
    const A = {
      state: re(x),
      timestamp: Date.now(),
      description: "Current state"
    };
    g((E) => [...E, A]);
    const V = b[b.length - 1];
    o((E) => E.slice(0, -1)), d = !0, t(re(V.state)), d = !1;
  }
  function $() {
    const b = f();
    if (b.length === 0) return;
    const x = e();
    if (!x) return;
    const A = {
      state: re(x),
      timestamp: Date.now(),
      description: "Redo checkpoint"
    };
    o((E) => [...E, A]);
    const V = b[b.length - 1];
    g((E) => E.slice(0, -1)), d = !0, t(re(V.state)), d = !1;
  }
  function y() {
    return r().length > 0;
  }
  function p() {
    return f().length > 0;
  }
  function R() {
    c !== null && (clearTimeout(c), c = null), o([]), g([]);
  }
  function k() {
    return r().length + f().length;
  }
  if (rt(() => {
    e() && !d && h("File change");
  }), s && typeof window < "u") {
    const b = (x) => {
      (x.ctrlKey || x.metaKey) && (x.key === "z" && !x.shiftKey ? (x.preventDefault(), u()) : (x.key === "y" || x.key === "z" && x.shiftKey) && (x.preventDefault(), $()));
    };
    document.addEventListener("keydown", b), Te(() => {
      document.removeEventListener("keydown", b), c !== null && clearTimeout(c);
    });
  }
  return {
    undo: u,
    redo: $,
    canUndo: y,
    canRedo: p,
    clear: R,
    historyLength: k,
    capture: h
  };
}
function Cl(e, t, n, i) {
  const l = (s) => {
    (s.ctrlKey || s.metaKey) && (s.key === "z" && !s.shiftKey && n() ? (s.preventDefault(), e()) : (s.key === "y" || s.key === "z" && s.shiftKey) && i() && (s.preventDefault(), t()));
  };
  return typeof window < "u" && (document.addEventListener("keydown", l), Te(() => {
    document.removeEventListener("keydown", l);
  })), l;
}
const Ee = Symbol("store-raw"), se = Symbol("store-node"), Q = Symbol("store-has"), vt = Symbol("store-self");
function _t(e) {
  let t = e[te];
  if (!t && (Object.defineProperty(e, te, {
    value: t = new Proxy(e, Jr)
  }), !Array.isArray(e))) {
    const n = Object.keys(e), i = Object.getOwnPropertyDescriptors(e);
    for (let l = 0, s = n.length; l < s; l++) {
      const r = n[l];
      i[r].get && Object.defineProperty(e, r, {
        enumerable: i[r].enumerable,
        get: i[r].get.bind(t)
      });
    }
  }
  return t;
}
function ae(e) {
  let t;
  return e != null && typeof e == "object" && (e[te] || !(t = Object.getPrototypeOf(e)) || t === Object.prototype || Array.isArray(e));
}
function oe(e, t = /* @__PURE__ */ new Set()) {
  let n, i, l, s;
  if (n = e != null && e[Ee]) return n;
  if (!ae(e) || t.has(e)) return e;
  if (Array.isArray(e)) {
    Object.isFrozen(e) ? e = e.slice(0) : t.add(e);
    for (let r = 0, o = e.length; r < o; r++)
      l = e[r], (i = oe(l, t)) !== l && (e[r] = i);
  } else {
    Object.isFrozen(e) ? e = Object.assign({}, e) : t.add(e);
    const r = Object.keys(e), o = Object.getOwnPropertyDescriptors(e);
    for (let f = 0, g = r.length; f < g; f++)
      s = r[f], !o[s].get && (l = e[s], (i = oe(l, t)) !== l && (e[s] = i));
  }
  return e;
}
function ke(e, t) {
  let n = e[t];
  return n || Object.defineProperty(e, t, {
    value: n = /* @__PURE__ */ Object.create(null)
  }), n;
}
function _e(e, t, n) {
  if (e[t]) return e[t];
  const [i, l] = I(n, {
    equals: !1,
    internal: !0
  });
  return i.$ = l, e[t] = i;
}
function Kr(e, t) {
  const n = Reflect.getOwnPropertyDescriptor(e, t);
  return !n || n.get || !n.configurable || t === te || t === se || (delete n.value, delete n.writable, n.get = () => e[te][t]), n;
}
function bt(e) {
  De() && _e(ke(e, se), vt)();
}
function zr(e) {
  return bt(e), Reflect.ownKeys(e);
}
const Jr = {
  get(e, t, n) {
    if (t === Ee) return e;
    if (t === te) return n;
    if (t === je)
      return bt(e), n;
    const i = ke(e, se), l = i[t];
    let s = l ? l() : e[t];
    if (t === se || t === Q || t === "__proto__") return s;
    if (!l) {
      const r = Object.getOwnPropertyDescriptor(e, t);
      De() && (typeof s != "function" || e.hasOwnProperty(t)) && !(r && r.get) && (s = _e(i, t, s)());
    }
    return ae(s) ? _t(s) : s;
  },
  has(e, t) {
    return t === Ee || t === te || t === je || t === se || t === Q || t === "__proto__" ? !0 : (De() && _e(ke(e, Q), t)(), t in e);
  },
  set() {
    return !0;
  },
  deleteProperty() {
    return !0;
  },
  ownKeys: zr,
  getOwnPropertyDescriptor: Kr
};
function ce(e, t, n, i = !1) {
  if (!i && e[t] === n) return;
  const l = e[t], s = e.length;
  n === void 0 ? (delete e[t], e[Q] && e[Q][t] && l !== void 0 && e[Q][t].$()) : (e[t] = n, e[Q] && e[Q][t] && l === void 0 && e[Q][t].$());
  let r = ke(e, se), o;
  if ((o = _e(r, t, l)) && o.$(() => n), Array.isArray(e) && e.length !== s) {
    for (let f = e.length; f < s; f++) (o = r[f]) && o.$();
    (o = _e(r, "length", s)) && o.$(e.length);
  }
  (o = r[vt]) && o.$();
}
function yt(e, t) {
  const n = Object.keys(t);
  for (let i = 0; i < n.length; i += 1) {
    const l = n[i];
    ce(e, l, t[l]);
  }
}
function Br(e, t) {
  if (typeof t == "function" && (t = t(e)), t = oe(t), Array.isArray(t)) {
    if (e === t) return;
    let n = 0, i = t.length;
    for (; n < i; n++) {
      const l = t[n];
      e[n] !== l && ce(e, n, l);
    }
    ce(e, "length", i);
  } else yt(e, t);
}
function $e(e, t, n = []) {
  let i, l = e;
  if (t.length > 1) {
    i = t.shift();
    const r = typeof i, o = Array.isArray(e);
    if (Array.isArray(i)) {
      for (let f = 0; f < i.length; f++)
        $e(e, [i[f]].concat(t), n);
      return;
    } else if (o && r === "function") {
      for (let f = 0; f < e.length; f++)
        i(e[f], f) && $e(e, [f].concat(t), n);
      return;
    } else if (o && r === "object") {
      const {
        from: f = 0,
        to: g = e.length - 1,
        by: d = 1
      } = i;
      for (let c = f; c <= g; c += d)
        $e(e, [c].concat(t), n);
      return;
    } else if (t.length > 1) {
      $e(e[i], t, [i].concat(n));
      return;
    }
    l = e[i], n = [i].concat(n);
  }
  let s = t[0];
  typeof s == "function" && (s = s(l, n), s === l) || i === void 0 && s == null || (s = oe(s), i === void 0 || ae(l) && ae(s) && !Array.isArray(s) ? yt(l, s) : ce(e, i, s));
}
function Wr(...[e, t]) {
  const n = oe(e || {}), i = Array.isArray(n), l = _t(n);
  function s(...r) {
    St(() => {
      i && r.length === 1 ? Br(n, r[0]) : $e(n, r);
    });
  }
  return [l, s];
}
const pe = /* @__PURE__ */ new WeakMap(), xt = {
  get(e, t) {
    if (t === Ee) return e;
    const n = e[t];
    let i;
    return ae(n) ? pe.get(n) || (pe.set(n, i = new Proxy(n, xt)), i) : n;
  },
  set(e, t, n) {
    return ce(e, t, oe(n)), !0;
  },
  deleteProperty(e, t) {
    return ce(e, t, void 0, !0), !0;
  }
};
function Yr(e) {
  return (t) => {
    if (ae(t)) {
      let n;
      (n = pe.get(t)) || pe.set(t, n = new Proxy(t, xt)), e(n);
    }
    return t;
  };
}
function Gr() {
  return {
    schema_version: "1.0",
    metadata: {
      name: "Untitled Model",
      description: "A new ESM model",
      version: "0.1.0",
      authors: [],
      created: (/* @__PURE__ */ new Date()).toISOString(),
      modified: (/* @__PURE__ */ new Date()).toISOString()
    },
    components: {},
    coupling: []
  };
}
function Xr(e, t) {
  if (t.length === 0) return e;
  let n = e;
  for (const i of t) {
    if (n == null) return;
    n = n[i];
  }
  return n;
}
function Re(e) {
  const t = [];
  return e.schema_version || t.push("Missing schema_version"), e.metadata ? e.metadata.name || t.push("Missing metadata.name") : t.push("Missing metadata"), e.components || t.push("Missing components"), Array.isArray(e.coupling) || t.push("coupling must be an array"), {
    isValid: t.length === 0,
    errors: t
  };
}
function El(e = {}) {
  const {
    initialFile: t = Gr(),
    historyConfig: n = {},
    enableValidation: i = !0
  } = e, [l, s] = Wr(t), [r, o] = I(
    i ? Re(t) : { isValid: !0, errors: [] }
  ), f = T(() => l), g = Ur(
    f,
    ($) => {
      s($), i && o(Re($));
    },
    n
  );
  function d($) {
    return Xr(l, $);
  }
  function c($, y) {
    $.length === 0 ? s(y) : s(
      Yr((p) => {
        let R = p;
        for (let k = 0; k < $.length - 1; k++) {
          const b = $[k];
          if (R[b] == null) {
            const x = $[k + 1];
            R[b] = typeof x == "number" ? [] : {};
          }
          R = R[b];
        }
        R[$[$.length - 1]] = y;
      })
    ), i && o(Re(l));
  }
  function m($, y) {
    const p = d($), R = y(p);
    c($, R);
  }
  function h() {
    return r().isValid;
  }
  function u() {
    return r().errors;
  }
  return {
    file: l,
    setFile: s,
    getPath: d,
    setPath: c,
    updatePath: m,
    history: g,
    isValid: h,
    validationErrors: u
  };
}
const kl = {
  /**
   * Convert a dot-separated string to a path array
   */
  fromString: (e) => e.split(".").filter((t) => t.length > 0),
  /**
   * Convert a path array to a dot-separated string
   */
  toString: (e) => e.join("."),
  /**
   * Check if two paths are equal
   */
  equals: (e, t) => e.length !== t.length ? !1 : e.every((n, i) => n === t[i]),
  /**
   * Check if path1 is a parent of path2
   */
  isParent: (e, t) => e.length >= t.length ? !1 : e.every((n, i) => n === t[i]),
  /**
   * Get the parent path (all segments except the last)
   */
  parent: (e) => e.slice(0, -1),
  /**
   * Get the last segment of a path
   */
  lastSegment: (e) => e[e.length - 1],
  /**
   * Append a segment to a path
   */
  append: (e, t) => [...e, t]
}, pl = {
  metadata: () => ["metadata"],
  metadataName: () => ["metadata", "name"],
  metadataDescription: () => ["metadata", "description"],
  components: () => ["components"],
  component: (e) => ["components", e],
  componentType: (e) => ["components", e, "type"],
  coupling: () => ["coupling"],
  couplingEntry: (e) => ["coupling", e],
  // Model-specific paths
  modelVariables: (e) => ["components", e, "variables"],
  modelVariable: (e, t) => ["components", e, "variables", t],
  modelEquations: (e) => ["components", e, "equations"],
  modelEquation: (e, t) => ["components", e, "equations", t],
  // Reaction system paths
  reactionSpecies: (e) => ["components", e, "species"],
  reactionSpeciesEntry: (e, t) => ["components", e, "species", t],
  reactions: (e) => ["components", e, "reactions"],
  reaction: (e, t) => ["components", e, "reactions", t]
}, Qr = (e) => {
  if (!e.expression)
    return () => {
      const t = document.createElement("div");
      return t.className = "error-state", t.textContent = "Missing required attribute: expression", t;
    };
  try {
    const n = {
      initialExpression: JSON.parse(e.expression),
      onChange: (i) => {
        if (typeof window < "u" && e.element) {
          const l = new CustomEvent("change", {
            detail: { expression: i },
            bubbles: !0
          });
          e.element.dispatchEvent(l);
        }
      },
      allowEditing: e["allow-editing"] !== "false",
      showPalette: e["show-palette"] !== "false",
      showValidation: e["show-validation"] !== "false"
    };
    return () => ct(n);
  } catch (t) {
    return () => {
      const n = document.createElement("div");
      return n.className = "error-state", n.textContent = `Component error: ${t instanceof Error ? t.message : "Unknown error"}`, n;
    };
  }
}, Zr = (e) => {
  if (!e.model)
    return () => {
      const t = document.createElement("div");
      return t.className = "error-state", t.textContent = "Missing required attribute: model", t;
    };
  try {
    const t = JSON.parse(e.model), n = e["validation-errors"] ? JSON.parse(e["validation-errors"]) : [], i = {
      model: t,
      onChange: (l) => {
        if (typeof window < "u" && e.element) {
          const s = new CustomEvent("change", {
            detail: { model: l },
            bubbles: !0
          });
          e.element.dispatchEvent(s);
        }
      },
      allowEditing: e["allow-editing"] !== "false",
      showValidation: e["show-validation"] !== "false",
      validationErrors: n
    };
    return () => ii(i);
  } catch (t) {
    return () => {
      const n = document.createElement("div");
      return n.className = "error-state", n.textContent = `Component error: ${t instanceof Error ? t.message : "Unknown error"}`, n;
    };
  }
}, el = (e) => {
  const t = e["esm-file"] || e.esmFile;
  if (!t)
    return () => {
      const n = document.createElement("div");
      return n.className = "error-state", n.textContent = "Missing required attribute: esm-file", n;
    };
  try {
    const n = JSON.parse(t), [i, l] = I(n), s = {
      esmFile: i(),
      showDetails: e["show-summary"] !== "false",
      showExportOptions: !0,
      onComponentTypeClick: (r) => {
        if (typeof window < "u" && e.element) {
          const o = new CustomEvent("componentTypeClick", {
            detail: { componentType: r },
            bubbles: !0
          });
          e.element.dispatchEvent(o);
        }
      },
      onExport: (r) => {
        if (typeof window < "u" && e.element) {
          const o = new CustomEvent("export", {
            detail: { format: r, file: i() },
            bubbles: !0
          });
          e.element.dispatchEvent(o);
        }
      }
    };
    return () => Nr(s);
  } catch (n) {
    return () => {
      const i = document.createElement("div");
      return i.className = "error-state", i.textContent = `Component error: ${n instanceof Error ? n.message : "Unknown error"}`, i;
    };
  }
}, tl = (e) => {
  const t = e["reaction-system"] || e.reactionSystem;
  if (!t)
    return () => {
      const n = document.createElement("div");
      return n.className = "error-state", n.textContent = "Missing required attribute: reaction-system", n;
    };
  try {
    const n = JSON.parse(t), i = e["validation-errors"] ? JSON.parse(e["validation-errors"]) : [], l = {
      reactionSystem: n,
      onChange: (s) => {
        if (typeof window < "u" && e.element) {
          const r = new CustomEvent("change", {
            detail: { reactionSystem: s },
            bubbles: !0
          });
          e.element.dispatchEvent(r);
        }
      },
      allowEditing: e["allow-editing"] !== "false",
      showValidation: e["show-validation"] !== "false",
      validationErrors: i
    };
    return () => Oi(l);
  } catch (n) {
    return () => {
      const i = document.createElement("div");
      return i.className = "error-state", i.textContent = `Component error: ${n instanceof Error ? n.message : "Unknown error"}`, i;
    };
  }
}, nl = (e) => {
  const t = e["esm-file"] || e.esmFile;
  if (!t)
    return () => {
      const n = document.createElement("div");
      return n.className = "error-state", n.textContent = "Missing required attribute: esm-file", n;
    };
  try {
    const i = {
      esmFile: JSON.parse(t),
      onEditCoupling: (l, s) => {
        if (typeof window < "u" && e.element) {
          const r = new CustomEvent("couplingEdit", {
            detail: { coupling: l, edgeId: s },
            bubbles: !0
          });
          e.element.dispatchEvent(r);
        }
      },
      onSelectComponent: (l) => {
        if (typeof window < "u" && e.element) {
          const s = new CustomEvent("componentSelect", {
            detail: { componentId: l },
            bubbles: !0
          });
          e.element.dispatchEvent(s);
        }
      },
      width: e.width ? parseInt(e.width, 10) : void 0,
      height: e.height ? parseInt(e.height, 10) : void 0,
      interactive: e.interactive !== "false",
      allowEditing: e["allow-editing"] !== "false"
    };
    return () => tr(i);
  } catch (n) {
    return () => {
      const i = document.createElement("div");
      return i.className = "error-state", i.textContent = `Component error: ${n instanceof Error ? n.message : "Unknown error"}`, i;
    };
  }
};
function nt() {
  if (!(typeof window > "u" || typeof customElements > "u"))
    try {
      ge("esm-expression-editor", {
        ...Qr,
        element: null
        // Will be set by solid-element
      }, ["expression", "allow-editing", "show-palette", "show-validation"]), ge("esm-model-editor", {
        ...Zr,
        element: null
        // Will be set by solid-element
      }, ["model", "allow-editing", "show-validation", "validation-errors"]), ge("esm-file-editor", {
        ...el,
        element: null
        // Will be set by solid-element
      }, ["esm-file", "allow-editing", "enable-undo", "show-summary", "show-validation"]), ge("esm-reaction-editor", {
        ...tl,
        element: null
        // Will be set by solid-element
      }, ["reaction-system", "allow-editing", "show-validation", "validation-errors"]), ge("esm-coupling-graph", {
        ...nl,
        element: null
        // Will be set by solid-element
      }, ["esm-file", "width", "height", "interactive", "allow-editing"]), console.log("ESM Editor web components registered successfully");
    } catch (e) {
      console.warn("Failed to register ESM Editor web components:", e);
    }
}
typeof window < "u" && (document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", nt) : setTimeout(nt, 0));
export {
  st as COMMUTATIVE_OPERATORS,
  pl as CommonPaths,
  tr as CouplingGraph,
  hl as Delimiters,
  ot as DraggableExpression,
  ct as EquationEditor,
  Se as ExpressionNode,
  yn as ExpressionPalette,
  Nr as FileSummary,
  ol as Fraction,
  fl as HighlightProvider,
  ii as ModelEditor,
  kl as PathUtils,
  ul as Radical,
  Oi as ReactionEditor,
  vl as SelectionProvider,
  Ht as StructuralEditingMenu,
  sl as StructuralEditingProvider,
  dl as Subscript,
  cl as Superscript,
  al as ValidationPanel,
  Lt as WRAP_OPERATORS,
  dt as buildVarEquivalences,
  El as createAstStore,
  $l as createHighlightContext,
  bl as createSelectionContext,
  Ur as createUndoHistory,
  Cl as createUndoKeyboardHandler,
  yl as getVariableSuggestions,
  ml as isHighlighted,
  ut as normalizeScopedReference,
  wl as pathToString,
  xl as pathsEqual,
  nt as registerWebComponents,
  Sl as stringToPath,
  gl as useHighlightContext,
  _l as useSelectionContext,
  Ae as useStructuralEditingContext
};
