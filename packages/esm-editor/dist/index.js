import { sharedConfig as Z, createRenderEffect as T, createMemo as M, untrack as at, createContext as Ie, useContext as Fe, createSignal as O, createComponent as v, Show as C, For as L, onMount as pt, onCleanup as ye, mergeProps as fe, createEffect as je, $PROXY as ne, batch as Pt, $TRACK as Ue, getListener as Te } from "solid-js";
import { forceSimulation as At, forceLink as Rt, forceManyBody as qt, forceCenter as Dt, forceCollide as Vt } from "d3-force";
import { validate as ot } from "esm-format";
import { customElement as ge } from "solid-element";
const Nt = /* @__PURE__ */ new Set(["innerHTML", "textContent", "innerText", "children"]), Tt = /* @__PURE__ */ Object.assign(/* @__PURE__ */ Object.create(null), {
  className: "class",
  htmlFor: "for"
}), Mt = /* @__PURE__ */ new Set(["beforeinput", "click", "dblclick", "contextmenu", "focusin", "focusout", "input", "keydown", "keyup", "mousedown", "mousemove", "mouseout", "mouseover", "mouseup", "pointerdown", "pointermove", "pointerout", "pointerover", "pointerup", "touchend", "touchmove", "touchstart"]), Ot = {
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace"
}, J = (e) => M(() => e());
function It(e, t, n) {
  let i = n.length, l = t.length, s = i, r = 0, c = 0, g = t[l - 1].nextSibling, $ = null;
  for (; r < l || c < s; ) {
    if (t[r] === n[c]) {
      r++, c++;
      continue;
    }
    for (; t[l - 1] === n[s - 1]; )
      l--, s--;
    if (l === r) {
      const d = s < i ? c ? n[c - 1].nextSibling : n[s - c] : g;
      for (; c < s; ) e.insertBefore(n[c++], d);
    } else if (s === c)
      for (; r < l; )
        (!$ || !$.has(t[r])) && t[r].remove(), r++;
    else if (t[r] === n[s - 1] && n[c] === t[l - 1]) {
      const d = t[--l].nextSibling;
      e.insertBefore(n[c++], t[r++].nextSibling), e.insertBefore(n[--s], d), t[l] = n[s];
    } else {
      if (!$) {
        $ = /* @__PURE__ */ new Map();
        let o = c;
        for (; o < s; ) $.set(n[o], o++);
      }
      const d = $.get(t[r]);
      if (d != null)
        if (c < d && d < s) {
          let o = r, m = 1, h;
          for (; ++o < l && o < s && !((h = $.get(t[o])) == null || h !== d + m); )
            m++;
          if (m > d - c) {
            const u = t[r];
            for (; c < d; ) e.insertBefore(n[c++], u);
          } else e.replaceChild(n[c++], t[r++]);
        } else r++;
      else t[r++].remove();
    }
  }
}
const Be = "_$DX_DELEGATE";
function _(e, t, n, i) {
  let l;
  const s = () => {
    const c = i ? document.createElementNS("http://www.w3.org/1998/Math/MathML", "template") : document.createElement("template");
    return c.innerHTML = e, n ? c.content.firstChild.firstChild : i ? c.firstChild : c.content.firstChild;
  }, r = t ? () => at(() => document.importNode(l || (l = s()), !0)) : () => (l || (l = s())).cloneNode(!0);
  return r.cloneNode = r, r;
}
function G(e, t = window.document) {
  const n = t[Be] || (t[Be] = /* @__PURE__ */ new Set());
  for (let i = 0, l = e.length; i < l; i++) {
    const s = e[i];
    n.has(s) || (n.add(s), t.addEventListener(s, Bt));
  }
}
function N(e, t, n) {
  de(e) || (n == null ? e.removeAttribute(t) : e.setAttribute(t, n));
}
function Ft(e, t, n, i) {
  de(e) || (i == null ? e.removeAttributeNS(t, n) : e.setAttributeNS(t, n, i));
}
function jt(e, t, n) {
  de(e) || (n ? e.setAttribute(t, "") : e.removeAttribute(t));
}
function H(e, t) {
  de(e) || (t == null ? e.removeAttribute("class") : e.className = t);
}
function B(e, t, n, i) {
  if (i)
    Array.isArray(n) ? (e[`$$${t}`] = n[0], e[`$$${t}Data`] = n[1]) : e[`$$${t}`] = n;
  else if (Array.isArray(n)) {
    const l = n[0];
    e.addEventListener(t, n[0] = (s) => l.call(e, n[1], s));
  } else e.addEventListener(t, n, typeof n != "function" && n);
}
function Lt(e, t, n = {}) {
  const i = Object.keys(t || {}), l = Object.keys(n);
  let s, r;
  for (s = 0, r = l.length; s < r; s++) {
    const c = l[s];
    !c || c === "undefined" || t[c] || (ze(e, c, !1), delete n[c]);
  }
  for (s = 0, r = i.length; s < r; s++) {
    const c = i[s], g = !!t[c];
    !c || c === "undefined" || n[c] === g || !g || (ze(e, c, !0), n[c] = g);
  }
  return n;
}
function ct(e, t, n) {
  if (!t) return n ? N(e, "style") : t;
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
function Ke(e, t, n) {
  n != null ? e.style.setProperty(t, n) : e.style.removeProperty(t);
}
function me(e, t = {}, n, i) {
  const l = {};
  return T(() => l.children = ve(e, t.children, l.children)), T(() => typeof t.ref == "function" && Le(t.ref, e)), T(() => Ht(e, t, n, !0, l, !0)), l;
}
function Le(e, t, n) {
  return at(() => e(t, n));
}
function a(e, t, n, i) {
  if (n !== void 0 && !i && (i = []), typeof t != "function") return ve(e, t, i, n);
  T((l) => ve(e, t(), l, n), i);
}
function Ht(e, t, n, i, l = {}, s = !1) {
  t || (t = {});
  for (const r in l)
    if (!(r in t)) {
      if (r === "children") continue;
      l[r] = Je(e, r, null, l[r], n, s, t);
    }
  for (const r in t) {
    if (r === "children")
      continue;
    const c = t[r];
    l[r] = Je(e, r, c, l[r], n, s, t);
  }
}
function de(e) {
  return !!Z.context && !Z.done && (!e || e.isConnected);
}
function Ut(e) {
  return e.toLowerCase().replace(/-([a-z])/g, (t, n) => n.toUpperCase());
}
function ze(e, t, n) {
  const i = t.trim().split(/\s+/);
  for (let l = 0, s = i.length; l < s; l++) e.classList.toggle(i[l], n);
}
function Je(e, t, n, i, l, s, r) {
  let c, g, $, d;
  if (t === "style") return ct(e, n, i);
  if (t === "classList") return Lt(e, n, i);
  if (n === i) return i;
  if (t === "ref")
    s || n(e);
  else if (t.slice(0, 3) === "on:") {
    const o = t.slice(3);
    i && e.removeEventListener(o, i, typeof i != "function" && i), n && e.addEventListener(o, n, typeof n != "function" && n);
  } else if (t.slice(0, 10) === "oncapture:") {
    const o = t.slice(10);
    i && e.removeEventListener(o, i, !0), n && e.addEventListener(o, n, !0);
  } else if (t.slice(0, 2) === "on") {
    const o = t.slice(2).toLowerCase(), m = Mt.has(o);
    if (!m && i) {
      const h = Array.isArray(i) ? i[0] : i;
      e.removeEventListener(o, h);
    }
    (m || n) && (B(e, o, n, m), m && G([o]));
  } else if (t.slice(0, 5) === "attr:")
    N(e, t.slice(5), n);
  else if (t.slice(0, 5) === "bool:")
    jt(e, t.slice(5), n);
  else if ((d = t.slice(0, 5) === "prop:") || ($ = Nt.has(t)) || (c = e.nodeName.includes("-") || "is" in r)) {
    if (d)
      t = t.slice(5), g = !0;
    else if (de(e)) return n;
    t === "class" || t === "className" ? H(e, n) : c && !g && !$ ? e[Ut(t)] = n : e[t] = n;
  } else {
    const o = t.indexOf(":") > -1 && Ot[t.split(":")[0]];
    o ? Ft(e, o, t, n) : N(e, Tt[t] || t, n);
  }
  return n;
}
function Bt(e) {
  if (Z.registry && Z.events && Z.events.find(([g, $]) => $ === e))
    return;
  let t = e.target;
  const n = `$$${e.type}`, i = e.target, l = e.currentTarget, s = (g) => Object.defineProperty(e, "target", {
    configurable: !0,
    value: g
  }), r = () => {
    const g = t[n];
    if (g && !t.disabled) {
      const $ = t[`${n}Data`];
      if ($ !== void 0 ? g.call(t, $, e) : g.call(t, e), e.cancelBubble) return;
    }
    return t.host && typeof t.host != "string" && !t.host._$host && t.contains(e.target) && s(t.host), !0;
  }, c = () => {
    for (; r() && (t = t._$host || t.parentNode || t.host); ) ;
  };
  if (Object.defineProperty(e, "currentTarget", {
    configurable: !0,
    get() {
      return t || document;
    }
  }), Z.registry && !Z.done && (Z.done = _$HY.done = !0), e.composedPath) {
    const g = e.composedPath();
    s(g[0]);
    for (let $ = 0; $ < g.length - 2 && (t = g[$], !!r()); $++) {
      if (t._$host) {
        t = t._$host, c();
        break;
      }
      if (t.parentNode === l)
        break;
    }
  } else c();
  s(i);
}
function ve(e, t, n, i, l) {
  const s = de(e);
  if (s) {
    !n && (n = [...e.childNodes]);
    let g = [];
    for (let $ = 0; $ < n.length; $++) {
      const d = n[$];
      d.nodeType === 8 && d.data.slice(0, 2) === "!$" ? d.remove() : g.push(d);
    }
    n = g;
  }
  for (; typeof n == "function"; ) n = n();
  if (t === n) return n;
  const r = typeof t, c = i !== void 0;
  if (e = c && n[0] && n[0].parentNode || e, r === "string" || r === "number") {
    if (s || r === "number" && (t = t.toString(), t === n))
      return n;
    if (c) {
      let g = n[0];
      g && g.nodeType === 3 ? g.data !== t && (g.data = t) : g = document.createTextNode(t), n = ie(e, n, i, g);
    } else
      n !== "" && typeof n == "string" ? n = e.firstChild.data = t : n = e.textContent = t;
  } else if (t == null || r === "boolean") {
    if (s) return n;
    n = ie(e, n, i);
  } else {
    if (r === "function")
      return T(() => {
        let g = t();
        for (; typeof g == "function"; ) g = g();
        n = ve(e, g, n, i);
      }), () => n;
    if (Array.isArray(t)) {
      const g = [], $ = n && Array.isArray(n);
      if (Me(g, t, n, l))
        return T(() => n = ve(e, g, n, i, !0)), () => n;
      if (s) {
        if (!g.length) return n;
        if (i === void 0) return n = [...e.childNodes];
        let d = g[0];
        if (d.parentNode !== e) return n;
        const o = [d];
        for (; (d = d.nextSibling) !== i; ) o.push(d);
        return n = o;
      }
      if (g.length === 0) {
        if (n = ie(e, n, i), c) return n;
      } else $ ? n.length === 0 ? We(e, g, i) : It(e, n, g) : (n && ie(e), We(e, g));
      n = g;
    } else if (t.nodeType) {
      if (s && t.parentNode) return n = c ? [t] : t;
      if (Array.isArray(n)) {
        if (c) return n = ie(e, n, i, t);
        ie(e, n, null, t);
      } else n == null || n === "" || !e.firstChild ? e.appendChild(t) : e.replaceChild(t, e.firstChild);
      n = t;
    }
  }
  return n;
}
function Me(e, t, n, i) {
  let l = !1;
  for (let s = 0, r = t.length; s < r; s++) {
    let c = t[s], g = n && n[e.length], $;
    if (!(c == null || c === !0 || c === !1)) if (($ = typeof c) == "object" && c.nodeType)
      e.push(c);
    else if (Array.isArray(c))
      l = Me(e, c, g) || l;
    else if ($ === "function")
      if (i) {
        for (; typeof c == "function"; ) c = c();
        l = Me(e, Array.isArray(c) ? c : [c], Array.isArray(g) ? g : [g]) || l;
      } else
        e.push(c), l = !0;
    else {
      const d = String(c);
      g && g.nodeType === 3 && g.data === d ? e.push(g) : e.push(document.createTextNode(d));
    }
  }
  return l;
}
function We(e, t, n = null) {
  for (let i = 0, l = t.length; i < l; i++) e.insertBefore(t[i], n);
}
function ie(e, t, n, i) {
  if (n === void 0) return e.textContent = "";
  const l = i || document.createTextNode("");
  if (t.length) {
    let s = !1;
    for (let r = t.length - 1; r >= 0; r--) {
      const c = t[r];
      if (l !== c) {
        const g = c.parentNode === e;
        !s && !r ? g ? e.replaceChild(l, c) : e.insertBefore(l, n) : g && c.remove();
      } else s = !0;
    }
  } else e.insertBefore(l, n);
  return [l];
}
var Kt = /* @__PURE__ */ _('<div class=structural-editing-menu style="position:absolute;background-color:white;border:1px solid #ccc;border-radius:4px;padding:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);z-index:1000;min-width:200px"><div class=menu-section><h4 class=menu-header>Wrap in Operator</h4><div class=wrap-operators></div></div><div class=menu-section><button class=close-menu-btn>Close'), zt = /* @__PURE__ */ _("<button class=wrap-operator-btn>"), Jt = /* @__PURE__ */ _('<div class=menu-section><button class=unwrap-btn title="Remove the outer operator and keep its argument">Unwrap'), Wt = /* @__PURE__ */ _('<div class=menu-section><button class=delete-term-btn title="Remove this term from the operation">Delete Term'), Gt = /* @__PURE__ */ _("<div class=draggable-expression>");
const Yt = [{
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
}], dt = /* @__PURE__ */ new Set(["+", "*"]), ut = Ie();
function Ge(e) {
  return typeof e == "object" && e !== null && "op" in e && "args" in e && Array.isArray(e.args) && e.args.length === 1;
}
function xe(e) {
  return typeof e == "object" && e !== null && "op" in e && dt.has(e.op);
}
function Se(e, t) {
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
function Ye(e, t) {
  if (t.length < 2)
    return {
      parent: null,
      parentPath: [],
      argIndex: null
    };
  const n = t.slice(0, -2), i = t[t.length - 1];
  return {
    parent: Se(e, n),
    parentPath: n,
    argIndex: typeof i == "number" ? i : null
  };
}
function re(e, t, n) {
  if (t.length === 0)
    return n;
  let i = JSON.parse(JSON.stringify(e)), l = i;
  for (let r = 0; r < t.length - 1; r++) {
    const c = t[r];
    if (c === "args" && typeof l == "object" && "args" in l)
      l = l.args;
    else if (typeof c == "number" && Array.isArray(l))
      l = l[c];
    else
      throw new Error(`Invalid path segment: ${c}`);
  }
  const s = t[t.length - 1];
  if (typeof s == "number" && Array.isArray(l))
    l[s] = n;
  else
    throw new Error(`Invalid final path segment: ${s}`);
  return i;
}
function bl(e) {
  const [t, n] = O({
    isDragging: !1,
    dragPath: null,
    dragIndex: null,
    dropTarget: null
  }), m = {
    replaceNode: (h, u) => {
      const f = e.rootExpression(), b = re(f, h, u);
      e.onRootReplace(b);
    },
    wrapNode: (h, u) => {
      const f = e.rootExpression(), b = Se(f, h);
      if (!b) return;
      const P = re(f, h, {
        op: u,
        args: [b]
      });
      e.onRootReplace(P);
    },
    unwrapNode: (h) => {
      const u = e.rootExpression(), f = Se(u, h);
      if (!Ge(f))
        return !1;
      const b = f.args[0], p = re(u, h, b);
      return e.onRootReplace(p), !0;
    },
    deleteTerm: (h) => {
      const u = e.rootExpression(), {
        parent: f,
        parentPath: b,
        argIndex: p
      } = Ye(u, h);
      if (!f || !xe(f) || p === null)
        return !1;
      const P = f;
      if (P.args.length <= 2) {
        const E = P.args[1 - p], y = re(u, b, E);
        e.onRootReplace(y);
      } else {
        const E = [...P.args];
        E.splice(p, 1);
        const y = {
          ...P,
          args: E
        }, x = re(u, b, y);
        e.onRootReplace(x);
      }
      return !0;
    },
    reorderArgs: (h, u, f) => {
      const b = e.rootExpression(), p = Se(b, h);
      if (!xe(p))
        return !1;
      const P = p, E = [...P.args], [y] = E.splice(u, 1);
      E.splice(f, 0, y);
      const x = {
        ...P,
        args: E
      }, R = re(b, h, x);
      return e.onRootReplace(R), !0;
    },
    canUnwrap: (h) => Ge(h),
    canDeleteTerm: (h, u) => {
      const f = e.rootExpression(), {
        parent: b
      } = Ye(f, u);
      return b !== null && xe(b);
    },
    canReorderArgs: (h) => xe(h) && h.args.length > 1,
    getWrapOperators: () => [...Yt],
    dragState: t,
    setDragState: n
  };
  return v(ut.Provider, {
    value: m,
    get children() {
      return e.children;
    }
  });
}
function Re() {
  const e = Fe(ut);
  if (!e)
    throw new Error("useStructuralEditingContext must be used within a StructuralEditingProvider");
  return e;
}
function Xt(e) {
  const t = Re();
  if (!e.isVisible || !e.selectedPath || !e.selectedExpr)
    return null;
  const n = (c) => {
    e.selectedPath && (t.wrapNode(e.selectedPath, c), e.onClose());
  }, i = () => {
    e.selectedPath && t.unwrapNode(e.selectedPath) && e.onClose();
  }, l = () => {
    e.selectedPath && t.deleteTerm(e.selectedPath) && e.onClose();
  }, s = t.canUnwrap(e.selectedExpr), r = e.selectedPath && t.canDeleteTerm(e.selectedExpr, e.selectedPath);
  return (() => {
    var c = Kt(), g = c.firstChild, $ = g.firstChild, d = $.nextSibling, o = g.nextSibling, m = o.firstChild;
    return a(d, () => t.getWrapOperators().map((h) => (() => {
      var u = zt();
      return u.$$click = () => n(h.op), a(u, () => h.label), T(() => N(u, "title", h.label)), u;
    })())), a(c, s && (() => {
      var h = Jt(), u = h.firstChild;
      return u.$$click = i, h;
    })(), o), a(c, r && (() => {
      var h = Wt(), u = h.firstChild;
      return u.$$click = l, h;
    })(), o), B(m, "click", e.onClose, !0), T((h) => {
      var b, p;
      var u = `${((b = e.position) == null ? void 0 : b.x) || 0}px`, f = `${((p = e.position) == null ? void 0 : p.y) || 0}px`;
      return u !== h.e && Ke(c, "left", h.e = u), f !== h.t && Ke(c, "top", h.t = f), h;
    }, {
      e: void 0,
      t: void 0
    }), c;
  })();
}
function ht(e) {
  const t = Re();
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
    const c = t.dragState();
    c.isDragging && c.dragIndex !== e.index && t.setDragState({
      ...c,
      dropTarget: {
        path: e.parentPath,
        index: e.index
      }
    });
  }, s = (r) => {
    var g;
    r.preventDefault();
    const c = (g = r.dataTransfer) == null ? void 0 : g.getData("text/plain");
    if (c)
      try {
        const $ = JSON.parse(c);
        $.index !== e.index && $.parentPath.join(".") === e.parentPath.join(".") && t.reorderArgs(e.parentPath, $.index, e.index);
      } catch ($) {
        console.error("Failed to parse drag data:", $);
      }
  };
  return (() => {
    var r = Gt();
    return r.addEventListener("drop", s), r.addEventListener("dragover", l), r.addEventListener("dragend", i), r.addEventListener("dragstart", n), N(r, "draggable", !0), a(r, () => e.children), T(() => N(r, "data-drag-index", e.index)), r;
  })();
}
G(["click"]);
var Qt = /* @__PURE__ */ _("<span class=esm-infix-op>"), Xe = /* @__PURE__ */ _("<span class=esm-operator> <!> "), Zt = /* @__PURE__ */ _("<span class=esm-multiplication>"), en = /* @__PURE__ */ _("<span class=esm-multiply>⋅"), tn = /* @__PURE__ */ _("<span class=esm-fraction><span class=esm-fraction-numerator></span><span class=esm-fraction-denominator>"), nn = /* @__PURE__ */ _("<span class=esm-exponentiation><span class=esm-base></span><span class=esm-exponent>"), rn = /* @__PURE__ */ _("<span class=esm-derivative-wrt><span class=esm-d-operator>d</span><span class=esm-variable>"), ln = /* @__PURE__ */ _("<span class=esm-derivative><span class=esm-d-operator>d</span><span class=esm-derivative-body>"), sn = /* @__PURE__ */ _('<span class="esm-function esm-sqrt"><span class=esm-radical>√</span><span class=esm-sqrt-content>'), an = /* @__PURE__ */ _("<span class=esm-function><span class=esm-function-name></span><span class=esm-function-args>(<!>)"), on = /* @__PURE__ */ _("<span class=esm-comparison>"), cn = /* @__PURE__ */ _("<span class=esm-generic-function><span class=esm-function-name></span><span class=esm-function-args>(<!>)"), dn = /* @__PURE__ */ _("<span class=esm-num>"), un = /* @__PURE__ */ _("<span class=esm-var>"), hn = /* @__PURE__ */ _("<span class=esm-unknown>?"), fn = /* @__PURE__ */ _("<span tabindex=0 role=button>");
const Ee = /* @__PURE__ */ new Set([
  // Period 1
  "H",
  "He",
  // Period 2
  "Li",
  "Be",
  "B",
  "C",
  "N",
  "O",
  "F",
  "Ne",
  // Period 3
  "Na",
  "Mg",
  "Al",
  "Si",
  "P",
  "S",
  "Cl",
  "Ar",
  // Period 4
  "K",
  "Ca",
  "Sc",
  "Ti",
  "V",
  "Cr",
  "Mn",
  "Fe",
  "Co",
  "Ni",
  "Cu",
  "Zn",
  "Ga",
  "Ge",
  "As",
  "Se",
  "Br",
  "Kr",
  // Period 5
  "Rb",
  "Sr",
  "Y",
  "Zr",
  "Nb",
  "Mo",
  "Tc",
  "Ru",
  "Rh",
  "Pd",
  "Ag",
  "Cd",
  "In",
  "Sn",
  "Sb",
  "Te",
  "I",
  "Xe",
  // Period 6
  "Cs",
  "Ba",
  "La",
  "Ce",
  "Pr",
  "Nd",
  "Pm",
  "Sm",
  "Eu",
  "Gd",
  "Tb",
  "Dy",
  "Ho",
  "Er",
  "Tm",
  "Yb",
  "Lu",
  "Hf",
  "Ta",
  "W",
  "Re",
  "Os",
  "Ir",
  "Pt",
  "Au",
  "Hg",
  "Tl",
  "Pb",
  "Bi",
  "Po",
  "At",
  "Rn",
  // Period 7
  "Fr",
  "Ra",
  "Ac",
  "Th",
  "Pa",
  "U",
  "Np",
  "Pu",
  "Am",
  "Cm",
  "Bk",
  "Cf",
  "Es",
  "Fm",
  "Md",
  "No",
  "Lr",
  "Rf",
  "Db",
  "Sg",
  "Bh",
  "Hs",
  "Mt",
  "Ds",
  "Rg",
  "Cn",
  "Nh",
  "Fl",
  "Mc",
  "Lv",
  "Ts",
  "Og"
]), Qe = "₀₁₂₃₄₅₆₇₈₉";
function te(e) {
  const t = e.replace(/_/g, "");
  let n = 0, i = !1;
  for (; n < t.length; ) {
    for (; n < t.length && !/[A-Za-z]/.test(t[n]); )
      n++;
    if (n >= t.length) break;
    let l = !1;
    if (n + 1 < t.length) {
      const s = t.slice(n, n + 2);
      if (Ee.has(s)) {
        for (i = !0, l = !0, n += 2; n < t.length && /\d/.test(t[n]); )
          n++;
        continue;
      }
    }
    if (!l) {
      const s = t[n];
      if (Ee.has(s)) {
        for (i = !0, l = !0, n++; n < t.length && /\d/.test(t[n]); )
          n++;
        continue;
      }
    }
    if (!l)
      return !1;
  }
  return i;
}
function gn(e) {
  if (e.includes("_")) {
    const t = e.split("_");
    if (t.length === 2) {
      const [n, i] = t;
      if (te(i) && !te(n))
        return {
          prefix: n,
          suffix: i
        };
    }
    if (t.length === 3) {
      const n = t[0], i = t.slice(1).join("_");
      if (te(i) && !te(n))
        return {
          prefix: n,
          suffix: i
        };
    }
  }
  for (let t = 1; t < e.length; t++) {
    const n = e.substring(0, t), i = e.substring(t);
    if (te(i) && !te(n))
      return {
        prefix: n,
        suffix: i
      };
  }
  return null;
}
function ft(e) {
  if (!te(e)) {
    const l = gn(e);
    if (l) {
      const {
        prefix: s,
        suffix: r
      } = l, c = ft(r);
      return e.includes("_") ? `${s}_${c}` : `${s}${c}`;
    }
    return e;
  }
  let n = "", i = 0;
  for (; i < e.length; ) {
    let l = !1;
    if (i + 1 < e.length) {
      const s = e.slice(i, i + 2);
      if (Ee.has(s)) {
        for (n += s, i += 2; i < e.length && /\d/.test(e[i]); )
          n += Qe[parseInt(e[i])], i++;
        l = !0;
      }
    }
    if (!l && i < e.length) {
      const s = e[i];
      if (Ee.has(s)) {
        for (n += s, i++; i < e.length && /\d/.test(e[i]); )
          n += Qe[parseInt(e[i])], i++;
        l = !0;
      }
    }
    l || (n += e[i], i++);
  }
  return n;
}
function mn(e) {
  let t;
  try {
    t = Re();
  } catch {
  }
  const n = dt.has(e.node.op), {
    op: i,
    args: l
  } = e.node, s = (r, c) => {
    const g = [...e.path, "args", c], $ = v(_e, {
      expr: r,
      path: g,
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
      indexInParent: c
    });
    return t && n && ((l == null ? void 0 : l.length) || 0) > 1 ? v(ht, {
      path: g,
      index: c,
      get parentPath() {
        return e.path;
      },
      canDrag: !0,
      children: $
    }) : $;
  };
  switch (i) {
    case "+":
    case "-":
      return (() => {
        var r = Qt();
        return N(r, "data-operator", i), a(r, () => l == null ? void 0 : l.map((c, g) => [v(C, {
          when: g > 0,
          get children() {
            var $ = Xe(), d = $.firstChild, o = d.nextSibling;
            return o.nextSibling, a($, i, o), $;
          }
        }), J(() => s(c, g))])), r;
      })();
    case "*":
      return (() => {
        var r = Zt();
        return N(r, "data-operator", i), a(r, () => l == null ? void 0 : l.map((c, g) => [v(C, {
          when: g > 0,
          get children() {
            return en();
          }
        }), J(() => s(c, g))])), r;
      })();
    case "/":
      return (() => {
        var r = tn(), c = r.firstChild, g = c.nextSibling;
        return N(r, "data-operator", i), a(c, () => l && s(l[0], 0)), a(g, () => l && s(l[1], 1)), r;
      })();
    case "^":
      return (() => {
        var r = nn(), c = r.firstChild, g = c.nextSibling;
        return N(r, "data-operator", i), a(c, () => l && s(l[0], 0)), a(g, () => l && s(l[1], 1)), r;
      })();
    case "D":
      return (() => {
        var r = ln(), c = r.firstChild, g = c.nextSibling;
        return N(r, "data-operator", i), a(g, () => l && s(l[0], 0)), a(r, v(C, {
          get when() {
            return e.node.wrt;
          },
          get children() {
            var $ = rn(), d = $.firstChild, o = d.nextSibling;
            return a(o, () => e.node.wrt), $;
          }
        }), null), r;
      })();
    case "sqrt":
      return (() => {
        var r = sn(), c = r.firstChild, g = c.nextSibling;
        return N(r, "data-operator", i), a(g, () => l && s(l[0], 0)), r;
      })();
    case "exp":
    case "log":
    case "sin":
    case "cos":
    case "tan":
      return (() => {
        var r = an(), c = r.firstChild, g = c.nextSibling, $ = g.firstChild, d = $.nextSibling;
        return d.nextSibling, N(r, "data-operator", i), a(c, i), a(g, () => l == null ? void 0 : l.map((o, m) => [v(C, {
          when: m > 0,
          children: ", "
        }), J(() => s(o, m))]), d), r;
      })();
    case ">":
    case "<":
    case ">=":
    case "<=":
    case "==":
    case "!=":
      return (() => {
        var r = on();
        return N(r, "data-operator", i), a(r, () => l == null ? void 0 : l.map((c, g) => [v(C, {
          when: g > 0,
          get children() {
            var $ = Xe(), d = $.firstChild, o = d.nextSibling;
            return o.nextSibling, a($, i, o), $;
          }
        }), J(() => s(c, g))])), r;
      })();
    default:
      return (() => {
        var r = cn(), c = r.firstChild, g = c.nextSibling, $ = g.firstChild, d = $.nextSibling;
        return d.nextSibling, N(r, "data-operator", i), a(c, i), a(g, () => l == null ? void 0 : l.map((o, m) => [v(C, {
          when: m > 0,
          children: ", "
        }), J(() => s(o, m))]), d), r;
      })();
  }
}
const _e = (e) => {
  const [t, n] = O(!1), [i, l] = O(!1), [s, r] = O({
    x: 0,
    y: 0
  });
  let c;
  try {
    c = Re();
  } catch {
  }
  const g = M(() => typeof e.expr == "string" && !$n(e.expr)), $ = M(() => g() && e.highlightedVars().has(e.expr)), d = M(() => e.selectedPath && e.selectedPath.length === e.path.length && e.selectedPath.every((x, R) => x === e.path[R])), o = M(() => c && e.parentPath && typeof e.indexInParent == "number" && e.parentPath.length > 0), m = M(() => {
    const x = ["esm-expression-node"];
    return t() && x.push("hovered"), $() && x.push("highlighted"), d() && x.push("selected"), g() && x.push("variable"), typeof e.expr == "number" && x.push("number"), typeof e.expr == "object" && x.push("operator"), x.join(" ");
  }), h = () => {
    n(!0), g() && e.onHoverVar(e.expr);
  }, u = () => {
    n(!1), g() && e.onHoverVar(null);
  }, f = (x) => {
    x.stopPropagation(), e.onSelect(e.path);
  }, b = (x) => {
    x.preventDefault(), x.stopPropagation(), c && (e.onSelect(e.path), r({
      x: x.clientX,
      y: x.clientY
    }), l(!0));
  }, p = () => {
    l(!1);
  }, P = () => typeof e.expr == "number" ? (() => {
    var x = dn();
    return a(x, () => vn(e.expr)), T(() => N(x, "title", `Number: ${e.expr}`)), x;
  })() : typeof e.expr == "string" ? (() => {
    var x = un();
    return a(x, () => ft(e.expr)), T(() => N(x, "title", `Variable: ${e.expr}`)), x;
  })() : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? v(mn, {
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
  }) : hn(), E = [(() => {
    var x = fn();
    return x.$$contextmenu = b, x.$$click = f, x.addEventListener("mouseleave", u), x.addEventListener("mouseenter", h), a(x, P), T((R) => {
      var V = m(), k = y(), q = e.path.join(".");
      return V !== R.e && H(x, R.e = V), k !== R.t && N(x, "aria-label", R.t = k), q !== R.a && N(x, "data-path", R.a = q), R;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), x;
  })(), v(C, {
    get when() {
      return i() && c;
    },
    get children() {
      return v(Xt, {
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
  if (o() && c && e.parentPath && typeof e.indexInParent == "number")
    return v(ht, {
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
      children: E
    });
  return E;
  function y() {
    return typeof e.expr == "number" ? `Number: ${e.expr}` : typeof e.expr == "string" ? `Variable: ${e.expr}` : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? `Operator: ${e.expr.op}` : "Expression";
  }
};
function $n(e) {
  return /^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(e);
}
function vn(e) {
  if (e === 0) return "0";
  const t = Math.abs(e);
  if (t < 0.01 || t >= 1e4) {
    const n = e.toExponential(), [i, l] = n.split("e"), s = parseFloat(i).toString(), r = parseInt(l, 10), c = _n(r);
    return `${s}×10${c}`;
  }
  return Number.isInteger(e), e.toString();
}
function _n(e) {
  const t = {
    0: "⁰",
    1: "¹",
    2: "²",
    3: "³",
    4: "⁴",
    5: "⁵",
    6: "⁶",
    7: "⁷",
    8: "⁸",
    9: "⁹",
    "-": "⁻",
    "+": "⁺"
  };
  return e.toString().split("").map((n) => t[n] || n).join("");
}
G(["click", "contextmenu"]);
var bn = /* @__PURE__ */ _("<div role=button tabindex=0><div class=template-label></div><div class=template-description>"), yn = /* @__PURE__ */ _("<div class=context-suggestions><h4 class=section-title><span class=section-icon>🧪</span>Model Context</h4><div class=suggestions-grid>"), xn = /* @__PURE__ */ _("<div role=button tabindex=0><div class=item-type></div><div class=item-label>"), wn = /* @__PURE__ */ _(`<div class=palette-search><input type=text class=search-input placeholder="Search expressions... (type '/' to open)">`), Sn = /* @__PURE__ */ _('<div class=no-results><div class=no-results-icon>🔍</div><div class=no-results-text>No expressions found for "<!>"</div><div class=no-results-hint>Try searching for operators, functions, or keywords'), Cn = /* @__PURE__ */ _("<div class=quick-insert-help>Press <kbd>Escape</kbd> to close, click or drag to insert"), En = /* @__PURE__ */ _("<div><div class=palette-content>"), kn = /* @__PURE__ */ _("<div class=palette-section><h4 class=section-title><span class=section-icon></span></h4><div class=templates-grid>");
const Ze = [
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
], pn = {
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
}, Pn = (e) => {
  const [t, n] = O(!1), i = (r) => {
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
    var r = bn(), c = r.firstChild, g = c.nextSibling;
    return r.$$click = s, r.addEventListener("dragend", l), r.addEventListener("dragstart", i), N(r, "draggable", !0), a(c, () => e.template.label), a(g, () => e.template.description), T(($) => {
      var d = `expression-template ${t() ? "dragging" : ""}`, o = e.template.description, m = `Insert ${e.template.label}: ${e.template.description}`;
      return d !== $.e && H(r, $.e = d), o !== $.t && N(r, "title", $.t = o), m !== $.a && N(r, "aria-label", $.a = m), $;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), r;
  })();
}, An = (e) => {
  const t = M(() => {
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
  return v(C, {
    get when() {
      return t().length > 0;
    },
    get children() {
      var n = yn(), i = n.firstChild, l = i.nextSibling;
      return a(l, v(L, {
        get each() {
          return t();
        },
        children: (s) => (() => {
          var r = xn(), c = r.firstChild, g = c.nextSibling;
          return r.$$click = () => e.onInsert(s.expression), a(c, () => s.type.charAt(0).toUpperCase()), a(g, () => s.label), T(($) => {
            var d = `context-item ${s.type}`, o = `${s.type}: ${s.label}`, m = `Insert ${s.type} ${s.label}`;
            return d !== $.e && H(r, $.e = d), o !== $.t && N(r, "title", $.t = o), m !== $.a && N(r, "aria-label", $.a = m), $;
          }, {
            e: void 0,
            t: void 0,
            a: void 0
          }), r;
        })()
      })), n;
    }
  });
}, gt = (e) => {
  const [t, n] = O(""), i = M(() => e.searchQuery || t()), l = M(() => {
    const d = i().toLowerCase().trim();
    return d ? Ze.filter((o) => o.label.toLowerCase().includes(d) || o.description.toLowerCase().includes(d) || o.keywords.some((m) => m.toLowerCase().includes(d))) : Ze;
  }), s = M(() => {
    const d = {};
    return l().forEach((o) => {
      d[o.category] || (d[o.category] = []), d[o.category].push(o);
    }), d;
  }), r = (d) => {
    var o, m;
    (o = e.onInsertExpression) == null || o.call(e, d), e.quickInsertMode && ((m = e.onCloseQuickInsert) == null || m.call(e));
  }, c = (d) => {
    e.onSearchQueryChange ? e.onSearchQueryChange(d) : n(d);
  }, g = (d) => {
    var o;
    e.quickInsertMode && d.key === "Escape" && ((o = e.onCloseQuickInsert) == null || o.call(e));
  }, $ = () => {
    const d = ["expression-palette"];
    return e.quickInsertMode && d.push("quick-insert-mode"), e.visible === !1 && d.push("hidden"), e.class && d.push(e.class), d.join(" ");
  };
  return (() => {
    var d = En(), o = d.firstChild;
    return d.$$keydown = g, a(d, v(C, {
      get when() {
        return e.quickInsertMode || i();
      },
      get children() {
        var m = wn(), h = m.firstChild;
        return h.$$input = (u) => c(u.currentTarget.value), T(() => h.autofocus = e.quickInsertMode), T(() => h.value = i()), m;
      }
    }), o), a(o, v(C, {
      get when() {
        return !i();
      },
      get children() {
        return v(An, {
          get model() {
            return e.currentModel;
          },
          onInsert: r
        });
      }
    }), null), a(o, v(L, {
      get each() {
        return Object.entries(pn);
      },
      children: ([m, h]) => {
        const u = s()[m] || [];
        return v(C, {
          get when() {
            return u.length > 0;
          },
          get children() {
            var f = kn(), b = f.firstChild, p = b.firstChild, P = b.nextSibling;
            return a(p, () => h.icon), a(b, () => h.title, null), a(P, v(L, {
              each: u,
              children: (E) => v(Pn, {
                template: E,
                onInsert: r
              })
            })), f;
          }
        });
      }
    }), null), a(o, v(C, {
      get when() {
        return J(() => !!i())() && l().length === 0;
      },
      get children() {
        var m = Sn(), h = m.firstChild, u = h.nextSibling, f = u.firstChild, b = f.nextSibling;
        return b.nextSibling, a(u, i, b), m;
      }
    }), null), a(d, v(C, {
      get when() {
        return e.quickInsertMode;
      },
      get children() {
        return Cn();
      }
    }), null), T(() => H(d, $())), d;
  })();
};
G(["click", "keydown", "input"]);
var Rn = /* @__PURE__ */ _('<div class=equation-description title="Equation description">'), qn = /* @__PURE__ */ _("<div><div class=equation-content><div class=equation-lhs></div><div class=equation-equals aria-label=equals>=</div><div class=equation-rhs>");
const Dn = (e) => {
  const [t, n] = O(null), [i, l] = O(null), s = M(() => {
    const d = e.highlightedVars || /* @__PURE__ */ new Set(), o = i();
    return o && !d.has(o) ? /* @__PURE__ */ new Set([...d, o]) : d;
  }), r = (d) => {
    n(d);
  }, c = (d) => {
    l(d);
  }, g = (d, o) => {
    if (e.readonly || !e.onEquationChange) return;
    const m = structuredClone(e.equation);
    let h = m;
    for (let u = 0; u < d.length - 1; u++)
      h = h[d[u]];
    d.length > 0 && (h[d[d.length - 1]] = o), e.onEquationChange(m);
  }, $ = () => {
    const d = ["equation-editor"];
    return e.readonly && d.push("readonly"), e.class && d.push(e.class), d.join(" ");
  };
  return (() => {
    var d = qn(), o = d.firstChild, m = o.firstChild, h = m.nextSibling, u = h.nextSibling;
    return a(m, v(_e, {
      get expr() {
        return e.equation.lhs;
      },
      path: ["lhs"],
      highlightedVars: () => s(),
      onHoverVar: c,
      onSelect: r,
      onReplace: g,
      get selectedPath() {
        return t();
      }
    })), a(u, v(_e, {
      get expr() {
        return e.equation.rhs;
      },
      path: ["rhs"],
      highlightedVars: () => s(),
      onHoverVar: c,
      onSelect: r,
      onReplace: g,
      get selectedPath() {
        return t();
      }
    })), a(d, v(C, {
      get when() {
        return e.equation.description;
      },
      get children() {
        var f = Rn();
        return a(f, () => e.equation.description), f;
      }
    }), null), T((f) => {
      var b = $(), p = e.id;
      return b !== f.e && H(d, f.e = b), p !== f.t && N(d, "id", f.t = p), f;
    }, {
      e: void 0,
      t: void 0
    }), d;
  })();
};
var Vn = /* @__PURE__ */ _("<div class=variable-unit title=Unit>[<!>]"), Nn = /* @__PURE__ */ _('<div class=variable-default title="Default value">= '), Tn = /* @__PURE__ */ _("<div class=variable-description title=Description>"), Mn = /* @__PURE__ */ _('<button class=variable-remove-btn title="Remove variable">×'), On = /* @__PURE__ */ _("<div role=button tabindex=0><div class=variable-info><div class=variable-header><span class=variable-name></span><span>"), In = /* @__PURE__ */ _('<button class=add-btn title="Add new variable"aria-label="Add new variable">+'), Fn = /* @__PURE__ */ _("<button class=add-first-btn>Add first variable"), jn = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>📊</div><div class=empty-text>No variables defined"), Ln = /* @__PURE__ */ _("<div class=variables-content>"), Hn = /* @__PURE__ */ _("<div class=variables-panel><div class=panel-header><span>▶</span><h3>Variables (<!>)"), Un = /* @__PURE__ */ _("<div class=variable-group><h4 class=group-title><span></span>s (<!>)</h4><div class=variables-list>"), Bn = /* @__PURE__ */ _('<button class=add-btn title="Add new equation"aria-label="Add new equation">+'), Kn = /* @__PURE__ */ _("<button class=add-first-btn>Add first equation"), zn = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚖️</div><div class=empty-text>No equations defined"), Jn = /* @__PURE__ */ _("<div class=equations-content>"), Wn = /* @__PURE__ */ _("<div class=equations-panel><div class=panel-header><span>▶</span><h3>Equations (<!>)"), Gn = /* @__PURE__ */ _('<button class=equation-remove-btn title="Remove equation">×'), Yn = /* @__PURE__ */ _("<div class=equation-item>"), Xn = /* @__PURE__ */ _('<div class=event-add-buttons><button class=add-btn title="Add continuous event">+ Continuous</button><button class=add-btn title="Add discrete event">+ Discrete'), Qn = /* @__PURE__ */ _("<div class=event-group><h4>Continuous Events"), Zn = /* @__PURE__ */ _("<div class=event-group><h4>Discrete Events"), ei = /* @__PURE__ */ _("<div class=empty-actions><button class=add-first-btn>Add continuous event</button><button class=add-first-btn>Add discrete event"), ti = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚡</div><div class=empty-text>No events defined"), ni = /* @__PURE__ */ _("<div class=events-content>"), ii = /* @__PURE__ */ _("<div class=events-panel><div class=panel-header><span>▶</span><h3>Events (<!>)"), et = /* @__PURE__ */ _("<div class=event-description>"), ri = /* @__PURE__ */ _('<div class="event-item continuous"><div class=event-name>'), li = /* @__PURE__ */ _('<div class="event-item discrete"><div class=event-name>'), si = /* @__PURE__ */ _("<div class=model-description>"), ai = /* @__PURE__ */ _("<div class=palette-sidebar>"), oi = /* @__PURE__ */ _("<div><div class=model-editor-layout><div class=model-content><div class=model-header><h2 class=model-name></h2></div><div class=model-panels>");
const Ce = {
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
}, ci = (e) => {
  const [t, n] = O(!1), i = () => Ce[e.type], l = () => {
    var r;
    e.readonly || (r = e.onEdit) == null || r.call(e, e.variable);
  }, s = (r) => {
    var c;
    r.stopPropagation(), e.readonly || (c = e.onRemove) == null || c.call(e, e.variable.name);
  };
  return (() => {
    var r = On(), c = r.firstChild, g = c.firstChild, $ = g.firstChild, d = $.nextSibling;
    return r.$$click = l, r.addEventListener("mouseleave", () => n(!1)), r.addEventListener("mouseenter", () => n(!0)), a($, () => e.variable.name), a(d, () => i().label), a(c, v(C, {
      get when() {
        return e.variable.unit;
      },
      get children() {
        var o = Vn(), m = o.firstChild, h = m.nextSibling;
        return h.nextSibling, a(o, () => e.variable.unit, h), o;
      }
    }), null), a(c, v(C, {
      get when() {
        return e.variable.default_value !== void 0;
      },
      get children() {
        var o = Nn();
        return o.firstChild, a(o, () => e.variable.default_value, null), o;
      }
    }), null), a(c, v(C, {
      get when() {
        return e.variable.description;
      },
      get children() {
        var o = Tn();
        return a(o, () => e.variable.description), o;
      }
    }), null), a(r, v(C, {
      get when() {
        return J(() => !e.readonly)() && t();
      },
      get children() {
        var o = Mn();
        return o.$$click = s, T(() => N(o, "aria-label", `Remove variable ${e.variable.name}`)), o;
      }
    }), null), T((o) => {
      var m = `variable-item ${t() ? "hovered" : ""}`, h = `variable-type-badge ${i().color}`, u = i().description;
      return m !== o.e && H(r, o.e = m), h !== o.t && H(d, o.t = h), u !== o.a && N(d, "title", o.a = u), o;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), r;
  })();
}, di = (e) => {
  const [t, n] = O(!0), i = M(() => {
    const l = e.variables || [], s = {
      state: [],
      parameter: [],
      observed: [],
      other: []
    };
    return l.forEach((r) => {
      const c = "type" in r && r.type ? r.type : "other";
      s[c].push(r);
    }), s;
  });
  return (() => {
    var l = Hn(), s = l.firstChild, r = s.firstChild, c = r.nextSibling, g = c.firstChild, $ = g.nextSibling;
    return $.nextSibling, s.$$click = () => n(!t()), a(c, () => (e.variables || []).length, $), a(s, v(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var d = In();
        return d.$$click = (o) => {
          var m;
          o.stopPropagation(), (m = e.onAddVariable) == null || m.call(e);
        }, d;
      }
    }), null), a(l, v(C, {
      get when() {
        return t();
      },
      get children() {
        var d = Ln();
        return a(d, v(L, {
          get each() {
            return Object.entries(i());
          },
          children: ([o, m]) => v(C, {
            get when() {
              return m.length > 0;
            },
            get children() {
              var h = Un(), u = h.firstChild, f = u.firstChild, b = f.nextSibling, p = b.nextSibling;
              p.nextSibling;
              var P = u.nextSibling;
              return a(f, () => Ce[o].label), a(u, () => Ce[o].description, b), a(u, () => m.length, p), a(P, v(L, {
                each: m,
                children: (E) => v(ci, {
                  variable: E,
                  type: o,
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
              })), T(() => H(f, `group-badge ${Ce[o].color}`)), h;
            }
          })
        }), null), a(d, v(C, {
          get when() {
            return (e.variables || []).length === 0;
          },
          get children() {
            var o = jn(), m = o.firstChild;
            return m.nextSibling, a(o, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = Fn();
                return B(h, "click", e.onAddVariable, !0), h;
              }
            }), null), o;
          }
        }), null), d;
      }
    }), null), T(() => H(r, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, ui = (e) => {
  const [t, n] = O(!0);
  return (() => {
    var i = Wn(), l = i.firstChild, s = l.firstChild, r = s.nextSibling, c = r.firstChild, g = c.nextSibling;
    return g.nextSibling, l.$$click = () => n(!t()), a(r, () => (e.equations || []).length, g), a(l, v(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var $ = Bn();
        return $.$$click = (d) => {
          var o;
          d.stopPropagation(), (o = e.onAddEquation) == null || o.call(e);
        }, $;
      }
    }), null), a(i, v(C, {
      get when() {
        return t();
      },
      get children() {
        var $ = Jn();
        return a($, v(L, {
          get each() {
            return e.equations || [];
          },
          children: (d, o) => (() => {
            var m = Yn();
            return a(m, v(Dn, {
              equation: d,
              get highlightedVars() {
                return e.highlightedVars;
              },
              onEquationChange: (h) => {
                var u;
                return (u = e.onEditEquation) == null ? void 0 : u.call(e, o(), h);
              },
              get readonly() {
                return e.readonly;
              },
              class: "model-equation"
            }), null), a(m, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = Gn();
                return h.$$click = () => {
                  var u;
                  return (u = e.onRemoveEquation) == null ? void 0 : u.call(e, o());
                }, T(() => N(h, "aria-label", `Remove equation ${o() + 1}`)), h;
              }
            }), null), m;
          })()
        }), null), a($, v(C, {
          get when() {
            return (e.equations || []).length === 0;
          },
          get children() {
            var d = zn(), o = d.firstChild;
            return o.nextSibling, a(d, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var m = Kn();
                return B(m, "click", e.onAddEquation, !0), m;
              }
            }), null), d;
          }
        }), null), $;
      }
    }), null), T(() => H(s, `expand-icon ${t() ? "expanded" : ""}`)), i;
  })();
}, hi = (e) => {
  const [t, n] = O(!0), i = () => (e.continuousEvents || []).length + (e.discreteEvents || []).length;
  return (() => {
    var l = ii(), s = l.firstChild, r = s.firstChild, c = r.nextSibling, g = c.firstChild, $ = g.nextSibling;
    return $.nextSibling, s.$$click = () => n(!t()), a(c, i, $), a(s, v(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var d = Xn(), o = d.firstChild, m = o.nextSibling;
        return o.$$click = (h) => {
          var u;
          h.stopPropagation(), (u = e.onAddContinuousEvent) == null || u.call(e);
        }, m.$$click = (h) => {
          var u;
          h.stopPropagation(), (u = e.onAddDiscreteEvent) == null || u.call(e);
        }, d;
      }
    }), null), a(l, v(C, {
      get when() {
        return t();
      },
      get children() {
        var d = ni();
        return a(d, v(C, {
          get when() {
            return (e.continuousEvents || []).length > 0;
          },
          get children() {
            var o = Qn();
            return o.firstChild, a(o, v(L, {
              get each() {
                return e.continuousEvents || [];
              },
              children: (m) => (() => {
                var h = ri(), u = h.firstChild;
                return a(u, () => m.name || "Unnamed Event"), a(h, v(C, {
                  get when() {
                    return m.description;
                  },
                  get children() {
                    var f = et();
                    return a(f, () => m.description), f;
                  }
                }), null), h;
              })()
            }), null), o;
          }
        }), null), a(d, v(C, {
          get when() {
            return (e.discreteEvents || []).length > 0;
          },
          get children() {
            var o = Zn();
            return o.firstChild, a(o, v(L, {
              get each() {
                return e.discreteEvents || [];
              },
              children: (m) => (() => {
                var h = li(), u = h.firstChild;
                return a(u, () => m.name || "Unnamed Event"), a(h, v(C, {
                  get when() {
                    return m.description;
                  },
                  get children() {
                    var f = et();
                    return a(f, () => m.description), f;
                  }
                }), null), h;
              })()
            }), null), o;
          }
        }), null), a(d, v(C, {
          get when() {
            return i() === 0;
          },
          get children() {
            var o = ti(), m = o.firstChild;
            return m.nextSibling, a(o, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = ei(), u = h.firstChild, f = u.nextSibling;
                return B(u, "click", e.onAddContinuousEvent, !0), B(f, "click", e.onAddDiscreteEvent, !0), h;
              }
            }), null), o;
          }
        }), null), d;
      }
    }), null), T(() => H(r, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, fi = (e) => {
  const [t, n] = O(/* @__PURE__ */ new Set()), i = (h) => {
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
    const u = (e.model.variables || []).filter((f) => f.name !== h);
    i({
      variables: u
    });
  }, c = () => {
    const h = {
      lhs: "_placeholder_",
      rhs: 0
    }, u = [...e.model.equations || [], h];
    i({
      equations: u
    });
  }, g = (h, u) => {
    const f = [...e.model.equations || []];
    f[h] = u, i({
      equations: f
    });
  }, $ = (h) => {
    const u = (e.model.equations || []).filter((f, b) => b !== h);
    i({
      equations: u
    });
  }, d = () => {
    console.log("Add continuous event");
  }, o = () => {
    console.log("Add discrete event");
  }, m = () => {
    const h = ["model-editor"];
    return e.readonly && h.push("readonly"), e.class && h.push(e.class), h.join(" ");
  };
  return (() => {
    var h = oi(), u = h.firstChild, f = u.firstChild, b = f.firstChild, p = b.firstChild, P = b.nextSibling;
    return a(p, () => e.model.name || "Untitled Model"), a(b, v(C, {
      get when() {
        return e.model.description;
      },
      get children() {
        var E = si();
        return a(E, () => e.model.description), E;
      }
    }), null), a(P, v(di, {
      get variables() {
        return e.model.variables;
      },
      onAddVariable: l,
      onEditVariable: s,
      onRemoveVariable: r,
      get readonly() {
        return e.readonly;
      }
    }), null), a(P, v(ui, {
      get equations() {
        return e.model.equations;
      },
      get highlightedVars() {
        return t();
      },
      onAddEquation: c,
      onEditEquation: g,
      onRemoveEquation: $,
      get readonly() {
        return e.readonly;
      }
    }), null), a(P, v(hi, {
      get continuousEvents() {
        return e.model.continuous_events;
      },
      get discreteEvents() {
        return e.model.discrete_events;
      },
      onAddContinuousEvent: d,
      onAddDiscreteEvent: o,
      get readonly() {
        return e.readonly;
      }
    }), null), a(u, v(C, {
      get when() {
        return J(() => !!e.showPalette)() && !e.readonly;
      },
      get children() {
        var E = ai();
        return a(E, v(gt, {
          get currentModel() {
            return e.model;
          },
          visible: !0
        })), E;
      }
    }), null), T(() => H(h, m())), h;
  })();
};
G(["click"]);
var gi = /* @__PURE__ */ _('<span class=reaction-name title="Reaction name">'), mi = /* @__PURE__ */ _('<button class=reaction-remove-btn title="Remove reaction">×'), $i = /* @__PURE__ */ _('<div class=reaction-rate-editor><div class=rate-editor-header><span>Rate Expression:</span><button class=collapse-btn title="Collapse rate editor">▲</button></div><div class=rate-editor-content>'), vi = /* @__PURE__ */ _("<div class=reaction-description>"), _i = /* @__PURE__ */ _("<div class=reaction-item><div class=reaction-header><div class=reaction-equation><span class=reactants></span><span class=reaction-arrow>→<span>[<!>]</span></span><span class=products></span></div><div class=reaction-controls>"), bi = /* @__PURE__ */ _("<div class=no-rate-placeholder><span>No rate expression defined</span><button class=add-rate-btn>Add rate constant"), yi = /* @__PURE__ */ _('<button class=add-btn title="Add new species"aria-label="Add new species">+'), xi = /* @__PURE__ */ _("<button class=add-first-btn>Add first species"), wi = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>🧪</div><div class=empty-text>No species defined"), Si = /* @__PURE__ */ _("<div class=species-content>"), Ci = /* @__PURE__ */ _("<div class=species-panel><div class=panel-header><span>▶</span><h3>Species (<!>)"), Ei = /* @__PURE__ */ _("<span class=species-name>(<!>)"), ki = /* @__PURE__ */ _("<div class=species-description>"), pi = /* @__PURE__ */ _('<button class=species-remove-btn title="Remove species">×'), Pi = /* @__PURE__ */ _("<div class=species-item><div class=species-info><span class=species-formula>"), Ai = /* @__PURE__ */ _('<button class=add-btn title="Add new parameter"aria-label="Add new parameter">+'), Ri = /* @__PURE__ */ _("<button class=add-first-btn>Add first parameter"), qi = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚗️</div><div class=empty-text>No parameters defined"), Di = /* @__PURE__ */ _("<div class=parameters-content>"), Vi = /* @__PURE__ */ _("<div class=parameters-panel><div class=panel-header><span>▶</span><h3>Parameters (<!>)"), Ni = /* @__PURE__ */ _("<span class=parameter-unit>[<!>]"), Ti = /* @__PURE__ */ _("<span class=parameter-value>= "), Mi = /* @__PURE__ */ _("<div class=parameter-description>"), Oi = /* @__PURE__ */ _('<button class=parameter-remove-btn title="Remove parameter">×'), Ii = /* @__PURE__ */ _("<div class=parameter-item><div class=parameter-info><span class=parameter-name>"), Fi = /* @__PURE__ */ _('<button class=add-reaction-btn title="Add new reaction">+ Add Reaction'), ji = /* @__PURE__ */ _("<button class=add-first-btn>Add first reaction"), Li = /* @__PURE__ */ _("<div class=empty-state><div class=empty-icon>⚛️</div><div class=empty-text>No reactions defined"), Hi = /* @__PURE__ */ _("<div><div class=reaction-editor-layout><div class=reactions-main><div class=reactions-header><h2>Reactions (<!>)</h2></div><div class=reactions-list></div></div><div class=reaction-sidebar>");
const Oe = (e) => e.replace(/(\d+)/g, (t) => {
  const n = "₀₁₂₃₄₅₆₇₈₉";
  return t.split("").map((i) => n[parseInt(i, 10)]).join("");
}), Ui = (e) => {
  const [t, n] = O(!1), [i, l] = O(null), [s, r] = O(null), c = M(() => {
    const u = /* @__PURE__ */ new Map();
    return e.species.forEach((f) => {
      u.set(f.name, f);
    }), u;
  }), g = M(() => {
    const u = e.highlightedVars || /* @__PURE__ */ new Set(), f = s();
    return f && !u.has(f) ? /* @__PURE__ */ new Set([...u, f]) : u;
  }), $ = () => e.reaction.reactants ? e.reaction.reactants.map((u, f) => {
    const b = c().get(u.species), p = (b == null ? void 0 : b.formula) || u.species, P = u.stoichiometry !== void 0 ? u.stoichiometry : 1;
    return `${P > 1 ? P : ""}${Oe(p)}`;
  }).join(" + ") : "", d = () => e.reaction.products ? e.reaction.products.map((u, f) => {
    const b = c().get(u.species), p = (b == null ? void 0 : b.formula) || u.species, P = u.stoichiometry !== void 0 ? u.stoichiometry : 1;
    return `${P > 1 ? P : ""}${Oe(p)}`;
  }).join(" + ") : "", o = () => {
    e.readonly || n(!t());
  }, m = (u) => {
    if (e.readonly || !e.onEditReaction) return;
    const f = {
      ...e.reaction,
      rate: u
    };
    e.onEditReaction(e.index, f);
  }, h = () => {
    var u;
    e.readonly || (u = e.onRemoveReaction) == null || u.call(e, e.index);
  };
  return (() => {
    var u = _i(), f = u.firstChild, b = f.firstChild, p = b.firstChild, P = p.nextSibling, E = P.firstChild, y = E.nextSibling, x = y.firstChild, R = x.nextSibling;
    R.nextSibling;
    var V = P.nextSibling, k = b.nextSibling;
    return a(p, $), y.$$click = o, a(y, () => e.reaction.rate ? "k" : "?", R), a(V, d), a(k, v(C, {
      get when() {
        return e.reaction.name;
      },
      get children() {
        var q = gi();
        return a(q, () => e.reaction.name), q;
      }
    }), null), a(k, v(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var q = mi();
        return q.$$click = h, T(() => N(q, "aria-label", `Remove reaction ${e.index + 1}`)), q;
      }
    }), null), a(u, v(C, {
      get when() {
        return t();
      },
      get children() {
        var q = $i(), w = q.firstChild, S = w.firstChild, D = S.nextSibling, I = w.nextSibling;
        return D.$$click = () => n(!1), a(I, v(C, {
          get when() {
            return e.reaction.rate;
          },
          get fallback() {
            return (() => {
              var A = bi(), F = A.firstChild, U = F.nextSibling;
              return U.$$click = () => m("k_rate"), A;
            })();
          },
          get children() {
            return v(_e, {
              get expr() {
                return e.reaction.rate;
              },
              path: ["rate"],
              highlightedVars: () => g(),
              onHoverVar: r,
              onSelect: l,
              onReplace: (A, F) => {
                A.length === 1 && A[0] === "rate" && m(F);
              },
              get selectedPath() {
                return i();
              }
            });
          }
        })), q;
      }
    }), null), a(u, v(C, {
      get when() {
        return e.reaction.description;
      },
      get children() {
        var q = vi();
        return a(q, () => e.reaction.description), q;
      }
    }), null), T((q) => {
      var w = `rate-expression ${t() ? "expanded" : ""} ${e.readonly ? "" : "clickable"}`, S = e.readonly ? void 0 : "Click to edit rate expression";
      return w !== q.e && H(y, q.e = w), S !== q.t && N(y, "title", q.t = S), q;
    }, {
      e: void 0,
      t: void 0
    }), u;
  })();
}, Bi = (e) => {
  const [t, n] = O(!0);
  return (() => {
    var i = Ci(), l = i.firstChild, s = l.firstChild, r = s.nextSibling, c = r.firstChild, g = c.nextSibling;
    return g.nextSibling, l.$$click = () => n(!t()), a(r, () => (e.species || []).length, g), a(l, v(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var $ = yi();
        return $.$$click = (d) => {
          var o;
          d.stopPropagation(), (o = e.onAddSpecies) == null || o.call(e);
        }, $;
      }
    }), null), a(i, v(C, {
      get when() {
        return t();
      },
      get children() {
        var $ = Si();
        return a($, v(L, {
          get each() {
            return e.species || [];
          },
          children: (d) => (() => {
            var o = Pi(), m = o.firstChild, h = m.firstChild;
            return o.$$click = () => {
              var u;
              return (u = e.onEditSpecies) == null ? void 0 : u.call(e, d);
            }, a(h, () => Oe(d.formula || d.name)), a(m, v(C, {
              get when() {
                return d.name !== d.formula;
              },
              get children() {
                var u = Ei(), f = u.firstChild, b = f.nextSibling;
                return b.nextSibling, a(u, () => d.name, b), u;
              }
            }), null), a(o, v(C, {
              get when() {
                return d.description;
              },
              get children() {
                var u = ki();
                return a(u, () => d.description), u;
              }
            }), null), a(o, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var u = pi();
                return u.$$click = (f) => {
                  var b;
                  f.stopPropagation(), (b = e.onRemoveSpecies) == null || b.call(e, d.name);
                }, T(() => N(u, "aria-label", `Remove species ${d.name}`)), u;
              }
            }), null), o;
          })()
        }), null), a($, v(C, {
          get when() {
            return (e.species || []).length === 0;
          },
          get children() {
            var d = wi(), o = d.firstChild;
            return o.nextSibling, a(d, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var m = xi();
                return B(m, "click", e.onAddSpecies, !0), m;
              }
            }), null), d;
          }
        }), null), $;
      }
    }), null), T(() => H(s, `expand-icon ${t() ? "expanded" : ""}`)), i;
  })();
}, Ki = (e) => {
  const [t, n] = O(!0), i = M(() => (e.parameters || []).filter((l) => l.name.startsWith("k_") || l.name.includes("rate") || l.name.includes("const")));
  return (() => {
    var l = Vi(), s = l.firstChild, r = s.firstChild, c = r.nextSibling, g = c.firstChild, $ = g.nextSibling;
    return $.nextSibling, s.$$click = () => n(!t()), a(c, () => i().length, $), a(s, v(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var d = Ai();
        return d.$$click = (o) => {
          var m;
          o.stopPropagation(), (m = e.onAddParameter) == null || m.call(e);
        }, d;
      }
    }), null), a(l, v(C, {
      get when() {
        return t();
      },
      get children() {
        var d = Di();
        return a(d, v(L, {
          get each() {
            return i();
          },
          children: (o) => (() => {
            var m = Ii(), h = m.firstChild, u = h.firstChild;
            return m.$$click = () => {
              var f;
              return (f = e.onEditParameter) == null ? void 0 : f.call(e, o);
            }, a(u, () => o.name), a(h, v(C, {
              get when() {
                return o.unit;
              },
              get children() {
                var f = Ni(), b = f.firstChild, p = b.nextSibling;
                return p.nextSibling, a(f, () => o.unit, p), f;
              }
            }), null), a(h, v(C, {
              get when() {
                return o.default_value !== void 0;
              },
              get children() {
                var f = Ti();
                return f.firstChild, a(f, () => o.default_value, null), f;
              }
            }), null), a(m, v(C, {
              get when() {
                return o.description;
              },
              get children() {
                var f = Mi();
                return a(f, () => o.description), f;
              }
            }), null), a(m, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var f = Oi();
                return f.$$click = (b) => {
                  var p;
                  b.stopPropagation(), (p = e.onRemoveParameter) == null || p.call(e, o.name);
                }, T(() => N(f, "aria-label", `Remove parameter ${o.name}`)), f;
              }
            }), null), m;
          })()
        }), null), a(d, v(C, {
          get when() {
            return i().length === 0;
          },
          get children() {
            var o = qi(), m = o.firstChild;
            return m.nextSibling, a(o, v(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var h = Ri();
                return B(h, "click", e.onAddParameter, !0), h;
              }
            }), null), o;
          }
        }), null), d;
      }
    }), null), T(() => H(r, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, zi = (e) => {
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
    const h = (e.reactionSystem.reactions || []).filter((u, f) => f !== m);
    t({
      reactions: h
    });
  }, s = () => {
    console.log("Add species");
  }, r = (m) => {
    console.log("Edit species:", m.name);
  }, c = (m) => {
    const h = (e.reactionSystem.species || []).filter((u) => u.name !== m);
    t({
      species: h
    });
  }, g = () => {
    console.log("Add parameter");
  }, $ = (m) => {
    console.log("Edit parameter:", m.name);
  }, d = (m) => {
    console.log("Remove parameter:", m);
  }, o = () => {
    const m = ["reaction-editor"];
    return e.readonly && m.push("readonly"), e.class && m.push(e.class), m.join(" ");
  };
  return (() => {
    var m = Hi(), h = m.firstChild, u = h.firstChild, f = u.firstChild, b = f.firstChild, p = b.firstChild, P = p.nextSibling;
    P.nextSibling;
    var E = f.nextSibling, y = u.nextSibling;
    return a(b, () => (e.reactionSystem.reactions || []).length, P), a(f, v(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var x = Fi();
        return x.$$click = n, x;
      }
    }), null), a(E, v(L, {
      get each() {
        return e.reactionSystem.reactions || [];
      },
      children: (x, R) => v(Ui, {
        reaction: x,
        get index() {
          return R();
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
    }), null), a(E, v(C, {
      get when() {
        return (e.reactionSystem.reactions || []).length === 0;
      },
      get children() {
        var x = Li(), R = x.firstChild;
        return R.nextSibling, a(x, v(C, {
          get when() {
            return !e.readonly;
          },
          get children() {
            var V = ji();
            return V.$$click = n, V;
          }
        }), null), x;
      }
    }), null), a(y, v(Bi, {
      get species() {
        return e.reactionSystem.species;
      },
      onAddSpecies: s,
      onEditSpecies: r,
      onRemoveSpecies: c,
      get readonly() {
        return e.readonly;
      }
    }), null), a(y, v(Ki, {
      parameters: [],
      onAddParameter: g,
      onEditParameter: $,
      onRemoveParameter: d,
      get readonly() {
        return e.readonly;
      }
    }), null), T(() => H(m, o())), m;
  })();
};
G(["click"]);
var Ji = /* @__PURE__ */ _("<svg><rect width=50 height=30></svg>", !1, !0, !1), Wi = /* @__PURE__ */ _("<svg><ellipse rx=25 ry=15></svg>", !1, !0, !1), Gi = /* @__PURE__ */ _("<svg><polygon></svg>", !1, !0, !1), Yi = /* @__PURE__ */ _("<svg><circle r=20></svg>", !1, !0, !1), Xi = /* @__PURE__ */ _("<svg><line></svg>", !1, !0, !1), Qi = /* @__PURE__ */ _('<div class="absolute top-4 right-4 border border-gray-300 bg-white bg-opacity-90"><svg width=150 height=150><rect width=100% height=100% fill=white stroke=gray></rect><rect fill=none stroke=red stroke-width=1>'), Zi = /* @__PURE__ */ _("<svg><circle r=2></svg>", !1, !0, !1), tt = /* @__PURE__ */ _('<p class="text-sm mt-2">'), er = /* @__PURE__ */ _("<div>Species: "), tr = /* @__PURE__ */ _('<div><h3 class="font-bold text-lg"></h3><p class="text-sm text-gray-600">Type: </p><div class="text-xs mt-2"><div>Variables: </div><div>Equations: '), nr = /* @__PURE__ */ _('<div><h3 class="font-bold text-lg"></h3><p class="text-sm text-gray-600">Type: </p><p class=text-sm>From: <!> → To: '), ir = /* @__PURE__ */ _('<div class="absolute bottom-4 left-4 p-4 bg-white border border-gray-300 rounded shadow-lg max-w-md"><button class="mt-2 px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded">Close'), rr = /* @__PURE__ */ _('<div class="relative w-full h-full"><svg class="border border-gray-300"><defs><marker id=arrowhead markerWidth=10 markerHeight=7 refX=9 refY=3.5 orient=auto><polygon points="0 0, 10 3.5, 0 7"fill=#999></polygon></marker></defs><g class=edges></g><g class=nodes></g><g class=labels>'), lr = /* @__PURE__ */ _("<svg><text text-anchor=middle font-size=12 fill=black pointer-events=none></svg>", !1, !0, !1);
const sr = (e) => {
  const t = () => e.width ?? 800, n = () => e.height ?? 600, i = M(() => [...e.graph.nodes]), l = M(() => e.graph.edges.map((w) => ({
    source: w.source,
    target: w.target,
    data: w.data
  }))), [s, r] = O(null), [c, g] = O(null), [$, d] = O(null), [o, m] = O({
    x: 0,
    y: 0,
    k: 1
  });
  let h, u;
  const f = () => {
    const w = i(), S = l();
    u = At(w).force("link", Rt(S).id((D) => D.id).distance(100).strength(0.1)).force("charge", qt().strength(-300)).force("center", Dt(t() / 2, n() / 2)).force("collision", Vt().radius(30)).on("tick", () => {
      b([...w]);
    }), w.forEach((D) => {
      D.x === void 0 && (D.x = t() / 2 + (Math.random() - 0.5) * 100), D.y === void 0 && (D.y = n() / 2 + (Math.random() - 0.5) * 100);
    });
  }, [, b] = O(i(), {
    equals: !1
  }), p = (w) => {
    var D;
    const S = {
      stroke: "#333",
      "stroke-width": ((D = s()) == null ? void 0 : D.id) === w.id ? 3 : 1,
      cursor: "pointer",
      filter: $() === w.id ? "brightness(1.2)" : "none"
    };
    switch (w.type) {
      case "model":
        return {
          ...S,
          fill: "#4CAF50",
          rx: 5,
          ry: 5
        };
      case "data_loader":
        return {
          ...S,
          fill: "#2196F3"
        };
      case "operator":
        return {
          ...S,
          fill: "#FF9800"
        };
      case "reaction_system":
        return {
          ...S,
          fill: "#9C27B0"
        };
      default:
        return {
          ...S,
          fill: "#607D8B"
        };
    }
  }, P = (w) => {
    var D;
    const S = {
      stroke: "#999",
      "stroke-width": ((D = c()) == null ? void 0 : D.id) === w.id ? 3 : 1,
      cursor: "pointer",
      "marker-end": "url(#arrowhead)",
      filter: $() === w.id ? "brightness(1.5)" : "none"
    };
    switch (w.type) {
      case "variable":
        return {
          ...S,
          "stroke-dasharray": "none"
        };
      case "temporal":
        return {
          ...S,
          "stroke-dasharray": "5,5"
        };
      case "spatial":
        return {
          ...S,
          "stroke-dasharray": "10,2"
        };
      default:
        return S;
    }
  }, E = (w) => {
    var S;
    r((D) => (D == null ? void 0 : D.id) === w.id ? null : w), g(null), (S = e.onNodeSelect) == null || S.call(e, w);
  }, y = (w) => {
    var S;
    g((D) => (D == null ? void 0 : D.id) === w.id ? null : w), r(null), (S = e.onEdgeSelect) == null || S.call(e, w);
  }, x = (w, S) => {
    u && (w.fx = S.offsetX, w.fy = S.offsetY, u.alpha(0.3).restart());
  }, R = (w) => {
    w.preventDefault();
    const S = w.deltaY > 0 ? 0.9 : 1.1, D = o();
    m({
      ...D,
      k: Math.max(0.1, Math.min(3, D.k * S))
    });
  };
  pt(() => {
    f(), h && h.addEventListener("wheel", R, {
      passive: !1
    });
  }), ye(() => {
    u == null || u.stop(), h && h.removeEventListener("wheel", R);
  }), M(() => {
    if (u) {
      u.nodes(i());
      const w = u.force("link");
      w && "links" in w && w.links(l()), u.alpha(0.3).restart();
    }
  });
  const V = (w) => {
    const S = p(w), D = w.x ?? 0, I = w.y ?? 0;
    switch (w.type) {
      case "model":
      case "reaction_system":
        return (() => {
          var A = Ji();
          return N(A, "x", D - 25), N(A, "y", I - 15), me(A, fe(S, {
            onClick: () => E(w),
            onMouseEnter: () => d(w.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(w, F)
          }), !0), A;
        })();
      case "data_loader":
        return (() => {
          var A = Wi();
          return N(A, "cx", D), N(A, "cy", I), me(A, fe(S, {
            onClick: () => E(w),
            onMouseEnter: () => d(w.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(w, F)
          }), !0), A;
        })();
      case "operator":
        return (() => {
          var A = Gi();
          return N(A, "points", `${D},${I - 20} ${D + 20},${I} ${D},${I + 20} ${D - 20},${I}`), me(A, fe(S, {
            onClick: () => E(w),
            onMouseEnter: () => d(w.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(w, F)
          }), !0), A;
        })();
      default:
        return (() => {
          var A = Yi();
          return N(A, "cx", D), N(A, "cy", I), me(A, fe(S, {
            onClick: () => E(w),
            onMouseEnter: () => d(w.id),
            onMouseLeave: () => d(null),
            onMouseDown: (F) => x(w, F)
          }), !0), A;
        })();
    }
  }, k = (w) => {
    const S = typeof w.source == "object" ? w.source : i().find((A) => A.id === w.source), D = typeof w.target == "object" ? w.target : i().find((A) => A.id === w.target);
    if (!(S != null && S.x) || !(S != null && S.y) || !(D != null && D.x) || !(D != null && D.y)) return null;
    const I = P(w.data);
    return (() => {
      var A = Xi();
      return me(A, fe({
        get x1() {
          return S.x;
        },
        get y1() {
          return S.y;
        },
        get x2() {
          return D.x;
        },
        get y2() {
          return D.y;
        }
      }, I, {
        onClick: () => y(w.data),
        onMouseEnter: () => d(w.data.id),
        onMouseLeave: () => d(null)
      }), !0), A;
    })();
  }, q = () => {
    const S = Math.min(150 / t(), 150 / n());
    return (() => {
      var D = Qi(), I = D.firstChild, A = I.firstChild, F = A.nextSibling;
      return a(I, v(L, {
        get each() {
          return i();
        },
        children: (U) => (() => {
          var j = Zi();
          return T((K) => {
            var z = (U.x ?? 0) * S, W = (U.y ?? 0) * S, Y = p(U).fill;
            return z !== K.e && N(j, "cx", K.e = z), W !== K.t && N(j, "cy", K.t = W), Y !== K.a && N(j, "fill", K.a = Y), K;
          }, {
            e: void 0,
            t: void 0,
            a: void 0
          }), j;
        })()
      }), F), T((U) => {
        var j = -o().x * S, K = -o().y * S, z = t() * S / o().k, W = n() * S / o().k;
        return j !== U.e && N(F, "x", U.e = j), K !== U.t && N(F, "y", U.t = K), z !== U.a && N(F, "width", U.a = z), W !== U.o && N(F, "height", U.o = W), U;
      }, {
        e: void 0,
        t: void 0,
        a: void 0,
        o: void 0
      }), D;
    })();
  };
  return (() => {
    var w = rr(), S = w.firstChild, D = S.firstChild, I = D.nextSibling, A = I.nextSibling, F = A.nextSibling, U = h;
    return typeof U == "function" ? Le(U, S) : h = S, a(I, v(L, {
      get each() {
        return l();
      },
      children: (j) => k(j)
    })), a(A, v(L, {
      get each() {
        return i();
      },
      children: (j) => V(j)
    })), a(F, v(L, {
      get each() {
        return i();
      },
      children: (j) => (() => {
        var K = lr();
        return a(K, () => j.name), T((z) => {
          var W = j.x ?? 0, Y = (j.y ?? 0) + 40;
          return W !== z.e && N(K, "x", z.e = W), Y !== z.t && N(K, "y", z.t = Y), z;
        }, {
          e: void 0,
          t: void 0
        }), K;
      })()
    })), a(w, v(C, {
      get when() {
        return e.showMinimap !== !1;
      },
      get children() {
        return v(q, {});
      }
    }), null), a(w, v(C, {
      get when() {
        return s() || c();
      },
      get children() {
        var j = ir(), K = j.firstChild;
        return a(j, v(C, {
          get when() {
            return s();
          },
          get children() {
            var z = tr(), W = z.firstChild, Y = W.nextSibling;
            Y.firstChild;
            var ee = Y.nextSibling, ue = ee.firstChild;
            ue.firstChild;
            var he = ue.nextSibling;
            return he.firstChild, a(W, () => s().name), a(Y, () => s().type, null), a(z, v(C, {
              get when() {
                return s().description;
              },
              get children() {
                var X = tt();
                return a(X, () => s().description), X;
              }
            }), ee), a(ue, () => s().metadata.var_count, null), a(he, () => s().metadata.eq_count, null), a(ee, v(C, {
              get when() {
                return s().metadata.species_count > 0;
              },
              get children() {
                var X = er();
                return X.firstChild, a(X, () => s().metadata.species_count, null), X;
              }
            }), null), z;
          }
        }), K), a(j, v(C, {
          get when() {
            return c();
          },
          get children() {
            var z = nr(), W = z.firstChild, Y = W.nextSibling;
            Y.firstChild;
            var ee = Y.nextSibling, ue = ee.firstChild, he = ue.nextSibling;
            return he.nextSibling, a(W, () => c().label), a(Y, () => c().type, null), a(ee, () => c().from, he), a(ee, () => c().to, null), a(z, v(C, {
              get when() {
                return c().description;
              },
              get children() {
                var X = tt();
                return a(X, () => c().description), X;
              }
            }), null), z;
          }
        }), K), K.$$click = () => {
          r(null), g(null);
        }, j;
      }
    }), null), T((j) => {
      var K = t(), z = n(), W = `transform: translate(${o().x}px, ${o().y}px) scale(${o().k})`;
      return K !== j.e && N(S, "width", j.e = K), z !== j.t && N(S, "height", j.t = z), j.a = ct(S, W, j.a), j;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), w;
  })();
};
G(["click"]);
var ar = /* @__PURE__ */ _("<span class=error-badge>"), or = /* @__PURE__ */ _("<span class=warning-badge>"), cr = /* @__PURE__ */ _('<span class=success-badge title="No errors found">✓'), dr = /* @__PURE__ */ _("<div class=validation-success><span class=success-icon>✓</span>No validation errors found. The ESM file is valid."), ur = /* @__PURE__ */ _('<div class=error-section><h4 class="error-section-title error-title">Schema Errors (<!>)</h4><div class=error-list>'), hr = /* @__PURE__ */ _('<div class=error-section><h4 class="error-section-title error-title">Structural Errors (<!>)</h4><div class=error-list>'), fr = /* @__PURE__ */ _('<div class=error-section><h4 class="error-section-title warning-title">Warnings (<!>)</h4><div class=error-list>'), gr = /* @__PURE__ */ _("<div class=validation-content>"), mr = /* @__PURE__ */ _("<div><div class=validation-header><h3 class=validation-title>Validation Results</h3><button class=collapse-toggle>"), qe = /* @__PURE__ */ _("<div class=error-details>"), nt = /* @__PURE__ */ _('<div class="error-item error-severity clickable"role=button tabindex=0><div class=error-header><span class=error-icon>🔴</span><span class=error-code></span><span class=error-path></span></div><div class=error-message>'), De = /* @__PURE__ */ _("<div class=error-detail><strong>:</strong> "), $r = /* @__PURE__ */ _('<div class="error-item warning-severity clickable"role=button tabindex=0><div class=error-header><span class=error-icon>🟡</span><span class=error-code></span><span class=error-path></span></div><div class=error-message>');
function vr(e) {
  return "error";
}
const yl = (e) => {
  const t = M(() => ot(e.esmFile)), n = M(() => {
    const d = t(), o = [];
    return d.schema_errors.forEach((m) => {
      o.push({
        ...m,
        severity: "error",
        type: "schema"
      });
    }), d.structural_errors.forEach((m) => {
      o.push({
        ...m,
        severity: vr(),
        type: "structural"
      });
    }), o;
  }), i = M(() => {
    const d = n();
    return {
      errors: d.filter((o) => o.severity === "error"),
      warnings: d.filter((o) => o.severity === "warning")
    };
  }), l = M(() => i().errors.length), s = M(() => i().warnings.length), r = M(() => t().is_valid), c = (d) => {
    e.onErrorClick && e.onErrorClick(d.path);
  }, g = () => {
    e.onToggleCollapsed && e.onToggleCollapsed(!e.collapsed);
  }, $ = () => {
    const d = ["validation-panel"];
    return e.collapsed && d.push("collapsed"), r() ? d.push("valid") : d.push("invalid"), e.class && d.push(e.class), d.join(" ");
  };
  return (() => {
    var d = mr(), o = d.firstChild, m = o.firstChild;
    m.firstChild;
    var h = m.nextSibling;
    return o.$$click = g, a(m, v(C, {
      get when() {
        return l() > 0;
      },
      get children() {
        var u = ar();
        return a(u, l), T(() => N(u, "title", `${l()} error(s)`)), u;
      }
    }), null), a(m, v(C, {
      get when() {
        return s() > 0;
      },
      get children() {
        var u = or();
        return a(u, s), T(() => N(u, "title", `${s()} warning(s)`)), u;
      }
    }), null), a(m, v(C, {
      get when() {
        return r();
      },
      get children() {
        return cr();
      }
    }), null), a(h, () => e.collapsed ? "▶" : "▼"), a(d, v(C, {
      get when() {
        return !e.collapsed;
      },
      get children() {
        var u = gr();
        return a(u, v(C, {
          get when() {
            return r();
          },
          get children() {
            return dr();
          }
        }), null), a(u, v(C, {
          get when() {
            return !r();
          },
          get children() {
            return [v(C, {
              get when() {
                return i().errors.filter((f) => f.type === "schema").length > 0;
              },
              get children() {
                var f = ur(), b = f.firstChild, p = b.firstChild, P = p.nextSibling;
                P.nextSibling;
                var E = b.nextSibling;
                return a(b, () => i().errors.filter((y) => y.type === "schema").length, P), a(E, v(L, {
                  get each() {
                    return i().errors.filter((y) => y.type === "schema");
                  },
                  children: (y) => (() => {
                    var x = nt(), R = x.firstChild, V = R.firstChild, k = V.nextSibling, q = k.nextSibling, w = R.nextSibling;
                    return x.$$keydown = (S) => {
                      (S.key === "Enter" || S.key === " ") && (S.preventDefault(), c(y));
                    }, x.$$click = () => c(y), a(k, () => y.code), a(q, () => y.path || "$"), a(w, () => y.message), a(x, v(C, {
                      get when() {
                        return Object.keys(y.details).length > 0;
                      },
                      get children() {
                        var S = qe();
                        return a(S, v(L, {
                          get each() {
                            return Object.entries(y.details);
                          },
                          children: ([D, I]) => (() => {
                            var A = De(), F = A.firstChild, U = F.firstChild;
                            return F.nextSibling, a(F, D, U), a(A, () => String(I), null), A;
                          })()
                        })), S;
                      }
                    }), null), T(() => N(q, "title", `Path: ${y.path}`)), x;
                  })()
                })), f;
              }
            }), v(C, {
              get when() {
                return i().errors.filter((f) => f.type === "structural").length > 0;
              },
              get children() {
                var f = hr(), b = f.firstChild, p = b.firstChild, P = p.nextSibling;
                P.nextSibling;
                var E = b.nextSibling;
                return a(b, () => i().errors.filter((y) => y.type === "structural").length, P), a(E, v(L, {
                  get each() {
                    return i().errors.filter((y) => y.type === "structural");
                  },
                  children: (y) => (() => {
                    var x = nt(), R = x.firstChild, V = R.firstChild, k = V.nextSibling, q = k.nextSibling, w = R.nextSibling;
                    return x.$$keydown = (S) => {
                      (S.key === "Enter" || S.key === " ") && (S.preventDefault(), c(y));
                    }, x.$$click = () => c(y), a(k, () => y.code), a(q, () => y.path || "$"), a(w, () => y.message), a(x, v(C, {
                      get when() {
                        return Object.keys(y.details).length > 0;
                      },
                      get children() {
                        var S = qe();
                        return a(S, v(L, {
                          get each() {
                            return Object.entries(y.details);
                          },
                          children: ([D, I]) => (() => {
                            var A = De(), F = A.firstChild, U = F.firstChild;
                            return F.nextSibling, a(F, D, U), a(A, () => String(I), null), A;
                          })()
                        })), S;
                      }
                    }), null), T(() => N(q, "title", `Path: ${y.path}`)), x;
                  })()
                })), f;
              }
            }), v(C, {
              get when() {
                return s() > 0;
              },
              get children() {
                var f = fr(), b = f.firstChild, p = b.firstChild, P = p.nextSibling;
                P.nextSibling;
                var E = b.nextSibling;
                return a(b, s, P), a(E, v(L, {
                  get each() {
                    return i().warnings;
                  },
                  children: (y) => (() => {
                    var x = $r(), R = x.firstChild, V = R.firstChild, k = V.nextSibling, q = k.nextSibling, w = R.nextSibling;
                    return x.$$keydown = (S) => {
                      (S.key === "Enter" || S.key === " ") && (S.preventDefault(), c(y));
                    }, x.$$click = () => c(y), a(k, () => y.code), a(q, () => y.path || "$"), a(w, () => y.message), a(x, v(C, {
                      get when() {
                        return Object.keys(y.details).length > 0;
                      },
                      get children() {
                        var S = qe();
                        return a(S, v(L, {
                          get each() {
                            return Object.entries(y.details);
                          },
                          children: ([D, I]) => (() => {
                            var A = De(), F = A.firstChild, U = F.firstChild;
                            return F.nextSibling, a(F, D, U), a(A, () => String(I), null), A;
                          })()
                        })), S;
                      }
                    }), null), T(() => N(q, "title", `Path: ${y.path}`)), x;
                  })()
                })), f;
              }
            })];
          }
        }), null), u;
      }
    }), null), T((u) => {
      var f = $(), b = e.collapsed ? "Expand validation panel" : "Collapse validation panel";
      return f !== u.e && H(d, u.e = f), b !== u.t && N(h, "aria-label", u.t = b), u;
    }, {
      e: void 0,
      t: void 0
    }), d;
  })();
};
G(["click", "keydown"]);
var _r = /* @__PURE__ */ _("<div class=info-item><strong>Title:</strong> "), br = /* @__PURE__ */ _("<div class=info-item><strong>Description:</strong> "), yr = /* @__PURE__ */ _("<div class=info-item><strong>Authors:</strong> "), xr = /* @__PURE__ */ _("<div class=info-item><strong>Created:</strong> "), wr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Models (<!>) →</h4><div class=section-content>'), Sr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Reaction Systems (<!>) →</h4><div class=section-content>'), Cr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Data Loaders (<!>) →</h4><div class=section-content>'), Er = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Operators (<!>) →</h4><div class=section-content>'), kr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Coupling Rules (<!>) →</h4><div class=section-content>'), pr = /* @__PURE__ */ _("<div class=info-item><strong>Time:</strong>Start: <!>, End: "), Pr = /* @__PURE__ */ _("<div class=info-item><strong>Spatial:</strong> "), Ar = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Domain Configuration →</h4><div class=section-content>'), Rr = /* @__PURE__ */ _("<div class=info-item><strong>Tolerances:"), qr = /* @__PURE__ */ _("<div class=info-item><strong>Max Steps:</strong> "), Dr = /* @__PURE__ */ _('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Solver Configuration →</h4><div class=section-content><div class=info-item><strong>Type:</strong> '), Vr = /* @__PURE__ */ _("<div class=empty-state><p>This ESM file appears to be empty or contains no major components."), Nr = /* @__PURE__ */ _("<div class=summary-content><div class=summary-section><h4 class=section-title>Format Information</h4><div class=section-content><div class=info-item><strong>Version:</strong> "), Tr = /* @__PURE__ */ _("<div><div class=summary-header><h3 class=summary-title>File Summary</h3><button class=collapse-toggle>"), it = /* @__PURE__ */ _('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong></strong> →</div><div class=system-summary>'), rt = /* @__PURE__ */ _('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong></strong> →</div><div class=system-summary>Type: '), Mr = /* @__PURE__ */ _('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong>Rule </strong> →</div><div class=system-summary>');
function we(e) {
  return e ? Object.keys(e).length : 0;
}
function Or(e) {
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
function lt(e) {
  const t = [];
  return "variables" in e && e.variables && t.push(`${Object.keys(e.variables).length} variables`), "species" in e && e.species && t.push(`${Object.keys(e.species).length} species`), "parameters" in e && e.parameters && t.push(`${Object.keys(e.parameters).length} parameters`), "equations" in e && e.equations && t.push(`${e.equations.length} equations`), "reactions" in e && e.reactions && t.push(`${e.reactions.length} reactions`), "subsystems" in e && e.subsystems && t.push(`${Object.keys(e.subsystems).length} subsystems`), t.join(", ") || "Empty system";
}
const Ir = (e) => {
  const t = M(() => we(e.esmFile.models)), n = M(() => we(e.esmFile.reaction_systems)), i = M(() => we(e.esmFile.data_loaders)), l = M(() => we(e.esmFile.operators)), s = M(() => {
    var $;
    return (($ = e.esmFile.coupling) == null ? void 0 : $.length) || 0;
  }), r = ($, d) => {
    e.onSectionClick && e.onSectionClick($, d);
  }, c = () => {
    e.onToggleCollapsed && e.onToggleCollapsed(!e.collapsed);
  }, g = () => {
    const $ = ["file-summary"];
    return e.collapsed && $.push("collapsed"), e.class && $.push(e.class), $.join(" ");
  };
  return (() => {
    var $ = Tr(), d = $.firstChild, o = d.firstChild, m = o.nextSibling;
    return d.$$click = c, a(m, () => e.collapsed ? "▶" : "▼"), a($, v(C, {
      get when() {
        return !e.collapsed;
      },
      get children() {
        var h = Nr(), u = h.firstChild, f = u.firstChild, b = f.nextSibling, p = b.firstChild, P = p.firstChild;
        return P.nextSibling, a(p, () => e.esmFile.esm_version || "Not specified", null), a(b, v(C, {
          get when() {
            return e.esmFile.metadata;
          },
          get children() {
            return [(() => {
              var E = _r(), y = E.firstChild;
              return y.nextSibling, a(E, () => e.esmFile.metadata.title || "Untitled", null), E;
            })(), v(C, {
              get when() {
                return e.esmFile.metadata.description;
              },
              get children() {
                var E = br(), y = E.firstChild;
                return y.nextSibling, a(E, () => e.esmFile.metadata.description, null), E;
              }
            }), v(C, {
              get when() {
                return J(() => !!e.esmFile.metadata.authors)() && e.esmFile.metadata.authors.length > 0;
              },
              get children() {
                var E = yr(), y = E.firstChild;
                return y.nextSibling, a(E, () => e.esmFile.metadata.authors.join(", "), null), E;
              }
            }), v(C, {
              get when() {
                return e.esmFile.metadata.created_date;
              },
              get children() {
                var E = xr(), y = E.firstChild;
                return y.nextSibling, a(E, () => e.esmFile.metadata.created_date, null), E;
              }
            })];
          }
        }), null), a(h, v(C, {
          get when() {
            return t() > 0;
          },
          get children() {
            var E = wr(), y = E.firstChild, x = y.firstChild, R = x.nextSibling;
            R.nextSibling;
            var V = y.nextSibling;
            return y.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), r("models"));
            }, y.$$click = () => r("models"), a(y, t, R), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.models || {});
              },
              children: ([k, q]) => (() => {
                var w = it(), S = w.firstChild, D = S.firstChild, I = S.nextSibling;
                return S.$$keydown = (A) => {
                  (A.key === "Enter" || A.key === " ") && (A.preventDefault(), r("models", k));
                }, S.$$click = () => r("models", k), a(D, k), a(I, () => lt(q)), w;
              })()
            })), E;
          }
        }), null), a(h, v(C, {
          get when() {
            return n() > 0;
          },
          get children() {
            var E = Sr(), y = E.firstChild, x = y.firstChild, R = x.nextSibling;
            R.nextSibling;
            var V = y.nextSibling;
            return y.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), r("reaction_systems"));
            }, y.$$click = () => r("reaction_systems"), a(y, n, R), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.reaction_systems || {});
              },
              children: ([k, q]) => (() => {
                var w = it(), S = w.firstChild, D = S.firstChild, I = S.nextSibling;
                return S.$$keydown = (A) => {
                  (A.key === "Enter" || A.key === " ") && (A.preventDefault(), r("reaction_systems", k));
                }, S.$$click = () => r("reaction_systems", k), a(D, k), a(I, () => lt(q)), w;
              })()
            })), E;
          }
        }), null), a(h, v(C, {
          get when() {
            return i() > 0;
          },
          get children() {
            var E = Cr(), y = E.firstChild, x = y.firstChild, R = x.nextSibling;
            R.nextSibling;
            var V = y.nextSibling;
            return y.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), r("data_loaders"));
            }, y.$$click = () => r("data_loaders"), a(y, i, R), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.data_loaders || {});
              },
              children: ([k, q]) => (() => {
                var w = rt(), S = w.firstChild, D = S.firstChild, I = S.nextSibling;
                return I.firstChild, S.$$keydown = (A) => {
                  (A.key === "Enter" || A.key === " ") && (A.preventDefault(), r("data_loaders", k));
                }, S.$$click = () => r("data_loaders", k), a(D, k), a(I, () => q.type || "Unknown", null), a(I, (() => {
                  var A = J(() => !!q.source);
                  return () => A() && ` | Source: ${q.source}`;
                })(), null), a(I, (() => {
                  var A = J(() => !!q.description);
                  return () => A() && ` | ${q.description}`;
                })(), null), w;
              })()
            })), E;
          }
        }), null), a(h, v(C, {
          get when() {
            return l() > 0;
          },
          get children() {
            var E = Er(), y = E.firstChild, x = y.firstChild, R = x.nextSibling;
            R.nextSibling;
            var V = y.nextSibling;
            return y.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), r("operators"));
            }, y.$$click = () => r("operators"), a(y, l, R), a(V, v(L, {
              get each() {
                return Object.entries(e.esmFile.operators || {});
              },
              children: ([k, q]) => (() => {
                var w = rt(), S = w.firstChild, D = S.firstChild, I = S.nextSibling;
                return I.firstChild, S.$$keydown = (A) => {
                  (A.key === "Enter" || A.key === " ") && (A.preventDefault(), r("operators", k));
                }, S.$$click = () => r("operators", k), a(D, k), a(I, () => q.type || "Unknown", null), a(I, (() => {
                  var A = J(() => !!q.description);
                  return () => A() && ` | ${q.description}`;
                })(), null), w;
              })()
            })), E;
          }
        }), null), a(h, v(C, {
          get when() {
            return s() > 0;
          },
          get children() {
            var E = kr(), y = E.firstChild, x = y.firstChild, R = x.nextSibling;
            R.nextSibling;
            var V = y.nextSibling;
            return y.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), r("coupling"));
            }, y.$$click = () => r("coupling"), a(y, s, R), a(V, v(L, {
              get each() {
                return e.esmFile.coupling || [];
              },
              children: (k, q) => (() => {
                var w = Mr(), S = w.firstChild, D = S.firstChild;
                D.firstChild;
                var I = S.nextSibling;
                return S.$$keydown = (A) => {
                  (A.key === "Enter" || A.key === " ") && (A.preventDefault(), r("coupling", q().toString()));
                }, S.$$click = () => r("coupling", q().toString()), a(D, () => q() + 1, null), a(I, () => Or(k)), w;
              })()
            })), E;
          }
        }), null), a(h, v(C, {
          get when() {
            return e.esmFile.domain;
          },
          get children() {
            var E = Ar(), y = E.firstChild, x = y.nextSibling;
            return y.$$keydown = (R) => {
              (R.key === "Enter" || R.key === " ") && (R.preventDefault(), r("domain"));
            }, y.$$click = () => r("domain"), a(x, v(C, {
              get when() {
                return e.esmFile.domain.time;
              },
              get children() {
                var R = pr(), V = R.firstChild, k = V.nextSibling, q = k.nextSibling;
                return q.nextSibling, a(R, () => e.esmFile.domain.time.start ?? "N/A", q), a(R, () => e.esmFile.domain.time.end ?? "N/A", null), a(R, (() => {
                  var w = J(() => !!e.esmFile.domain.time.step);
                  return () => w() && `, Step: ${e.esmFile.domain.time.step}`;
                })(), null), R;
              }
            }), null), a(x, v(C, {
              get when() {
                return e.esmFile.domain.spatial;
              },
              get children() {
                var R = Pr(), V = R.firstChild;
                return V.nextSibling, a(R, () => e.esmFile.domain.spatial.type || "Unknown type", null), R;
              }
            }), null), E;
          }
        }), null), a(h, v(C, {
          get when() {
            return e.esmFile.solver;
          },
          get children() {
            var E = Dr(), y = E.firstChild, x = y.nextSibling, R = x.firstChild, V = R.firstChild;
            return V.nextSibling, y.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), r("solver"));
            }, y.$$click = () => r("solver"), a(R, () => e.esmFile.solver.type || "Not specified", null), a(x, v(C, {
              get when() {
                return e.esmFile.solver.tolerances;
              },
              get children() {
                var k = Rr();
                return k.firstChild, a(k, (() => {
                  var q = J(() => !!e.esmFile.solver.tolerances.absolute);
                  return () => q() && ` Absolute: ${e.esmFile.solver.tolerances.absolute}`;
                })(), null), a(k, (() => {
                  var q = J(() => !!e.esmFile.solver.tolerances.relative);
                  return () => q() && ` Relative: ${e.esmFile.solver.tolerances.relative}`;
                })(), null), k;
              }
            }), null), a(x, v(C, {
              get when() {
                return e.esmFile.solver.max_steps;
              },
              get children() {
                var k = qr(), q = k.firstChild;
                return q.nextSibling, a(k, () => e.esmFile.solver.max_steps, null), k;
              }
            }), null), E;
          }
        }), null), a(h, v(C, {
          get when() {
            return J(() => t() === 0 && n() === 0 && i() === 0)() && s() === 0;
          },
          get children() {
            return Vr();
          }
        }), null), h;
      }
    }), null), T((h) => {
      var u = g(), f = e.collapsed ? "Expand file summary" : "Collapse file summary";
      return u !== h.e && H($, h.e = u), f !== h.t && N(m, "aria-label", h.t = f), h;
    }, {
      e: void 0,
      t: void 0
    }), $;
  })();
};
G(["click", "keydown"]);
var Fr = /* @__PURE__ */ _("<span role=math aria-label=fraction><span class=esm-fraction-numerator></span><span class=esm-fraction-bar></span><span class=esm-fraction-denominator>");
const xl = (e) => {
  const t = () => {
    const n = ["esm-fraction"];
    return e.inline !== !1 && n.push("esm-fraction-inline"), e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = Fr(), i = n.firstChild, l = i.nextSibling, s = l.nextSibling;
    return B(n, "mouseleave", e.onMouseLeave), B(n, "mouseenter", e.onMouseEnter), B(n, "click", e.onClick, !0), a(i, () => e.numerator), a(s, () => e.denominator), T(() => H(n, t())), n;
  })();
};
G(["click"]);
var jr = /* @__PURE__ */ _("<span role=math aria-label=exponentiation><span class=esm-superscript-base></span><span class=esm-superscript-exponent>");
const wl = (e) => {
  const t = () => {
    const n = ["esm-superscript"];
    return e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = jr(), i = n.firstChild, l = i.nextSibling;
    return B(n, "mouseleave", e.onMouseLeave), B(n, "mouseenter", e.onMouseEnter), B(n, "click", e.onClick, !0), a(i, () => e.base), a(l, () => e.exponent), T(() => H(n, t())), n;
  })();
};
G(["click"]);
var Lr = /* @__PURE__ */ _("<span role=math><span class=esm-subscript-base></span><span class=esm-subscript-content>");
const Sl = (e) => {
  const t = () => {
    const n = ["esm-subscript"];
    return e.chemical && n.push("esm-subscript-chemical"), e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = Lr(), i = n.firstChild, l = i.nextSibling;
    return B(n, "mouseleave", e.onMouseLeave), B(n, "mouseenter", e.onMouseEnter), B(n, "click", e.onClick, !0), a(i, () => e.base), a(l, () => e.subscript), T((s) => {
      var r = t(), c = e.chemical ? "chemical subscript" : "subscript";
      return r !== s.e && H(n, s.e = r), c !== s.t && N(n, "aria-label", s.t = c), s;
    }, {
      e: void 0,
      t: void 0
    }), n;
  })();
};
G(["click"]);
var Hr = /* @__PURE__ */ _("<span role=math><span class=esm-radical-symbol>√</span><span class=esm-radical-content>"), Ur = /* @__PURE__ */ _("<span class=esm-radical-index>");
const Cl = (e) => {
  const t = () => {
    const n = ["esm-radical"];
    return e.index && n.push("esm-radical-with-index"), e.class && n.push(e.class), n.join(" ");
  };
  return (() => {
    var n = Hr(), i = n.firstChild, l = i.nextSibling;
    return B(n, "mouseleave", e.onMouseLeave), B(n, "mouseenter", e.onMouseEnter), B(n, "click", e.onClick, !0), a(n, (() => {
      var s = J(() => !!e.index);
      return () => s() && (() => {
        var r = Ur();
        return a(r, () => e.index), r;
      })();
    })(), i), a(l, () => e.content), T((s) => {
      var r = t(), c = e.index ? "nth root" : "square root";
      return r !== s.e && H(n, s.e = r), c !== s.t && N(n, "aria-label", s.t = c), s;
    }, {
      e: void 0,
      t: void 0
    }), n;
  })();
};
G(["click"]);
var Br = /* @__PURE__ */ _("<span role=math><span class=esm-delimiters-left></span><span class=esm-delimiters-content></span><span class=esm-delimiters-right>");
const El = (e) => {
  let t;
  const n = () => e.type || "parentheses", i = () => e.autoSize !== !1, l = () => e.size, s = () => {
    const $ = ["esm-delimiters", `esm-delimiters-${n()}`];
    return i() && $.push("esm-delimiters-auto"), l() && $.push(`esm-delimiters-${l()}`), e.class && $.push(e.class), $.join(" ");
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
  je(() => {
    if (i() && t) {
      const $ = () => {
        const m = t == null ? void 0 : t.querySelector(".esm-delimiters-content");
        if (m) {
          const h = m.offsetHeight, u = t == null ? void 0 : t.querySelector(".esm-delimiters-left"), f = t == null ? void 0 : t.querySelector(".esm-delimiters-right");
          if (u && f) {
            let b = 1;
            h > 20 && (b = Math.min(h / 16, 4));
            const p = `scaleY(${b})`;
            u.style.transform = p, f.style.transform = p;
          }
        }
      };
      setTimeout($, 0);
      const d = new ResizeObserver($), o = t == null ? void 0 : t.querySelector(".esm-delimiters-content");
      return o && d.observe(o), () => d.disconnect();
    }
  });
  const {
    left: c,
    right: g
  } = r();
  return (() => {
    var $ = Br(), d = $.firstChild, o = d.nextSibling, m = o.nextSibling;
    B($, "mouseleave", e.onMouseLeave), B($, "mouseenter", e.onMouseEnter), B($, "click", e.onClick, !0);
    var h = t;
    return typeof h == "function" ? Le(h, $) : t = $, a(d, c), a(o, () => e.content), a(m, g), T((u) => {
      var f = s(), b = `${n()} delimiters`;
      return f !== u.e && H($, u.e = f), b !== u.t && N($, "aria-label", u.t = b), u;
    }, {
      e: void 0,
      t: void 0
    }), $;
  })();
};
G(["click"]);
class Kr {
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
function mt(e) {
  const t = new Kr();
  if (e.couplings)
    for (const n of e.couplings)
      zr(n, t);
  return t.getAllEquivalenceClasses();
}
function zr(e, t) {
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
function $t(e, t, n = "model") {
  const i = [];
  return n === "equation" ? (i.push(e), i) : (i.push(e), !e.includes(".") && t && n !== "file" && i.push(`${t}.${e}`), i);
}
const vt = Ie();
function kl(e) {
  const [t, n] = O(null), i = M(() => mt(e.file)), l = M(() => {
    const r = t();
    if (!r) return /* @__PURE__ */ new Set();
    const c = i(), g = e.scopingMode || "model", $ = $t(r, e.currentModelContext, g), d = /* @__PURE__ */ new Set();
    for (const o of $)
      for (const [m, h] of c.entries())
        if (h.has(o)) {
          for (const u of h)
            ke(u, r, g, e.currentModelContext) && d.add(u);
          break;
        }
    for (const o of $)
      ke(o, r, g, e.currentModelContext) && d.add(o);
    return d;
  }), s = {
    hoveredVar: t,
    setHoveredVar: n,
    highlightedVars: l,
    equivalences: i
  };
  return v(vt.Provider, {
    value: s,
    get children() {
      return e.children;
    }
  });
}
function pl() {
  const e = Fe(vt);
  if (!e)
    throw new Error("useHighlightContext must be used within a HighlightProvider");
  return e;
}
function ke(e, t, n, i) {
  switch (n) {
    case "equation":
      return e === t;
    case "model":
      return !0;
    case "file":
      return !0;
  }
}
function Pl(e, t) {
  return t.has(e);
}
function Al(e, t, n = "model") {
  const [i, l] = O(null), s = M(() => mt(e)), r = M(() => {
    const c = i();
    if (!c) return /* @__PURE__ */ new Set();
    const g = s(), $ = $t(c, t, n), d = /* @__PURE__ */ new Set();
    for (const o of $)
      for (const [, m] of g.entries())
        if (m.has(o)) {
          for (const h of m)
            ke(h, c, n) && d.add(h);
          break;
        }
    for (const o of $)
      ke(o, c, n) && d.add(o);
    return d;
  });
  return {
    hoveredVar: i,
    setHoveredVar: l,
    highlightedVars: r,
    equivalences: s
  };
}
const _t = Ie();
function He(e, t) {
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
function bt(e, t, n) {
  if (t.length === 0)
    return n;
  let i = JSON.parse(JSON.stringify(e)), l = i;
  for (let r = 0; r < t.length - 1; r++) {
    const c = t[r];
    if (c === "args" && typeof l == "object" && "args" in l)
      l = l.args;
    else if (typeof c == "number" && Array.isArray(l))
      l = l[c];
    else
      throw new Error(`Invalid path segment: ${c}`);
  }
  const s = t[t.length - 1];
  if (typeof s == "number" && Array.isArray(l))
    l[s] = n;
  else
    throw new Error(`Invalid final path segment: ${s}`);
  return i;
}
function yt(e, t) {
  if (t.length === 0)
    return {
      type: "root"
    };
  const n = t.slice(0, -2), i = t[t.length - 1];
  if (typeof i != "number")
    return {
      type: "root"
    };
  const l = He(e, n);
  return l && typeof l == "object" && "op" in l ? {
    type: "operator",
    operator: l.op,
    argIndex: i
  } : {
    type: "root"
  };
}
function xt(e) {
  const t = [];
  return typeof e == "number" ? t.push("Edit Value", "Convert to Variable", "Wrap in Operator") : typeof e == "string" ? t.push("Edit Variable", "Convert to Number", "Wrap in Operator") : typeof e == "object" && e !== null && "op" in e && t.push("Change Operator", "Add Argument", "Remove Argument", "Unwrap"), t;
}
function Jr(e) {
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
function Rl(e) {
  const [t, n] = O(null), [i, l] = O(!1), [s, r] = O(""), c = (u) => {
    const f = t();
    return !f || f.length !== u.length ? !1 : f.every((b, p) => b === u[p]);
  }, g = M(() => {
    const u = t();
    if (!u) return null;
    const f = e.rootExpression(), b = He(f, u);
    if (!b) return null;
    const p = typeof b == "number" ? "number" : typeof b == "string" ? "variable" : "operator", P = typeof b == "object" && "op" in b ? b.op : b;
    return {
      type: p,
      value: P,
      parentContext: yt(f, u),
      availableActions: xt(b),
      path: [...u],
      expression: b
    };
  }), $ = (u, f) => {
    const b = e.rootExpression(), p = bt(b, u, f);
    e.onRootReplace(p);
  }, d = () => {
    const u = g();
    u && (u.type === "number" || u.type === "variable") && (r(String(u.value)), l(!0));
  }, o = () => {
    l(!1), r("");
  }, h = {
    selectedPath: t,
    setSelectedPath: n,
    isSelected: c,
    selectedNodeDetails: g,
    onReplace: $,
    startInlineEdit: d,
    cancelInlineEdit: o,
    confirmInlineEdit: (u) => {
      const f = t(), b = g();
      if (!f || !b) return;
      let p;
      if (b.type === "number") {
        const P = parseFloat(u);
        if (isNaN(P)) return;
        p = P;
      } else if (b.type === "variable") {
        if (!u.trim()) return;
        p = u.trim();
      } else
        return;
      $(f, p), o();
    },
    isInlineEditing: i,
    inlineEditValue: s,
    setInlineEditValue: r
  };
  return v(_t.Provider, {
    value: h,
    get children() {
      return e.children;
    }
  });
}
function ql() {
  const e = Fe(_t);
  if (!e)
    throw new Error("useSelectionContext must be used within a SelectionProvider");
  return e;
}
function Dl(e, t) {
  const [n, i] = O(null), [l, s] = O(!1), [r, c] = O(""), g = (o) => {
    const m = n();
    return !m || m.length !== o.length ? !1 : m.every((h, u) => h === o[u]);
  }, $ = M(() => {
    const o = n();
    if (!o) return null;
    const m = e(), h = He(m, o);
    if (!h) return null;
    const u = typeof h == "number" ? "number" : typeof h == "string" ? "variable" : "operator", f = typeof h == "object" && "op" in h ? h.op : h;
    return {
      type: u,
      value: f,
      parentContext: yt(m, o),
      availableActions: xt(h),
      path: [...o],
      expression: h
    };
  }), d = (o, m) => {
    const h = e(), u = bt(h, o, m);
    t(u);
  };
  return {
    selectedPath: n,
    setSelectedPath: i,
    isSelected: g,
    selectedNodeDetails: $,
    onReplace: d,
    startInlineEdit: () => {
      const o = $();
      o && (o.type === "number" || o.type === "variable") && (c(String(o.value)), s(!0));
    },
    cancelInlineEdit: () => {
      s(!1), c("");
    },
    confirmInlineEdit: (o) => {
      const m = n(), h = $();
      if (!m || !h) return;
      let u;
      if (h.type === "number") {
        const f = parseFloat(o);
        if (isNaN(f)) return;
        u = f;
      } else if (h.type === "variable") {
        if (!o.trim()) return;
        u = o.trim();
      } else
        return;
      d(m, u), s(!1), c("");
    },
    isInlineEditing: l,
    inlineEditValue: r,
    setInlineEditValue: c
  };
}
function Vl(e, t = "") {
  const n = Jr(e);
  if (!t) return n;
  const i = t.toLowerCase();
  return n.filter((l) => l.toLowerCase().includes(i));
}
function Nl(e, t) {
  return e.length !== t.length ? !1 : e.every((n, i) => n === t[i]);
}
function Tl(e) {
  return e.join(".");
}
function Ml(e) {
  return e ? e.split(".").map((t) => {
    const n = parseInt(t, 10);
    return isNaN(n) ? t : n;
  }) : [];
}
function le(e) {
  return JSON.parse(JSON.stringify(e));
}
function Wr(e, t, n = {}) {
  const {
    maxEntries: i = 100,
    debounceMs: l = 500,
    registerKeyboardShortcuts: s = !0
  } = n, [r, c] = O([]), [g, $] = O([]);
  let d = !1, o = null, m = null;
  function h(y) {
    d || (o !== null && clearTimeout(o), o = window.setTimeout(() => {
      const x = e();
      if (!x || m && JSON.stringify(x) === JSON.stringify(m))
        return;
      const R = {
        state: le(x),
        timestamp: Date.now(),
        description: y
      };
      c((V) => {
        const k = [...V, R];
        return k.length > i && k.splice(0, k.length - i), k;
      }), $([]), m = le(x), o = null;
    }, l));
  }
  function u() {
    const y = r();
    if (y.length === 0) return;
    const x = e();
    if (!x) return;
    const R = {
      state: le(x),
      timestamp: Date.now(),
      description: "Current state"
    };
    $((k) => [...k, R]);
    const V = y[y.length - 1];
    c((k) => k.slice(0, -1)), d = !0, t(le(V.state)), d = !1;
  }
  function f() {
    const y = g();
    if (y.length === 0) return;
    const x = e();
    if (!x) return;
    const R = {
      state: le(x),
      timestamp: Date.now(),
      description: "Redo checkpoint"
    };
    c((k) => [...k, R]);
    const V = y[y.length - 1];
    $((k) => k.slice(0, -1)), d = !0, t(le(V.state)), d = !1;
  }
  function b() {
    return r().length > 0;
  }
  function p() {
    return g().length > 0;
  }
  function P() {
    o !== null && (clearTimeout(o), o = null), c([]), $([]);
  }
  function E() {
    return r().length + g().length;
  }
  if (je(() => {
    e() && !d && h("File change");
  }), s && typeof window < "u") {
    const y = (x) => {
      (x.ctrlKey || x.metaKey) && (x.key === "z" && !x.shiftKey ? (x.preventDefault(), u()) : (x.key === "y" || x.key === "z" && x.shiftKey) && (x.preventDefault(), f()));
    };
    document.addEventListener("keydown", y), ye(() => {
      document.removeEventListener("keydown", y), o !== null && clearTimeout(o);
    });
  }
  return {
    undo: u,
    redo: f,
    canUndo: b,
    canRedo: p,
    clear: P,
    historyLength: E,
    capture: h
  };
}
function Ol(e, t, n, i) {
  const l = (s) => {
    (s.ctrlKey || s.metaKey) && (s.key === "z" && !s.shiftKey && n() ? (s.preventDefault(), e()) : (s.key === "y" || s.key === "z" && s.shiftKey) && i() && (s.preventDefault(), t()));
  };
  return typeof window < "u" && (document.addEventListener("keydown", l), ye(() => {
    document.removeEventListener("keydown", l);
  })), l;
}
const pe = Symbol("store-raw"), se = Symbol("store-node"), Q = Symbol("store-has"), wt = Symbol("store-self");
function St(e) {
  let t = e[ne];
  if (!t && (Object.defineProperty(e, ne, {
    value: t = new Proxy(e, Xr)
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
  return e != null && typeof e == "object" && (e[ne] || !(t = Object.getPrototypeOf(e)) || t === Object.prototype || Array.isArray(e));
}
function oe(e, t = /* @__PURE__ */ new Set()) {
  let n, i, l, s;
  if (n = e != null && e[pe]) return n;
  if (!ae(e) || t.has(e)) return e;
  if (Array.isArray(e)) {
    Object.isFrozen(e) ? e = e.slice(0) : t.add(e);
    for (let r = 0, c = e.length; r < c; r++)
      l = e[r], (i = oe(l, t)) !== l && (e[r] = i);
  } else {
    Object.isFrozen(e) ? e = Object.assign({}, e) : t.add(e);
    const r = Object.keys(e), c = Object.getOwnPropertyDescriptors(e);
    for (let g = 0, $ = r.length; g < $; g++)
      s = r[g], !c[s].get && (l = e[s], (i = oe(l, t)) !== l && (e[s] = i));
  }
  return e;
}
function Pe(e, t) {
  let n = e[t];
  return n || Object.defineProperty(e, t, {
    value: n = /* @__PURE__ */ Object.create(null)
  }), n;
}
function be(e, t, n) {
  if (e[t]) return e[t];
  const [i, l] = O(n, {
    equals: !1,
    internal: !0
  });
  return i.$ = l, e[t] = i;
}
function Gr(e, t) {
  const n = Reflect.getOwnPropertyDescriptor(e, t);
  return !n || n.get || !n.configurable || t === ne || t === se || (delete n.value, delete n.writable, n.get = () => e[ne][t]), n;
}
function Ct(e) {
  Te() && be(Pe(e, se), wt)();
}
function Yr(e) {
  return Ct(e), Reflect.ownKeys(e);
}
const Xr = {
  get(e, t, n) {
    if (t === pe) return e;
    if (t === ne) return n;
    if (t === Ue)
      return Ct(e), n;
    const i = Pe(e, se), l = i[t];
    let s = l ? l() : e[t];
    if (t === se || t === Q || t === "__proto__") return s;
    if (!l) {
      const r = Object.getOwnPropertyDescriptor(e, t);
      Te() && (typeof s != "function" || e.hasOwnProperty(t)) && !(r && r.get) && (s = be(i, t, s)());
    }
    return ae(s) ? St(s) : s;
  },
  has(e, t) {
    return t === pe || t === ne || t === Ue || t === se || t === Q || t === "__proto__" ? !0 : (Te() && be(Pe(e, Q), t)(), t in e);
  },
  set() {
    return !0;
  },
  deleteProperty() {
    return !0;
  },
  ownKeys: Yr,
  getOwnPropertyDescriptor: Gr
};
function ce(e, t, n, i = !1) {
  if (!i && e[t] === n) return;
  const l = e[t], s = e.length;
  n === void 0 ? (delete e[t], e[Q] && e[Q][t] && l !== void 0 && e[Q][t].$()) : (e[t] = n, e[Q] && e[Q][t] && l === void 0 && e[Q][t].$());
  let r = Pe(e, se), c;
  if ((c = be(r, t, l)) && c.$(() => n), Array.isArray(e) && e.length !== s) {
    for (let g = e.length; g < s; g++) (c = r[g]) && c.$();
    (c = be(r, "length", s)) && c.$(e.length);
  }
  (c = r[wt]) && c.$();
}
function Et(e, t) {
  const n = Object.keys(t);
  for (let i = 0; i < n.length; i += 1) {
    const l = n[i];
    ce(e, l, t[l]);
  }
}
function Qr(e, t) {
  if (typeof t == "function" && (t = t(e)), t = oe(t), Array.isArray(t)) {
    if (e === t) return;
    let n = 0, i = t.length;
    for (; n < i; n++) {
      const l = t[n];
      e[n] !== l && ce(e, n, l);
    }
    ce(e, "length", i);
  } else Et(e, t);
}
function $e(e, t, n = []) {
  let i, l = e;
  if (t.length > 1) {
    i = t.shift();
    const r = typeof i, c = Array.isArray(e);
    if (Array.isArray(i)) {
      for (let g = 0; g < i.length; g++)
        $e(e, [i[g]].concat(t), n);
      return;
    } else if (c && r === "function") {
      for (let g = 0; g < e.length; g++)
        i(e[g], g) && $e(e, [g].concat(t), n);
      return;
    } else if (c && r === "object") {
      const {
        from: g = 0,
        to: $ = e.length - 1,
        by: d = 1
      } = i;
      for (let o = g; o <= $; o += d)
        $e(e, [o].concat(t), n);
      return;
    } else if (t.length > 1) {
      $e(e[i], t, [i].concat(n));
      return;
    }
    l = e[i], n = [i].concat(n);
  }
  let s = t[0];
  typeof s == "function" && (s = s(l, n), s === l) || i === void 0 && s == null || (s = oe(s), i === void 0 || ae(l) && ae(s) && !Array.isArray(s) ? Et(l, s) : ce(e, i, s));
}
function Zr(...[e, t]) {
  const n = oe(e || {}), i = Array.isArray(n), l = St(n);
  function s(...r) {
    Pt(() => {
      i && r.length === 1 ? Qr(n, r[0]) : $e(n, r);
    });
  }
  return [l, s];
}
const Ae = /* @__PURE__ */ new WeakMap(), kt = {
  get(e, t) {
    if (t === pe) return e;
    const n = e[t];
    let i;
    return ae(n) ? Ae.get(n) || (Ae.set(n, i = new Proxy(n, kt)), i) : n;
  },
  set(e, t, n) {
    return ce(e, t, oe(n)), !0;
  },
  deleteProperty(e, t) {
    return ce(e, t, void 0, !0), !0;
  }
};
function el(e) {
  return (t) => {
    if (ae(t)) {
      let n;
      (n = Ae.get(t)) || Ae.set(t, n = new Proxy(t, kt)), e(n);
    }
    return t;
  };
}
function tl() {
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
function nl(e, t) {
  if (t.length === 0) return e;
  let n = e;
  for (const i of t) {
    if (n == null) return;
    n = n[i];
  }
  return n;
}
function Ve(e) {
  const t = [];
  return e.schema_version || t.push("Missing schema_version"), e.metadata ? e.metadata.name || t.push("Missing metadata.name") : t.push("Missing metadata"), e.components || t.push("Missing components"), Array.isArray(e.coupling) || t.push("coupling must be an array"), {
    isValid: t.length === 0,
    errors: t
  };
}
function Il(e = {}) {
  const {
    initialFile: t = tl(),
    historyConfig: n = {},
    enableValidation: i = !0
  } = e, [l, s] = Zr(t), [r, c] = O(
    i ? Ve(t) : { isValid: !0, errors: [] }
  ), g = M(() => l), $ = Wr(
    g,
    (f) => {
      s(f), i && c(Ve(f));
    },
    n
  );
  function d(f) {
    return nl(l, f);
  }
  function o(f, b) {
    f.length === 0 ? s(b) : s(
      el((p) => {
        let P = p;
        for (let E = 0; E < f.length - 1; E++) {
          const y = f[E];
          if (P[y] == null) {
            const x = f[E + 1];
            P[y] = typeof x == "number" ? [] : {};
          }
          P = P[y];
        }
        P[f[f.length - 1]] = b;
      })
    ), i && c(Ve(l));
  }
  function m(f, b) {
    const p = d(f), P = b(p);
    o(f, P);
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
    setPath: o,
    updatePath: m,
    history: $,
    isValid: h,
    validationErrors: u
  };
}
const Fl = {
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
}, jl = {
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
};
function Ne(e, t) {
  return t === "unit" ? "warning" : "error";
}
function il(e, t = {}) {
  const {
    enabled: n = !0,
    debounceMs: i = 300,
    validateOnInit: l = !0
  } = t, [s, r] = O(!1), [c, g] = O(null), [$, d] = O(0);
  let o;
  const m = M(() => {
    if ($(), !n)
      return {
        is_valid: !0,
        schema_errors: [],
        structural_errors: [],
        unit_warnings: []
      };
    const V = e();
    if (!V)
      return {
        is_valid: !1,
        schema_errors: [{
          path: "$",
          message: "No ESM file provided",
          code: "missing_file",
          details: {}
        }],
        structural_errors: [],
        unit_warnings: []
      };
    try {
      r(!0);
      const k = ot(V);
      return r(!1), k;
    } catch (k) {
      r(!1);
      const q = k;
      return {
        is_valid: !1,
        schema_errors: [{
          path: "$",
          message: `Validation error: ${q.message || String(k)}`,
          code: "validation_exception",
          details: {
            exception_type: q.constructor.name,
            error: q.message || String(k)
          }
        }],
        structural_errors: [],
        unit_warnings: []
      };
    }
  }), h = M(() => {
    const V = m(), k = c(), q = [];
    return V && ((V.schema_errors || []).forEach((w) => {
      q.push({
        ...w,
        severity: Ne(w, "schema"),
        type: "schema",
        highlighted: k === w.path
      });
    }), (V.structural_errors || []).forEach((w) => {
      q.push({
        ...w,
        severity: Ne(w, "structural"),
        type: "structural",
        highlighted: k === w.path
      });
    }), (V.unit_warnings || []).forEach((w) => {
      q.push({
        path: w.path || "$",
        message: w.message,
        code: w.code || "unit_warning",
        details: w.details || {},
        severity: Ne(w, "unit"),
        type: "unit",
        highlighted: k === (w.path || "$")
      });
    })), q;
  }), u = M(
    () => h().filter((V) => V.type === "schema")
  ), f = M(
    () => h().filter((V) => V.type === "structural")
  ), b = M(
    () => h().filter((V) => V.type === "unit")
  ), p = M(
    () => h().filter((V) => V.severity === "error").length
  ), P = M(
    () => h().filter((V) => V.severity === "warning").length
  ), E = M(() => {
    const V = m();
    return V ? V.is_valid : !1;
  }), y = () => {
    d((V) => V + 1);
  }, x = (V) => {
    g(V);
  }, R = () => {
    g(null);
  };
  return n && i > 0 && (je(() => {
    e(), o && clearTimeout(o), o = setTimeout(() => {
      y();
    }, i);
  }), ye(() => {
    o && clearTimeout(o);
  })), l && n && setTimeout(() => y(), 0), {
    validationResult: m,
    allErrors: h,
    schemaErrors: u,
    structuralErrors: f,
    unitWarnings: b,
    errorCount: p,
    warningCount: P,
    isValid: E,
    isValidating: s,
    revalidate: y,
    highlightError: x,
    clearHighlight: R
  };
}
function Ll(e, t = {}) {
  const n = il(e, t);
  return {
    isValid: n.isValid,
    errorCount: n.errorCount,
    warningCount: n.warningCount,
    revalidate: n.revalidate
  };
}
function Hl(e, t = 300) {
  let n;
  const i = () => {
    n && clearTimeout(n), n = setTimeout(e, t);
  };
  return ye(() => {
    n && clearTimeout(n);
  }), i;
}
var rl = /* @__PURE__ */ _('<button class=palette-toggle-btn title="Toggle expression palette"aria-label="Toggle expression palette">'), ll = /* @__PURE__ */ _("<div class=expression-palette-container>"), sl = /* @__PURE__ */ _("<div class=expression-validation>"), al = /* @__PURE__ */ _("<div><div class=expression-editor-content><div class=expression-main>");
const ol = (e) => {
  const [t, n] = O(e.initialExpression), [i, l] = O(null), [s, r] = O(null), [c, g] = O(e.showPalette ?? !1), $ = M(() => {
    const f = e.highlightedVars || /* @__PURE__ */ new Set(), b = s();
    return b && !f.has(b) ? /* @__PURE__ */ new Set([...f, b]) : f;
  }), d = (f) => {
    l(f);
  }, o = (f) => {
    r(f);
  }, m = (f, b) => {
    var P;
    if (e.allowEditing === !1) return;
    let p;
    if (f.length === 0)
      p = b;
    else {
      p = structuredClone(t());
      let E = p;
      for (let y = 0; y < f.length - 1; y++)
        E = E[f[y]];
      E[f[f.length - 1]] = b;
    }
    n(p), (P = e.onChange) == null || P.call(e, p);
  }, h = (f) => {
    const b = i();
    m(b || [], f), g(!1);
  }, u = () => {
    const f = ["expression-editor"];
    return e.allowEditing === !1 && f.push("readonly"), e.class && f.push(e.class), f.join(" ");
  };
  return (() => {
    var f = al(), b = f.firstChild, p = b.firstChild;
    return a(p, v(_e, {
      get expr() {
        return t();
      },
      path: [],
      highlightedVars: () => $(),
      onHoverVar: o,
      onSelect: d,
      onReplace: m,
      get selectedPath() {
        return i();
      }
    })), a(b, v(C, {
      get when() {
        return J(() => !!e.showPalette)() && e.allowEditing !== !1;
      },
      get children() {
        var P = rl();
        return P.$$click = () => g((E) => !E), a(P, () => c() ? "←" : "→"), P;
      }
    }), null), a(f, v(C, {
      get when() {
        return J(() => !!(c() && e.showPalette))() && e.allowEditing !== !1;
      },
      get children() {
        var P = ll();
        return a(P, v(gt, {
          get visible() {
            return c();
          },
          onInsertExpression: h,
          class: "expression-editor-palette"
        })), P;
      }
    }), null), a(f, v(C, {
      get when() {
        return e.showValidation;
      },
      get children() {
        return sl();
      }
    }), null), T((P) => {
      var E = u(), y = e.id;
      return E !== P.e && H(f, P.e = E), y !== P.t && N(f, "id", P.t = y), P;
    }, {
      e: void 0,
      t: void 0
    }), f;
  })();
};
G(["click"]);
function cl(e) {
  return {
    nodes: [],
    edges: []
  };
}
const dl = (e) => {
  if (!e.expression) {
    const t = document.createElement("div");
    return t.className = "error-state", t.textContent = "Missing required attribute: expression", t;
  }
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
    return ol(n);
  } catch (t) {
    const n = document.createElement("div");
    return n.className = "error-state", n.textContent = `Component error: ${t instanceof Error ? t.message : "Unknown error"}`, n;
  }
}, ul = (e) => {
  if (!e.model) {
    const t = document.createElement("div");
    return t.className = "error-state", t.textContent = "Missing required attribute: model", t;
  }
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
    return fi(i);
  } catch (t) {
    const n = document.createElement("div");
    return n.className = "error-state", n.textContent = `Component error: ${t instanceof Error ? t.message : "Unknown error"}`, n;
  }
}, hl = (e) => {
  const t = e["esm-file"] || e.esmFile;
  if (!t)
    return () => {
      const n = document.createElement("div");
      return n.className = "error-state", n.textContent = "Missing required attribute: esm-file", n;
    };
  try {
    const n = JSON.parse(t), [i, l] = O(n), s = {
      esmFile: i(),
      showDetails: e["show-summary"] !== "false",
      showExportOptions: !0,
      onComponentTypeClick: (r) => {
        if (typeof window < "u" && e.element) {
          const c = new CustomEvent("componentTypeClick", {
            detail: { componentType: r },
            bubbles: !0
          });
          e.element.dispatchEvent(c);
        }
      },
      onExport: (r) => {
        if (typeof window < "u" && e.element) {
          const c = new CustomEvent("export", {
            detail: { format: r, file: i() },
            bubbles: !0
          });
          e.element.dispatchEvent(c);
        }
      }
    };
    return Ir(s);
  } catch (n) {
    return () => {
      const i = document.createElement("div");
      return i.className = "error-state", i.textContent = `Component error: ${n instanceof Error ? n.message : "Unknown error"}`, i;
    };
  }
}, fl = (e) => {
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
    return zi(l);
  } catch (n) {
    return () => {
      const i = document.createElement("div");
      return i.className = "error-state", i.textContent = `Component error: ${n instanceof Error ? n.message : "Unknown error"}`, i;
    };
  }
}, gl = (e) => {
  const t = e["esm-file"] || e.esmFile;
  if (!t)
    return () => {
      const n = document.createElement("div");
      return n.className = "error-state", n.textContent = "Missing required attribute: esm-file", n;
    };
  try {
    const n = JSON.parse(t), l = {
      graph: cl(n),
      onNodeSelect: (s) => {
        if (typeof window < "u" && e.element) {
          const r = new CustomEvent("componentSelect", {
            detail: { componentId: s.id },
            bubbles: !0
          });
          e.element.dispatchEvent(r);
        }
      },
      onEdgeSelect: (s) => {
        if (typeof window < "u" && e.element) {
          const r = new CustomEvent("couplingEdit", {
            detail: { coupling: s.data, edgeId: s.id },
            bubbles: !0
          });
          e.element.dispatchEvent(r);
        }
      },
      width: e.width ? parseInt(e.width, 10) : void 0,
      height: e.height ? parseInt(e.height, 10) : void 0,
      showMinimap: !0
    };
    return sr(l);
  } catch (n) {
    return () => {
      const i = document.createElement("div");
      return i.className = "error-state", i.textContent = `Component error: ${n instanceof Error ? n.message : "Unknown error"}`, i;
    };
  }
};
function st() {
  if (!(typeof window > "u" || typeof customElements > "u"))
    try {
      ge("esm-expression-editor", {
        expression: "",
        "allow-editing": !0,
        "show-palette": !0,
        "show-validation": !0
      }, (e, { element: t }) => dl({ ...e, element: t })), ge("esm-model-editor", {
        model: "",
        "allow-editing": !0,
        "show-validation": !0,
        "validation-errors": "[]"
      }, (e, { element: t }) => ul({ ...e, element: t })), ge("esm-file-editor", {
        "esm-file": "",
        "allow-editing": !0,
        "enable-undo": !0,
        "show-summary": !0,
        "show-validation": !0
      }, (e, { element: t }) => hl({ ...e, element: t })), ge("esm-reaction-editor", {
        "reaction-system": "",
        "allow-editing": !0,
        "show-validation": !0,
        "validation-errors": "[]"
      }, (e, { element: t }) => fl({ ...e, element: t })), ge("esm-coupling-graph", {
        "esm-file": "",
        width: 800,
        height: 600,
        interactive: !0,
        "allow-editing": !0
      }, (e, { element: t }) => gl({ ...e, element: t })), console.log("ESM Editor web components registered successfully");
    } catch (e) {
      console.warn("Failed to register ESM Editor web components:", e);
    }
}
typeof window < "u" && (document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", st) : setTimeout(st, 0));
export {
  dt as COMMUTATIVE_OPERATORS,
  jl as CommonPaths,
  sr as CouplingGraph,
  El as Delimiters,
  ht as DraggableExpression,
  Dn as EquationEditor,
  _e as ExpressionNode,
  gt as ExpressionPalette,
  Ir as FileSummary,
  xl as Fraction,
  kl as HighlightProvider,
  fi as ModelEditor,
  Fl as PathUtils,
  Cl as Radical,
  zi as ReactionEditor,
  Rl as SelectionProvider,
  Xt as StructuralEditingMenu,
  bl as StructuralEditingProvider,
  Sl as Subscript,
  wl as Superscript,
  yl as ValidationPanel,
  Yt as WRAP_OPERATORS,
  mt as buildVarEquivalences,
  Il as createAstStore,
  Hl as createDebouncedValidation,
  Al as createHighlightContext,
  Dl as createSelectionContext,
  Wr as createUndoHistory,
  Ol as createUndoKeyboardHandler,
  Ll as createValidationContext,
  il as createValidationSignals,
  Vl as getVariableSuggestions,
  Pl as isHighlighted,
  $t as normalizeScopedReference,
  Tl as pathToString,
  Nl as pathsEqual,
  st as registerWebComponents,
  Ml as stringToPath,
  pl as useHighlightContext,
  ql as useSelectionContext,
  Re as useStructuralEditingContext
};
