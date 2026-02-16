import { sharedConfig as v, createRenderEffect as E, createSignal as b, createMemo as x, createComponent as I, createContext as j, useContext as R } from "solid-js";
function G(e, t, n) {
  let i = n.length, o = t.length, a = i, f = 0, r = 0, l = t[o - 1].nextSibling, c = null;
  for (; f < o || r < a; ) {
    if (t[f] === n[r]) {
      f++, r++;
      continue;
    }
    for (; t[o - 1] === n[a - 1]; )
      o--, a--;
    if (o === f) {
      const u = a < i ? r ? n[r - 1].nextSibling : n[a - r] : l;
      for (; r < a; ) e.insertBefore(n[r++], u);
    } else if (a === r)
      for (; f < o; )
        (!c || !c.has(t[f])) && t[f].remove(), f++;
    else if (t[f] === n[a - 1] && n[r] === t[o - 1]) {
      const u = t[--o].nextSibling;
      e.insertBefore(n[r++], t[f++].nextSibling), e.insertBefore(n[--a], u), t[o] = n[a];
    } else {
      if (!c) {
        c = /* @__PURE__ */ new Map();
        let s = r;
        for (; s < a; ) c.set(n[s], s++);
      }
      const u = c.get(t[f]);
      if (u != null)
        if (r < u && u < a) {
          let s = f, g = 1, h;
          for (; ++s < o && s < a && !((h = c.get(t[s])) == null || h !== u + g); )
            g++;
          if (g > u - r) {
            const d = t[f];
            for (; r < u; ) e.insertBefore(n[r++], d);
          } else e.replaceChild(n[r++], t[f++]);
        } else f++;
      else t[f++].remove();
    }
  }
}
const _ = "_$DX_DELEGATE";
function A(e, t, n, i) {
  let o;
  const a = () => {
    const r = document.createElement("template");
    return r.innerHTML = e, r.content.firstChild;
  }, f = () => (o || (o = a())).cloneNode(!0);
  return f.cloneNode = f, f;
}
function J(e, t = window.document) {
  const n = t[_] || (t[_] = /* @__PURE__ */ new Set());
  for (let i = 0, o = e.length; i < o; i++) {
    const a = e[i];
    n.has(a) || (n.add(a), t.addEventListener(a, X));
  }
}
function C(e, t, n) {
  H(e) || (n == null ? e.removeAttribute(t) : e.setAttribute(t, n));
}
function W(e, t) {
  H(e) || (t == null ? e.removeAttribute("class") : e.className = t);
}
function w(e, t, n, i) {
  if (n !== void 0 && !i && (i = []), typeof t != "function") return $(e, t, i, n);
  E((o) => $(e, t(), o, n), i);
}
function H(e) {
  return !!v.context && !v.done && (!e || e.isConnected);
}
function X(e) {
  if (v.registry && v.events && v.events.find(([l, c]) => c === e))
    return;
  let t = e.target;
  const n = `$$${e.type}`, i = e.target, o = e.currentTarget, a = (l) => Object.defineProperty(e, "target", {
    configurable: !0,
    value: l
  }), f = () => {
    const l = t[n];
    if (l && !t.disabled) {
      const c = t[`${n}Data`];
      if (c !== void 0 ? l.call(t, c, e) : l.call(t, e), e.cancelBubble) return;
    }
    return t.host && typeof t.host != "string" && !t.host._$host && t.contains(e.target) && a(t.host), !0;
  }, r = () => {
    for (; f() && (t = t._$host || t.parentNode || t.host); ) ;
  };
  if (Object.defineProperty(e, "currentTarget", {
    configurable: !0,
    get() {
      return t || document;
    }
  }), v.registry && !v.done && (v.done = _$HY.done = !0), e.composedPath) {
    const l = e.composedPath();
    a(l[0]);
    for (let c = 0; c < l.length - 2 && (t = l[c], !!f()); c++) {
      if (t._$host) {
        t = t._$host, r();
        break;
      }
      if (t.parentNode === o)
        break;
    }
  } else r();
  a(i);
}
function $(e, t, n, i, o) {
  const a = H(e);
  if (a) {
    !n && (n = [...e.childNodes]);
    let l = [];
    for (let c = 0; c < n.length; c++) {
      const u = n[c];
      u.nodeType === 8 && u.data.slice(0, 2) === "!$" ? u.remove() : l.push(u);
    }
    n = l;
  }
  for (; typeof n == "function"; ) n = n();
  if (t === n) return n;
  const f = typeof t, r = i !== void 0;
  if (e = r && n[0] && n[0].parentNode || e, f === "string" || f === "number") {
    if (a || f === "number" && (t = t.toString(), t === n))
      return n;
    if (r) {
      let l = n[0];
      l && l.nodeType === 3 ? l.data !== t && (l.data = t) : l = document.createTextNode(t), n = S(e, n, i, l);
    } else
      n !== "" && typeof n == "string" ? n = e.firstChild.data = t : n = e.textContent = t;
  } else if (t == null || f === "boolean") {
    if (a) return n;
    n = S(e, n, i);
  } else {
    if (f === "function")
      return E(() => {
        let l = t();
        for (; typeof l == "function"; ) l = l();
        n = $(e, l, n, i);
      }), () => n;
    if (Array.isArray(t)) {
      const l = [], c = n && Array.isArray(n);
      if (q(l, t, n, o))
        return E(() => n = $(e, l, n, i, !0)), () => n;
      if (a) {
        if (!l.length) return n;
        if (i === void 0) return n = [...e.childNodes];
        let u = l[0];
        if (u.parentNode !== e) return n;
        const s = [u];
        for (; (u = u.nextSibling) !== i; ) s.push(u);
        return n = s;
      }
      if (l.length === 0) {
        if (n = S(e, n, i), r) return n;
      } else c ? n.length === 0 ? T(e, l, i) : G(e, n, l) : (n && S(e), T(e, l));
      n = l;
    } else if (t.nodeType) {
      if (a && t.parentNode) return n = r ? [t] : t;
      if (Array.isArray(n)) {
        if (r) return n = S(e, n, i, t);
        S(e, n, null, t);
      } else n == null || n === "" || !e.firstChild ? e.appendChild(t) : e.replaceChild(t, e.firstChild);
      n = t;
    }
  }
  return n;
}
function q(e, t, n, i) {
  let o = !1;
  for (let a = 0, f = t.length; a < f; a++) {
    let r = t[a], l = n && n[e.length], c;
    if (!(r == null || r === !0 || r === !1)) if ((c = typeof r) == "object" && r.nodeType)
      e.push(r);
    else if (Array.isArray(r))
      o = q(e, r, l) || o;
    else if (c === "function")
      if (i) {
        for (; typeof r == "function"; ) r = r();
        o = q(e, Array.isArray(r) ? r : [r], Array.isArray(l) ? l : [l]) || o;
      } else
        e.push(r), o = !0;
    else {
      const u = String(r);
      l && l.nodeType === 3 && l.data === u ? e.push(l) : e.push(document.createTextNode(u));
    }
  }
  return o;
}
function T(e, t, n = null) {
  for (let i = 0, o = t.length; i < o; i++) e.insertBefore(t[i], n);
}
function S(e, t, n, i) {
  if (n === void 0) return e.textContent = "";
  const o = i || document.createTextNode("");
  if (t.length) {
    let a = !1;
    for (let f = t.length - 1; f >= 0; f--) {
      const r = t[f];
      if (o !== r) {
        const l = r.parentNode === e;
        !a && !f ? l ? e.replaceChild(o, r) : e.insertBefore(o, n) : l && r.remove();
      } else a = !0;
    }
  } else e.insertBefore(o, n);
  return [o];
}
var Y = /* @__PURE__ */ A("<span class=esm-operator-layout><span class=esm-operator-name></span><span class=esm-operator-args>(<!>)"), F = /* @__PURE__ */ A("<span class=esm-num>"), K = /* @__PURE__ */ A("<span class=esm-var>"), Q = /* @__PURE__ */ A("<span class=esm-unknown>?"), Z = /* @__PURE__ */ A("<span tabindex=0 role=button>");
function z(e) {
  return e.replace(/(\d+)/g, (t) => {
    const n = "₀₁₂₃₄₅₆₇₈₉";
    return t.split("").map((i) => n[parseInt(i, 10)]).join("");
  });
}
function ee(e) {
  return (() => {
    var t = Y(), n = t.firstChild, i = n.nextSibling, o = i.firstChild, a = o.nextSibling;
    return a.nextSibling, w(n, () => e.node.op), w(i, () => {
      var f;
      return (f = e.node.args) == null ? void 0 : f.map((r, l) => I(te, {
        expr: r,
        get path() {
          return [...e.path, "args", l];
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
    }, a), E(() => C(t, "data-operator", e.node.op)), t;
  })();
}
const te = (e) => {
  const [t, n] = b(!1), i = x(() => typeof e.expr == "string" && !ne(e.expr)), o = x(() => i() && e.highlightedVars().has(e.expr)), a = x(() => {
    const s = ["esm-expression-node"];
    return t() && s.push("hovered"), o() && s.push("highlighted"), i() && s.push("variable"), typeof e.expr == "number" && s.push("number"), typeof e.expr == "object" && s.push("operator"), s.join(" ");
  }), f = () => {
    n(!0), i() && e.onHoverVar(e.expr);
  }, r = () => {
    n(!1), i() && e.onHoverVar(null);
  }, l = (s) => {
    s.stopPropagation(), e.onSelect(e.path);
  }, c = () => typeof e.expr == "number" ? (() => {
    var s = F();
    return w(s, () => ie(e.expr)), E(() => C(s, "title", `Number: ${e.expr}`)), s;
  })() : typeof e.expr == "string" ? (() => {
    var s = K();
    return w(s, () => z(e.expr)), E(() => C(s, "title", `Variable: ${e.expr}`)), s;
  })() : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? I(ee, {
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
  }) : Q();
  return (() => {
    var s = Z();
    return s.$$click = l, s.addEventListener("mouseleave", r), s.addEventListener("mouseenter", f), w(s, c), E((g) => {
      var h = a(), d = u(), p = e.path.join(".");
      return h !== g.e && W(s, g.e = h), d !== g.t && C(s, "aria-label", g.t = d), p !== g.a && C(s, "data-path", g.a = p), g;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), s;
  })();
  function u() {
    return typeof e.expr == "number" ? `Number: ${e.expr}` : typeof e.expr == "string" ? `Variable: ${e.expr}` : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? `Operator: ${e.expr.op}` : "Expression";
  }
};
function ne(e) {
  return /^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(e);
}
function ie(e) {
  return Math.abs(e) >= 1e6 || Math.abs(e) < 1e-3 && e !== 0 ? e.toExponential(3) : e.toString();
}
J(["click"]);
class oe {
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
    const i = this.find(t), o = this.find(n);
    if (i === o) return;
    const a = this.rank.get(i) || 0, f = this.rank.get(o) || 0;
    a < f ? this.parent.set(i, o) : a > f ? this.parent.set(o, i) : (this.parent.set(o, i), this.rank.set(i, a + 1));
  }
  // Get all variables in the same equivalence class
  getEquivalenceClass(t) {
    const n = this.find(t), i = /* @__PURE__ */ new Set();
    for (const [o, a] of this.parent.entries())
      this.find(o) === n && i.add(o);
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
function M(e) {
  const t = new oe();
  if (e.couplings)
    for (const n of e.couplings)
      re(n, t);
  return t.getAllEquivalenceClasses();
}
function re(e, t) {
  var n;
  switch (e.type) {
    case "variable_map":
      t.union(e.from, e.to);
      break;
    case "operator_compose":
      if (e.translate)
        for (const [i, o] of Object.entries(e.translate)) {
          const a = typeof o == "string" ? o : o.var;
          t.union(i, a);
        }
      break;
    case "couple2":
      if ((n = e.connector) != null && n.equations)
        for (const i of e.connector.equations)
          t.union(i.from, i.to);
      break;
  }
}
function k(e, t, n = "model") {
  const i = [];
  return n === "equation" ? (i.push(e), i) : (i.push(e), !e.includes(".") && t && n !== "file" && i.push(`${t}.${e}`), i);
}
const L = j();
function ae(e) {
  const [t, n] = b(null), i = x(() => M(e.file)), o = x(() => {
    const f = t();
    if (!f) return /* @__PURE__ */ new Set();
    const r = i(), l = e.scopingMode || "model", c = k(f, e.currentModelContext, l), u = /* @__PURE__ */ new Set();
    for (const s of c)
      for (const [g, h] of r.entries())
        if (h.has(s)) {
          for (const d of h)
            N(d, f, l, e.currentModelContext) && u.add(d);
          break;
        }
    for (const s of c)
      N(s, f, l, e.currentModelContext) && u.add(s);
    return u;
  }), a = {
    hoveredVar: t,
    setHoveredVar: n,
    highlightedVars: o,
    equivalences: i
  };
  return I(L.Provider, {
    value: a,
    get children() {
      return e.children;
    }
  });
}
function fe() {
  const e = R(L);
  if (!e)
    throw new Error("useHighlightContext must be used within a HighlightProvider");
  return e;
}
function N(e, t, n, i) {
  switch (n) {
    case "equation":
      return e === t;
    case "model":
      return !0;
    case "file":
      return !0;
  }
}
function ce(e, t) {
  return t.has(e);
}
function ue(e, t, n = "model") {
  const [i, o] = b(null), a = x(() => M(e)), f = x(() => {
    const r = i();
    if (!r) return /* @__PURE__ */ new Set();
    const l = a(), c = k(r, t, n), u = /* @__PURE__ */ new Set();
    for (const s of c)
      for (const [, g] of l.entries())
        if (g.has(s)) {
          for (const h of g)
            N(h, r, n) && u.add(h);
          break;
        }
    for (const s of c)
      N(s, r, n) && u.add(s);
    return u;
  });
  return {
    hoveredVar: i,
    setHoveredVar: o,
    highlightedVars: f,
    equivalences: a
  };
}
const O = j();
function P(e, t) {
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
function B(e, t, n) {
  if (t.length === 0)
    return n;
  let i = JSON.parse(JSON.stringify(e)), o = i;
  for (let f = 0; f < t.length - 1; f++) {
    const r = t[f];
    if (r === "args" && typeof o == "object" && "args" in o)
      o = o.args;
    else if (typeof r == "number" && Array.isArray(o))
      o = o[r];
    else
      throw new Error(`Invalid path segment: ${r}`);
  }
  const a = t[t.length - 1];
  if (typeof a == "number" && Array.isArray(o))
    o[a] = n;
  else
    throw new Error(`Invalid final path segment: ${a}`);
  return i;
}
function D(e, t) {
  if (t.length === 0)
    return {
      type: "root"
    };
  const n = t.slice(0, -2), i = t[t.length - 1];
  if (typeof i != "number")
    return {
      type: "root"
    };
  const o = P(e, n);
  return o && typeof o == "object" && "op" in o ? {
    type: "operator",
    operator: o.op,
    argIndex: i
  } : {
    type: "root"
  };
}
function U(e) {
  const t = [];
  return typeof e == "number" ? t.push("Edit Value", "Convert to Variable", "Wrap in Operator") : typeof e == "string" ? t.push("Edit Variable", "Convert to Number", "Wrap in Operator") : typeof e == "object" && e !== null && "op" in e && t.push("Change Operator", "Add Argument", "Remove Argument", "Unwrap"), t;
}
function se(e) {
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
function de(e) {
  const [t, n] = b(null), [i, o] = b(!1), [a, f] = b(""), r = (d) => {
    const p = t();
    return !p || p.length !== d.length ? !1 : p.every((y, m) => y === d[m]);
  }, l = x(() => {
    const d = t();
    if (!d) return null;
    const p = e.rootExpression(), y = P(p, d);
    if (!y) return null;
    const m = typeof y == "number" ? "number" : typeof y == "string" ? "variable" : "operator", V = typeof y == "object" && "op" in y ? y.op : y;
    return {
      type: m,
      value: V,
      parentContext: D(p, d),
      availableActions: U(y),
      path: [...d],
      expression: y
    };
  }), c = (d, p) => {
    const y = e.rootExpression(), m = B(y, d, p);
    e.onRootReplace(m);
  }, u = () => {
    const d = l();
    d && (d.type === "number" || d.type === "variable") && (f(String(d.value)), o(!0));
  }, s = () => {
    o(!1), f("");
  }, h = {
    selectedPath: t,
    setSelectedPath: n,
    isSelected: r,
    selectedNodeDetails: l,
    onReplace: c,
    startInlineEdit: u,
    cancelInlineEdit: s,
    confirmInlineEdit: (d) => {
      const p = t(), y = l();
      if (!p || !y) return;
      let m;
      if (y.type === "number") {
        const V = parseFloat(d);
        if (isNaN(V)) return;
        m = V;
      } else if (y.type === "variable") {
        if (!d.trim()) return;
        m = d.trim();
      } else
        return;
      c(p, m), s();
    },
    isInlineEditing: i,
    inlineEditValue: a,
    setInlineEditValue: f
  };
  return I(O.Provider, {
    value: h,
    get children() {
      return e.children;
    }
  });
}
function he() {
  const e = R(O);
  if (!e)
    throw new Error("useSelectionContext must be used within a SelectionProvider");
  return e;
}
function ge(e, t) {
  const [n, i] = b(null), [o, a] = b(!1), [f, r] = b(""), l = (s) => {
    const g = n();
    return !g || g.length !== s.length ? !1 : g.every((h, d) => h === s[d]);
  }, c = x(() => {
    const s = n();
    if (!s) return null;
    const g = e(), h = P(g, s);
    if (!h) return null;
    const d = typeof h == "number" ? "number" : typeof h == "string" ? "variable" : "operator", p = typeof h == "object" && "op" in h ? h.op : h;
    return {
      type: d,
      value: p,
      parentContext: D(g, s),
      availableActions: U(h),
      path: [...s],
      expression: h
    };
  }), u = (s, g) => {
    const h = e(), d = B(h, s, g);
    t(d);
  };
  return {
    selectedPath: n,
    setSelectedPath: i,
    isSelected: l,
    selectedNodeDetails: c,
    onReplace: u,
    startInlineEdit: () => {
      const s = c();
      s && (s.type === "number" || s.type === "variable") && (r(String(s.value)), a(!0));
    },
    cancelInlineEdit: () => {
      a(!1), r("");
    },
    confirmInlineEdit: (s) => {
      const g = n(), h = c();
      if (!g || !h) return;
      let d;
      if (h.type === "number") {
        const p = parseFloat(s);
        if (isNaN(p)) return;
        d = p;
      } else if (h.type === "variable") {
        if (!s.trim()) return;
        d = s.trim();
      } else
        return;
      u(g, d), a(!1), r("");
    },
    isInlineEditing: o,
    inlineEditValue: f,
    setInlineEditValue: r
  };
}
function pe(e, t = "") {
  const n = se(e);
  if (!t) return n;
  const i = t.toLowerCase();
  return n.filter((o) => o.toLowerCase().includes(i));
}
function ye(e, t) {
  return e.length !== t.length ? !1 : e.every((n, i) => n === t[i]);
}
function me(e) {
  return e.join(".");
}
function be(e) {
  return e ? e.split(".").map((t) => {
    const n = parseInt(t, 10);
    return isNaN(n) ? t : n;
  }) : [];
}
export {
  te as ExpressionNode,
  ae as HighlightProvider,
  de as SelectionProvider,
  M as buildVarEquivalences,
  ue as createHighlightContext,
  ge as createSelectionContext,
  pe as getVariableSuggestions,
  ce as isHighlighted,
  k as normalizeScopedReference,
  me as pathToString,
  ye as pathsEqual,
  be as stringToPath,
  fe as useHighlightContext,
  he as useSelectionContext
};
