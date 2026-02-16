import { sharedConfig as Q, createRenderEffect as N, createMemo as M, untrack as Ie, createContext as ye, createSignal as j, createComponent as f, useContext as xe, Show as C, For as F, onMount as ze, onCleanup as Qe, mergeProps as ae } from "solid-js";
import { validate as Ke } from "esm-format";
const Ze = /* @__PURE__ */ new Set(["innerHTML", "textContent", "innerText", "children"]), et = /* @__PURE__ */ Object.assign(/* @__PURE__ */ Object.create(null), {
  className: "class",
  htmlFor: "for"
}), tt = /* @__PURE__ */ new Set(["beforeinput", "click", "dblclick", "contextmenu", "focusin", "focusout", "input", "keydown", "keyup", "mousedown", "mousemove", "mouseout", "mouseover", "mouseup", "pointerdown", "pointermove", "pointerout", "pointerover", "pointerup", "touchend", "touchmove", "touchstart"]), nt = {
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace"
}, J = (e) => M(() => e());
function it(e, t, n) {
  let l = n.length, c = t.length, h = l, a = 0, d = 0, _ = t[c - 1].nextSibling, m = null;
  for (; a < c || d < h; ) {
    if (t[a] === n[d]) {
      a++, d++;
      continue;
    }
    for (; t[c - 1] === n[h - 1]; )
      c--, h--;
    if (c === a) {
      const o = h < l ? d ? n[d - 1].nextSibling : n[h - d] : _;
      for (; d < h; ) e.insertBefore(n[d++], o);
    } else if (h === d)
      for (; a < c; )
        (!m || !m.has(t[a])) && t[a].remove(), a++;
    else if (t[a] === n[h - 1] && n[d] === t[c - 1]) {
      const o = t[--c].nextSibling;
      e.insertBefore(n[d++], t[a++].nextSibling), e.insertBefore(n[--h], o), t[c] = n[h];
    } else {
      if (!m) {
        m = /* @__PURE__ */ new Map();
        let r = d;
        for (; r < h; ) m.set(n[r], r++);
      }
      const o = m.get(t[a]);
      if (o != null)
        if (d < o && o < h) {
          let r = a, g = 1, u;
          for (; ++r < c && r < h && !((u = m.get(t[r])) == null || u !== o + g); )
            g++;
          if (g > o - d) {
            const s = t[a];
            for (; d < o; ) e.insertBefore(n[d++], s);
          } else e.replaceChild(n[d++], t[a++]);
        } else a++;
      else t[a++].remove();
    }
  }
}
const Ce = "_$DX_DELEGATE";
function v(e, t, n, l) {
  let c;
  const h = () => {
    const d = l ? document.createElementNS("http://www.w3.org/1998/Math/MathML", "template") : document.createElement("template");
    return d.innerHTML = e, n ? d.content.firstChild.firstChild : l ? d.firstChild : d.content.firstChild;
  }, a = t ? () => Ie(() => document.importNode(c || (c = h()), !0)) : () => (c || (c = h())).cloneNode(!0);
  return a.cloneNode = a, a;
}
function z(e, t = window.document) {
  const n = t[Ce] || (t[Ce] = /* @__PURE__ */ new Set());
  for (let l = 0, c = e.length; l < c; l++) {
    const h = e[l];
    n.has(h) || (n.add(h), t.addEventListener(h, ct));
  }
}
function D(e, t, n) {
  ie(e) || (n == null ? e.removeAttribute(t) : e.setAttribute(t, n));
}
function lt(e, t, n, l) {
  ie(e) || (l == null ? e.removeAttributeNS(t, n) : e.setAttributeNS(t, n, l));
}
function rt(e, t, n) {
  ie(e) || (n ? e.setAttribute(t, "") : e.removeAttribute(t));
}
function W(e, t) {
  ie(e) || (t == null ? e.removeAttribute("class") : e.className = t);
}
function K(e, t, n, l) {
  if (l)
    Array.isArray(n) ? (e[`$$${t}`] = n[0], e[`$$${t}Data`] = n[1]) : e[`$$${t}`] = n;
  else if (Array.isArray(n)) {
    const c = n[0];
    e.addEventListener(t, n[0] = (h) => c.call(e, n[1], h));
  } else e.addEventListener(t, n, typeof n != "function" && n);
}
function at(e, t, n = {}) {
  const l = Object.keys(t || {}), c = Object.keys(n);
  let h, a;
  for (h = 0, a = c.length; h < a; h++) {
    const d = c[h];
    !d || d === "undefined" || t[d] || (Ee(e, d, !1), delete n[d]);
  }
  for (h = 0, a = l.length; h < a; h++) {
    const d = l[h], _ = !!t[d];
    !d || d === "undefined" || n[d] === _ || !_ || (Ee(e, d, !0), n[d] = _);
  }
  return n;
}
function Le(e, t, n) {
  if (!t) return n ? D(e, "style") : t;
  const l = e.style;
  if (typeof t == "string") return l.cssText = t;
  typeof n == "string" && (l.cssText = n = void 0), n || (n = {}), t || (t = {});
  let c, h;
  for (h in n)
    t[h] == null && l.removeProperty(h), delete n[h];
  for (h in t)
    c = t[h], c !== n[h] && (l.setProperty(h, c), n[h] = c);
  return n;
}
function Se(e, t, n) {
  n != null ? e.style.setProperty(t, n) : e.style.removeProperty(t);
}
function se(e, t = {}, n, l) {
  const c = {};
  return N(() => c.children = oe(e, t.children, c.children)), N(() => typeof t.ref == "function" && je(t.ref, e)), N(() => st(e, t, n, !0, c, !0)), c;
}
function je(e, t, n) {
  return Ie(() => e(t, n));
}
function i(e, t, n, l) {
  if (n !== void 0 && !l && (l = []), typeof t != "function") return oe(e, t, l, n);
  N((c) => oe(e, t(), c, n), l);
}
function st(e, t, n, l, c = {}, h = !1) {
  t || (t = {});
  for (const a in c)
    if (!(a in t)) {
      if (a === "children") continue;
      c[a] = ke(e, a, null, c[a], n, h, t);
    }
  for (const a in t) {
    if (a === "children")
      continue;
    const d = t[a];
    c[a] = ke(e, a, d, c[a], n, h, t);
  }
}
function ie(e) {
  return !!Q.context && !Q.done && (!e || e.isConnected);
}
function ot(e) {
  return e.toLowerCase().replace(/-([a-z])/g, (t, n) => n.toUpperCase());
}
function Ee(e, t, n) {
  const l = t.trim().split(/\s+/);
  for (let c = 0, h = l.length; c < h; c++) e.classList.toggle(l[c], n);
}
function ke(e, t, n, l, c, h, a) {
  let d, _, m, o;
  if (t === "style") return Le(e, n, l);
  if (t === "classList") return at(e, n, l);
  if (n === l) return l;
  if (t === "ref")
    h || n(e);
  else if (t.slice(0, 3) === "on:") {
    const r = t.slice(3);
    l && e.removeEventListener(r, l, typeof l != "function" && l), n && e.addEventListener(r, n, typeof n != "function" && n);
  } else if (t.slice(0, 10) === "oncapture:") {
    const r = t.slice(10);
    l && e.removeEventListener(r, l, !0), n && e.addEventListener(r, n, !0);
  } else if (t.slice(0, 2) === "on") {
    const r = t.slice(2).toLowerCase(), g = tt.has(r);
    if (!g && l) {
      const u = Array.isArray(l) ? l[0] : l;
      e.removeEventListener(r, u);
    }
    (g || n) && (K(e, r, n, g), g && z([r]));
  } else if (t.slice(0, 5) === "attr:")
    D(e, t.slice(5), n);
  else if (t.slice(0, 5) === "bool:")
    rt(e, t.slice(5), n);
  else if ((o = t.slice(0, 5) === "prop:") || (m = Ze.has(t)) || (d = e.nodeName.includes("-") || "is" in a)) {
    if (o)
      t = t.slice(5), _ = !0;
    else if (ie(e)) return n;
    t === "class" || t === "className" ? W(e, n) : d && !_ && !m ? e[ot(t)] = n : e[t] = n;
  } else {
    const r = t.indexOf(":") > -1 && nt[t.split(":")[0]];
    r ? lt(e, r, t, n) : D(e, et[t] || t, n);
  }
  return n;
}
function ct(e) {
  if (Q.registry && Q.events && Q.events.find(([_, m]) => m === e))
    return;
  let t = e.target;
  const n = `$$${e.type}`, l = e.target, c = e.currentTarget, h = (_) => Object.defineProperty(e, "target", {
    configurable: !0,
    value: _
  }), a = () => {
    const _ = t[n];
    if (_ && !t.disabled) {
      const m = t[`${n}Data`];
      if (m !== void 0 ? _.call(t, m, e) : _.call(t, e), e.cancelBubble) return;
    }
    return t.host && typeof t.host != "string" && !t.host._$host && t.contains(e.target) && h(t.host), !0;
  }, d = () => {
    for (; a() && (t = t._$host || t.parentNode || t.host); ) ;
  };
  if (Object.defineProperty(e, "currentTarget", {
    configurable: !0,
    get() {
      return t || document;
    }
  }), Q.registry && !Q.done && (Q.done = _$HY.done = !0), e.composedPath) {
    const _ = e.composedPath();
    h(_[0]);
    for (let m = 0; m < _.length - 2 && (t = _[m], !!a()); m++) {
      if (t._$host) {
        t = t._$host, d();
        break;
      }
      if (t.parentNode === c)
        break;
    }
  } else d();
  h(l);
}
function oe(e, t, n, l, c) {
  const h = ie(e);
  if (h) {
    !n && (n = [...e.childNodes]);
    let _ = [];
    for (let m = 0; m < n.length; m++) {
      const o = n[m];
      o.nodeType === 8 && o.data.slice(0, 2) === "!$" ? o.remove() : _.push(o);
    }
    n = _;
  }
  for (; typeof n == "function"; ) n = n();
  if (t === n) return n;
  const a = typeof t, d = l !== void 0;
  if (e = d && n[0] && n[0].parentNode || e, a === "string" || a === "number") {
    if (h || a === "number" && (t = t.toString(), t === n))
      return n;
    if (d) {
      let _ = n[0];
      _ && _.nodeType === 3 ? _.data !== t && (_.data = t) : _ = document.createTextNode(t), n = ee(e, n, l, _);
    } else
      n !== "" && typeof n == "string" ? n = e.firstChild.data = t : n = e.textContent = t;
  } else if (t == null || a === "boolean") {
    if (h) return n;
    n = ee(e, n, l);
  } else {
    if (a === "function")
      return N(() => {
        let _ = t();
        for (; typeof _ == "function"; ) _ = _();
        n = oe(e, _, n, l);
      }), () => n;
    if (Array.isArray(t)) {
      const _ = [], m = n && Array.isArray(n);
      if (_e(_, t, n, c))
        return N(() => n = oe(e, _, n, l, !0)), () => n;
      if (h) {
        if (!_.length) return n;
        if (l === void 0) return n = [...e.childNodes];
        let o = _[0];
        if (o.parentNode !== e) return n;
        const r = [o];
        for (; (o = o.nextSibling) !== l; ) r.push(o);
        return n = r;
      }
      if (_.length === 0) {
        if (n = ee(e, n, l), d) return n;
      } else m ? n.length === 0 ? pe(e, _, l) : it(e, n, _) : (n && ee(e), pe(e, _));
      n = _;
    } else if (t.nodeType) {
      if (h && t.parentNode) return n = d ? [t] : t;
      if (Array.isArray(n)) {
        if (d) return n = ee(e, n, l, t);
        ee(e, n, null, t);
      } else n == null || n === "" || !e.firstChild ? e.appendChild(t) : e.replaceChild(t, e.firstChild);
      n = t;
    }
  }
  return n;
}
function _e(e, t, n, l) {
  let c = !1;
  for (let h = 0, a = t.length; h < a; h++) {
    let d = t[h], _ = n && n[e.length], m;
    if (!(d == null || d === !0 || d === !1)) if ((m = typeof d) == "object" && d.nodeType)
      e.push(d);
    else if (Array.isArray(d))
      c = _e(e, d, _) || c;
    else if (m === "function")
      if (l) {
        for (; typeof d == "function"; ) d = d();
        c = _e(e, Array.isArray(d) ? d : [d], Array.isArray(_) ? _ : [_]) || c;
      } else
        e.push(d), c = !0;
    else {
      const o = String(d);
      _ && _.nodeType === 3 && _.data === o ? e.push(_) : e.push(document.createTextNode(o));
    }
  }
  return c;
}
function pe(e, t, n = null) {
  for (let l = 0, c = t.length; l < c; l++) e.insertBefore(t[l], n);
}
function ee(e, t, n, l) {
  if (n === void 0) return e.textContent = "";
  const c = l || document.createTextNode("");
  if (t.length) {
    let h = !1;
    for (let a = t.length - 1; a >= 0; a--) {
      const d = t[a];
      if (c !== d) {
        const _ = d.parentNode === e;
        !h && !a ? _ ? e.replaceChild(c, d) : e.insertBefore(c, n) : _ && d.remove();
      } else h = !0;
    }
  } else e.insertBefore(c, n);
  return [c];
}
var dt = /* @__PURE__ */ v('<div class=structural-editing-menu style="position:absolute;background-color:white;border:1px solid #ccc;border-radius:4px;padding:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);z-index:1000;min-width:200px"><div class=menu-section><h4 class=menu-header>Wrap in Operator</h4><div class=wrap-operators></div></div><div class=menu-section><button class=close-menu-btn>Close'), ut = /* @__PURE__ */ v("<button class=wrap-operator-btn>"), ht = /* @__PURE__ */ v('<div class=menu-section><button class=unwrap-btn title="Remove the outer operator and keep its argument">Unwrap'), gt = /* @__PURE__ */ v('<div class=menu-section><button class=delete-term-btn title="Remove this term from the operation">Delete Term'), ft = /* @__PURE__ */ v("<div class=draggable-expression>");
const $t = [{
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
}], Oe = /* @__PURE__ */ new Set(["+", "*"]), Fe = ye();
function Ae(e) {
  return typeof e == "object" && e !== null && "op" in e && "args" in e && Array.isArray(e.args) && e.args.length === 1;
}
function ce(e) {
  return typeof e == "object" && e !== null && "op" in e && Oe.has(e.op);
}
function ue(e, t) {
  let n = e;
  for (const l of t) {
    if (n == null) return null;
    if (l === "args" && typeof n == "object" && "args" in n)
      n = n.args;
    else if (typeof l == "number" && Array.isArray(n))
      n = n[l];
    else
      return null;
  }
  return n;
}
function Pe(e, t) {
  if (t.length < 2)
    return {
      parent: null,
      parentPath: [],
      argIndex: null
    };
  const n = t.slice(0, -2), l = t[t.length - 1];
  return {
    parent: ue(e, n),
    parentPath: n,
    argIndex: typeof l == "number" ? l : null
  };
}
function te(e, t, n) {
  if (t.length === 0)
    return n;
  let l = JSON.parse(JSON.stringify(e)), c = l;
  for (let a = 0; a < t.length - 1; a++) {
    const d = t[a];
    if (d === "args" && typeof c == "object" && "args" in c)
      c = c.args;
    else if (typeof d == "number" && Array.isArray(c))
      c = c[d];
    else
      throw new Error(`Invalid path segment: ${d}`);
  }
  const h = t[t.length - 1];
  if (typeof h == "number" && Array.isArray(c))
    c[h] = n;
  else
    throw new Error(`Invalid final path segment: ${h}`);
  return l;
}
function el(e) {
  const [t, n] = j({
    isDragging: !1,
    dragPath: null,
    dragIndex: null,
    dropTarget: null
  }), g = {
    replaceNode: (u, s) => {
      const $ = e.rootExpression(), y = te($, u, s);
      e.onRootReplace(y);
    },
    wrapNode: (u, s) => {
      const $ = e.rootExpression(), y = ue($, u);
      if (!y) return;
      const V = te($, u, {
        op: s,
        args: [y]
      });
      e.onRootReplace(V);
    },
    unwrapNode: (u) => {
      const s = e.rootExpression(), $ = ue(s, u);
      if (!Ae($))
        return !1;
      const y = $.args[0], P = te(s, u, y);
      return e.onRootReplace(P), !0;
    },
    deleteTerm: (u) => {
      const s = e.rootExpression(), {
        parent: $,
        parentPath: y,
        argIndex: P
      } = Pe(s, u);
      if (!$ || !ce($) || P === null)
        return !1;
      const V = $;
      if (V.args.length <= 2) {
        const E = V.args[1 - P], x = te(s, y, E);
        e.onRootReplace(x);
      } else {
        const E = [...V.args];
        E.splice(P, 1);
        const x = {
          ...V,
          args: E
        }, S = te(s, y, x);
        e.onRootReplace(S);
      }
      return !0;
    },
    reorderArgs: (u, s, $) => {
      const y = e.rootExpression(), P = ue(y, u);
      if (!ce(P))
        return !1;
      const V = P, E = [...V.args], [x] = E.splice(s, 1);
      E.splice($, 0, x);
      const S = {
        ...V,
        args: E
      }, A = te(y, u, S);
      return e.onRootReplace(A), !0;
    },
    canUnwrap: (u) => Ae(u),
    canDeleteTerm: (u, s) => {
      const $ = e.rootExpression(), {
        parent: y
      } = Pe($, s);
      return y !== null && ce(y);
    },
    canReorderArgs: (u) => ce(u) && u.args.length > 1,
    getWrapOperators: () => [...$t],
    dragState: t,
    setDragState: n
  };
  return f(Fe.Provider, {
    value: g,
    get children() {
      return e.children;
    }
  });
}
function $e() {
  const e = xe(Fe);
  if (!e)
    throw new Error("useStructuralEditingContext must be used within a StructuralEditingProvider");
  return e;
}
function mt(e) {
  const t = $e();
  if (!e.isVisible || !e.selectedPath || !e.selectedExpr)
    return null;
  const n = (d) => {
    e.selectedPath && (t.wrapNode(e.selectedPath, d), e.onClose());
  }, l = () => {
    e.selectedPath && t.unwrapNode(e.selectedPath) && e.onClose();
  }, c = () => {
    e.selectedPath && t.deleteTerm(e.selectedPath) && e.onClose();
  }, h = t.canUnwrap(e.selectedExpr), a = e.selectedPath && t.canDeleteTerm(e.selectedExpr, e.selectedPath);
  return (() => {
    var d = dt(), _ = d.firstChild, m = _.firstChild, o = m.nextSibling, r = _.nextSibling, g = r.firstChild;
    return i(o, () => t.getWrapOperators().map((u) => (() => {
      var s = ut();
      return s.$$click = () => n(u.op), i(s, () => u.label), N(() => D(s, "title", u.label)), s;
    })())), i(d, h && (() => {
      var u = ht(), s = u.firstChild;
      return s.$$click = l, u;
    })(), r), i(d, a && (() => {
      var u = gt(), s = u.firstChild;
      return s.$$click = c, u;
    })(), r), K(g, "click", e.onClose, !0), N((u) => {
      var y, P;
      var s = `${((y = e.position) == null ? void 0 : y.x) || 0}px`, $ = `${((P = e.position) == null ? void 0 : P.y) || 0}px`;
      return s !== u.e && Se(d, "left", u.e = s), $ !== u.t && Se(d, "top", u.t = $), u;
    }, {
      e: void 0,
      t: void 0
    }), d;
  })();
}
function He(e) {
  const t = $e();
  if (!e.canDrag)
    return e.children;
  const n = (a) => {
    a.dataTransfer && (a.dataTransfer.effectAllowed = "move", a.dataTransfer.setData("text/plain", JSON.stringify({
      path: e.path,
      index: e.index,
      parentPath: e.parentPath
    }))), t.setDragState({
      isDragging: !0,
      dragPath: e.path,
      dragIndex: e.index,
      dropTarget: null
    });
  }, l = () => {
    t.setDragState({
      isDragging: !1,
      dragPath: null,
      dragIndex: null,
      dropTarget: null
    });
  }, c = (a) => {
    a.preventDefault(), a.dataTransfer && (a.dataTransfer.dropEffect = "move");
    const d = t.dragState();
    d.isDragging && d.dragIndex !== e.index && t.setDragState({
      ...d,
      dropTarget: {
        path: e.parentPath,
        index: e.index
      }
    });
  }, h = (a) => {
    var _;
    a.preventDefault();
    const d = (_ = a.dataTransfer) == null ? void 0 : _.getData("text/plain");
    if (d)
      try {
        const m = JSON.parse(d);
        m.index !== e.index && m.parentPath.join(".") === e.parentPath.join(".") && t.reorderArgs(e.parentPath, m.index, e.index);
      } catch (m) {
        console.error("Failed to parse drag data:", m);
      }
  };
  return (() => {
    var a = ft();
    return a.addEventListener("drop", h), a.addEventListener("dragover", c), a.addEventListener("dragend", l), a.addEventListener("dragstart", n), D(a, "draggable", !0), i(a, () => e.children), N(() => D(a, "data-drag-index", e.index)), a;
  })();
}
z(["click"]);
var vt = /* @__PURE__ */ v("<span class=esm-operator-layout><span class=esm-operator-name></span><span class=esm-operator-args>(<!>)"), _t = /* @__PURE__ */ v("<span class=esm-num>"), bt = /* @__PURE__ */ v("<span class=esm-var>"), yt = /* @__PURE__ */ v("<span class=esm-unknown>?"), xt = /* @__PURE__ */ v("<span tabindex=0 role=button>");
function wt(e) {
  return e.replace(/(\d+)/g, (t) => {
    const n = "₀₁₂₃₄₅₆₇₈₉";
    return t.split("").map((l) => n[parseInt(l, 10)]).join("");
  });
}
function Ct(e) {
  let t;
  try {
    t = $e();
  } catch {
  }
  const n = Oe.has(e.node.op);
  return (() => {
    var l = vt(), c = l.firstChild, h = c.nextSibling, a = h.firstChild, d = a.nextSibling;
    return d.nextSibling, i(c, () => e.node.op), i(h, () => {
      var _;
      return (_ = e.node.args) == null ? void 0 : _.map((m, o) => {
        var u;
        const r = [...e.path, "args", o], g = f(ge, {
          expr: m,
          path: r,
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
        return t && n && (((u = e.node.args) == null ? void 0 : u.length) || 0) > 1 ? f(He, {
          path: r,
          index: o,
          get parentPath() {
            return e.path;
          },
          canDrag: !0,
          children: g
        }) : g;
      });
    }, d), N(() => D(l, "data-operator", e.node.op)), l;
  })();
}
const ge = (e) => {
  const [t, n] = j(!1), [l, c] = j(!1), [h, a] = j({
    x: 0,
    y: 0
  });
  let d;
  try {
    d = $e();
  } catch {
  }
  const _ = M(() => typeof e.expr == "string" && !St(e.expr)), m = M(() => _() && e.highlightedVars().has(e.expr)), o = M(() => e.selectedPath && e.selectedPath.length === e.path.length && e.selectedPath.every((S, A) => S === e.path[A])), r = M(() => d && e.parentPath && typeof e.indexInParent == "number" && e.parentPath.length > 0), g = M(() => {
    const S = ["esm-expression-node"];
    return t() && S.push("hovered"), m() && S.push("highlighted"), o() && S.push("selected"), _() && S.push("variable"), typeof e.expr == "number" && S.push("number"), typeof e.expr == "object" && S.push("operator"), S.join(" ");
  }), u = () => {
    n(!0), _() && e.onHoverVar(e.expr);
  }, s = () => {
    n(!1), _() && e.onHoverVar(null);
  }, $ = (S) => {
    S.stopPropagation(), e.onSelect(e.path);
  }, y = (S) => {
    S.preventDefault(), S.stopPropagation(), d && (e.onSelect(e.path), a({
      x: S.clientX,
      y: S.clientY
    }), c(!0));
  }, P = () => {
    c(!1);
  }, V = () => typeof e.expr == "number" ? (() => {
    var S = _t();
    return i(S, () => Et(e.expr)), N(() => D(S, "title", `Number: ${e.expr}`)), S;
  })() : typeof e.expr == "string" ? (() => {
    var S = bt();
    return i(S, () => wt(e.expr)), N(() => D(S, "title", `Variable: ${e.expr}`)), S;
  })() : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? f(Ct, {
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
  }) : yt(), E = [(() => {
    var S = xt();
    return S.$$contextmenu = y, S.$$click = $, S.addEventListener("mouseleave", s), S.addEventListener("mouseenter", u), i(S, V), N((A) => {
      var I = g(), k = x(), R = e.path.join(".");
      return I !== A.e && W(S, A.e = I), k !== A.t && D(S, "aria-label", A.t = k), R !== A.a && D(S, "data-path", A.a = R), A;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), S;
  })(), f(C, {
    get when() {
      return l() && d;
    },
    get children() {
      return f(mt, {
        get selectedPath() {
          return e.path;
        },
        get selectedExpr() {
          return e.expr;
        },
        get isVisible() {
          return l();
        },
        get position() {
          return h();
        },
        onClose: P
      });
    }
  })];
  if (r() && d && e.parentPath && typeof e.indexInParent == "number")
    return f(He, {
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
  function x() {
    return typeof e.expr == "number" ? `Number: ${e.expr}` : typeof e.expr == "string" ? `Variable: ${e.expr}` : typeof e.expr == "object" && e.expr !== null && "op" in e.expr ? `Operator: ${e.expr.op}` : "Expression";
  }
};
function St(e) {
  return /^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(e);
}
function Et(e) {
  return Math.abs(e) >= 1e6 || Math.abs(e) < 1e-3 && e !== 0 ? e.toExponential(3) : e.toString();
}
z(["click", "contextmenu"]);
var kt = /* @__PURE__ */ v("<div role=button tabindex=0><div class=template-label></div><div class=template-description>"), pt = /* @__PURE__ */ v("<div class=context-suggestions><h4 class=section-title><span class=section-icon>🧪</span>Model Context</h4><div class=suggestions-grid>"), At = /* @__PURE__ */ v("<div role=button tabindex=0><div class=item-type></div><div class=item-label>"), Pt = /* @__PURE__ */ v(`<div class=palette-search><input type=text class=search-input placeholder="Search expressions... (type '/' to open)">`), Rt = /* @__PURE__ */ v('<div class=no-results><div class=no-results-icon>🔍</div><div class=no-results-text>No expressions found for "<!>"</div><div class=no-results-hint>Try searching for operators, functions, or keywords'), qt = /* @__PURE__ */ v("<div class=quick-insert-help>Press <kbd>Escape</kbd> to close, click or drag to insert"), Vt = /* @__PURE__ */ v("<div><div class=palette-content>"), Dt = /* @__PURE__ */ v("<div class=palette-section><h4 class=section-title><span class=section-icon></span></h4><div class=templates-grid>");
const Re = [
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
], Nt = {
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
}, Tt = (e) => {
  const [t, n] = j(!1), l = (a) => {
    a.dataTransfer && (a.dataTransfer.effectAllowed = "copy", a.dataTransfer.setData("application/json", JSON.stringify({
      type: "expression-template",
      expression: e.template.expression,
      templateId: e.template.id
    }))), n(!0);
  }, c = () => {
    n(!1);
  }, h = () => {
    e.onInsert(e.template.expression);
  };
  return (() => {
    var a = kt(), d = a.firstChild, _ = d.nextSibling;
    return a.$$click = h, a.addEventListener("dragend", c), a.addEventListener("dragstart", l), D(a, "draggable", !0), i(d, () => e.template.label), i(_, () => e.template.description), N((m) => {
      var o = `expression-template ${t() ? "dragging" : ""}`, r = e.template.description, g = `Insert ${e.template.label}: ${e.template.description}`;
      return o !== m.e && W(a, m.e = o), r !== m.t && D(a, "title", m.t = r), g !== m.a && D(a, "aria-label", m.a = g), m;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), a;
  })();
}, Mt = (e) => {
  const t = M(() => {
    if (!e.model) return [];
    const n = [];
    return e.model.variables && e.model.variables.forEach((l) => {
      n.push({
        label: l.name,
        expression: l.name,
        type: "variable"
      });
    }), e.model.reaction_systems && e.model.reaction_systems.forEach((l) => {
      l.species && l.species.forEach((c) => {
        n.push({
          label: c.name,
          expression: c.name,
          type: "species"
        });
      });
    }), n;
  });
  return f(C, {
    get when() {
      return t().length > 0;
    },
    get children() {
      var n = pt(), l = n.firstChild, c = l.nextSibling;
      return i(c, f(F, {
        get each() {
          return t();
        },
        children: (h) => (() => {
          var a = At(), d = a.firstChild, _ = d.nextSibling;
          return a.$$click = () => e.onInsert(h.expression), i(d, () => h.type.charAt(0).toUpperCase()), i(_, () => h.label), N((m) => {
            var o = `context-item ${h.type}`, r = `${h.type}: ${h.label}`, g = `Insert ${h.type} ${h.label}`;
            return o !== m.e && W(a, m.e = o), r !== m.t && D(a, "title", m.t = r), g !== m.a && D(a, "aria-label", m.a = g), m;
          }, {
            e: void 0,
            t: void 0,
            a: void 0
          }), a;
        })()
      })), n;
    }
  });
}, It = (e) => {
  const [t, n] = j(""), l = M(() => e.searchQuery || t()), c = M(() => {
    const o = l().toLowerCase().trim();
    return o ? Re.filter((r) => r.label.toLowerCase().includes(o) || r.description.toLowerCase().includes(o) || r.keywords.some((g) => g.toLowerCase().includes(o))) : Re;
  }), h = M(() => {
    const o = {};
    return c().forEach((r) => {
      o[r.category] || (o[r.category] = []), o[r.category].push(r);
    }), o;
  }), a = (o) => {
    var r, g;
    (r = e.onInsertExpression) == null || r.call(e, o), e.quickInsertMode && ((g = e.onCloseQuickInsert) == null || g.call(e));
  }, d = (o) => {
    e.onSearchQueryChange ? e.onSearchQueryChange(o) : n(o);
  }, _ = (o) => {
    var r;
    e.quickInsertMode && o.key === "Escape" && ((r = e.onCloseQuickInsert) == null || r.call(e));
  }, m = () => {
    const o = ["expression-palette"];
    return e.quickInsertMode && o.push("quick-insert-mode"), e.visible === !1 && o.push("hidden"), e.class && o.push(e.class), o.join(" ");
  };
  return (() => {
    var o = Vt(), r = o.firstChild;
    return o.$$keydown = _, i(o, f(C, {
      get when() {
        return e.quickInsertMode || l();
      },
      get children() {
        var g = Pt(), u = g.firstChild;
        return u.$$input = (s) => d(s.currentTarget.value), N(() => u.autofocus = e.quickInsertMode), N(() => u.value = l()), g;
      }
    }), r), i(r, f(C, {
      get when() {
        return !l();
      },
      get children() {
        return f(Mt, {
          get model() {
            return e.currentModel;
          },
          onInsert: a
        });
      }
    }), null), i(r, f(F, {
      get each() {
        return Object.entries(Nt);
      },
      children: ([g, u]) => {
        const s = h()[g] || [];
        return f(C, {
          get when() {
            return s.length > 0;
          },
          get children() {
            var $ = Dt(), y = $.firstChild, P = y.firstChild, V = y.nextSibling;
            return i(P, () => u.icon), i(y, () => u.title, null), i(V, f(F, {
              each: s,
              children: (E) => f(Tt, {
                template: E,
                onInsert: a
              })
            })), $;
          }
        });
      }
    }), null), i(r, f(C, {
      get when() {
        return J(() => !!l())() && c().length === 0;
      },
      get children() {
        var g = Rt(), u = g.firstChild, s = u.nextSibling, $ = s.firstChild, y = $.nextSibling;
        return y.nextSibling, i(s, l, y), g;
      }
    }), null), i(o, f(C, {
      get when() {
        return e.quickInsertMode;
      },
      get children() {
        return qt();
      }
    }), null), N(() => W(o, m())), o;
  })();
};
z(["click", "keydown", "input"]);
var Lt = /* @__PURE__ */ v('<div class=equation-description title="Equation description">'), jt = /* @__PURE__ */ v("<div><div class=equation-content><div class=equation-lhs></div><div class=equation-equals aria-label=equals>=</div><div class=equation-rhs>");
const Ot = (e) => {
  const [t, n] = j(null), [l, c] = j(null), h = M(() => {
    const o = e.highlightedVars || /* @__PURE__ */ new Set(), r = l();
    return r && !o.has(r) ? /* @__PURE__ */ new Set([...o, r]) : o;
  }), a = (o) => {
    n(o);
  }, d = (o) => {
    c(o);
  }, _ = (o, r) => {
    if (e.readonly || !e.onEquationChange) return;
    const g = structuredClone(e.equation);
    let u = g;
    for (let s = 0; s < o.length - 1; s++)
      u = u[o[s]];
    o.length > 0 && (u[o[o.length - 1]] = r), e.onEquationChange(g);
  }, m = () => {
    const o = ["equation-editor"];
    return e.readonly && o.push("readonly"), e.class && o.push(e.class), o.join(" ");
  };
  return (() => {
    var o = jt(), r = o.firstChild, g = r.firstChild, u = g.nextSibling, s = u.nextSibling;
    return i(g, f(ge, {
      get expr() {
        return e.equation.lhs;
      },
      path: ["lhs"],
      highlightedVars: () => h(),
      onHoverVar: d,
      onSelect: a,
      onReplace: _,
      get selectedPath() {
        return t();
      }
    })), i(s, f(ge, {
      get expr() {
        return e.equation.rhs;
      },
      path: ["rhs"],
      highlightedVars: () => h(),
      onHoverVar: d,
      onSelect: a,
      onReplace: _,
      get selectedPath() {
        return t();
      }
    })), i(o, f(C, {
      get when() {
        return e.equation.description;
      },
      get children() {
        var $ = Lt();
        return i($, () => e.equation.description), $;
      }
    }), null), N(($) => {
      var y = m(), P = e.id;
      return y !== $.e && W(o, $.e = y), P !== $.t && D(o, "id", $.t = P), $;
    }, {
      e: void 0,
      t: void 0
    }), o;
  })();
};
var Ft = /* @__PURE__ */ v("<div class=variable-unit title=Unit>[<!>]"), Ht = /* @__PURE__ */ v('<div class=variable-default title="Default value">= '), Ut = /* @__PURE__ */ v("<div class=variable-description title=Description>"), Bt = /* @__PURE__ */ v('<button class=variable-remove-btn title="Remove variable">×'), Wt = /* @__PURE__ */ v("<div role=button tabindex=0><div class=variable-info><div class=variable-header><span class=variable-name></span><span>"), Yt = /* @__PURE__ */ v('<button class=add-btn title="Add new variable"aria-label="Add new variable">+'), Gt = /* @__PURE__ */ v("<button class=add-first-btn>Add first variable"), Jt = /* @__PURE__ */ v("<div class=empty-state><div class=empty-icon>📊</div><div class=empty-text>No variables defined"), Xt = /* @__PURE__ */ v("<div class=variables-content>"), zt = /* @__PURE__ */ v("<div class=variables-panel><div class=panel-header><span>▶</span><h3>Variables (<!>)"), Qt = /* @__PURE__ */ v("<div class=variable-group><h4 class=group-title><span></span>s (<!>)</h4><div class=variables-list>"), Kt = /* @__PURE__ */ v('<button class=add-btn title="Add new equation"aria-label="Add new equation">+'), Zt = /* @__PURE__ */ v("<button class=add-first-btn>Add first equation"), en = /* @__PURE__ */ v("<div class=empty-state><div class=empty-icon>⚖️</div><div class=empty-text>No equations defined"), tn = /* @__PURE__ */ v("<div class=equations-content>"), nn = /* @__PURE__ */ v("<div class=equations-panel><div class=panel-header><span>▶</span><h3>Equations (<!>)"), ln = /* @__PURE__ */ v('<button class=equation-remove-btn title="Remove equation">×'), rn = /* @__PURE__ */ v("<div class=equation-item>"), an = /* @__PURE__ */ v('<div class=event-add-buttons><button class=add-btn title="Add continuous event">+ Continuous</button><button class=add-btn title="Add discrete event">+ Discrete'), sn = /* @__PURE__ */ v("<div class=event-group><h4>Continuous Events"), on = /* @__PURE__ */ v("<div class=event-group><h4>Discrete Events"), cn = /* @__PURE__ */ v("<div class=empty-actions><button class=add-first-btn>Add continuous event</button><button class=add-first-btn>Add discrete event"), dn = /* @__PURE__ */ v("<div class=empty-state><div class=empty-icon>⚡</div><div class=empty-text>No events defined"), un = /* @__PURE__ */ v("<div class=events-content>"), hn = /* @__PURE__ */ v("<div class=events-panel><div class=panel-header><span>▶</span><h3>Events (<!>)"), qe = /* @__PURE__ */ v("<div class=event-description>"), gn = /* @__PURE__ */ v('<div class="event-item continuous"><div class=event-name>'), fn = /* @__PURE__ */ v('<div class="event-item discrete"><div class=event-name>'), $n = /* @__PURE__ */ v("<div class=model-description>"), mn = /* @__PURE__ */ v("<div class=palette-sidebar>"), vn = /* @__PURE__ */ v("<div><div class=model-editor-layout><div class=model-content><div class=model-header><h2 class=model-name></h2></div><div class=model-panels>");
const he = {
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
}, _n = (e) => {
  const [t, n] = j(!1), l = () => he[e.type], c = () => {
    var a;
    e.readonly || (a = e.onEdit) == null || a.call(e, e.variable);
  }, h = (a) => {
    var d;
    a.stopPropagation(), e.readonly || (d = e.onRemove) == null || d.call(e, e.variable.name);
  };
  return (() => {
    var a = Wt(), d = a.firstChild, _ = d.firstChild, m = _.firstChild, o = m.nextSibling;
    return a.$$click = c, a.addEventListener("mouseleave", () => n(!1)), a.addEventListener("mouseenter", () => n(!0)), i(m, () => e.variable.name), i(o, () => l().label), i(d, f(C, {
      get when() {
        return e.variable.unit;
      },
      get children() {
        var r = Ft(), g = r.firstChild, u = g.nextSibling;
        return u.nextSibling, i(r, () => e.variable.unit, u), r;
      }
    }), null), i(d, f(C, {
      get when() {
        return e.variable.default_value !== void 0;
      },
      get children() {
        var r = Ht();
        return r.firstChild, i(r, () => e.variable.default_value, null), r;
      }
    }), null), i(d, f(C, {
      get when() {
        return e.variable.description;
      },
      get children() {
        var r = Ut();
        return i(r, () => e.variable.description), r;
      }
    }), null), i(a, f(C, {
      get when() {
        return J(() => !e.readonly)() && t();
      },
      get children() {
        var r = Bt();
        return r.$$click = h, N(() => D(r, "aria-label", `Remove variable ${e.variable.name}`)), r;
      }
    }), null), N((r) => {
      var g = `variable-item ${t() ? "hovered" : ""}`, u = `variable-type-badge ${l().color}`, s = l().description;
      return g !== r.e && W(a, r.e = g), u !== r.t && W(o, r.t = u), s !== r.a && D(o, "title", r.a = s), r;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), a;
  })();
}, bn = (e) => {
  const [t, n] = j(!0), l = M(() => {
    const c = e.variables || [], h = {
      state: [],
      parameter: [],
      observed: [],
      other: []
    };
    return c.forEach((a) => {
      let d = "other";
      a.name.startsWith("k_") || a.name.includes("rate") || a.name.includes("param") ? d = "parameter" : a.name.includes("obs") || a.name.includes("measured") ? d = "observed" : !a.name.includes("_const") && !a.name.includes("_param") && (d = "state"), h[d].push(a);
    }), h;
  });
  return (() => {
    var c = zt(), h = c.firstChild, a = h.firstChild, d = a.nextSibling, _ = d.firstChild, m = _.nextSibling;
    return m.nextSibling, h.$$click = () => n(!t()), i(d, () => (e.variables || []).length, m), i(h, f(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var o = Yt();
        return o.$$click = (r) => {
          var g;
          r.stopPropagation(), (g = e.onAddVariable) == null || g.call(e);
        }, o;
      }
    }), null), i(c, f(C, {
      get when() {
        return t();
      },
      get children() {
        var o = Xt();
        return i(o, f(F, {
          get each() {
            return Object.entries(l());
          },
          children: ([r, g]) => f(C, {
            get when() {
              return g.length > 0;
            },
            get children() {
              var u = Qt(), s = u.firstChild, $ = s.firstChild, y = $.nextSibling, P = y.nextSibling;
              P.nextSibling;
              var V = s.nextSibling;
              return i($, () => he[r].label), i(s, () => he[r].description, y), i(s, () => g.length, P), i(V, f(F, {
                each: g,
                children: (E) => f(_n, {
                  variable: E,
                  type: r,
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
              })), N(() => W($, `group-badge ${he[r].color}`)), u;
            }
          })
        }), null), i(o, f(C, {
          get when() {
            return (e.variables || []).length === 0;
          },
          get children() {
            var r = Jt(), g = r.firstChild;
            return g.nextSibling, i(r, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var u = Gt();
                return K(u, "click", e.onAddVariable, !0), u;
              }
            }), null), r;
          }
        }), null), o;
      }
    }), null), N(() => W(a, `expand-icon ${t() ? "expanded" : ""}`)), c;
  })();
}, yn = (e) => {
  const [t, n] = j(!0);
  return (() => {
    var l = nn(), c = l.firstChild, h = c.firstChild, a = h.nextSibling, d = a.firstChild, _ = d.nextSibling;
    return _.nextSibling, c.$$click = () => n(!t()), i(a, () => (e.equations || []).length, _), i(c, f(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var m = Kt();
        return m.$$click = (o) => {
          var r;
          o.stopPropagation(), (r = e.onAddEquation) == null || r.call(e);
        }, m;
      }
    }), null), i(l, f(C, {
      get when() {
        return t();
      },
      get children() {
        var m = tn();
        return i(m, f(F, {
          get each() {
            return e.equations || [];
          },
          children: (o, r) => (() => {
            var g = rn();
            return i(g, f(Ot, {
              equation: o,
              get highlightedVars() {
                return e.highlightedVars;
              },
              onEquationChange: (u) => {
                var s;
                return (s = e.onEditEquation) == null ? void 0 : s.call(e, r(), u);
              },
              get readonly() {
                return e.readonly;
              },
              class: "model-equation"
            }), null), i(g, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var u = ln();
                return u.$$click = () => {
                  var s;
                  return (s = e.onRemoveEquation) == null ? void 0 : s.call(e, r());
                }, N(() => D(u, "aria-label", `Remove equation ${r() + 1}`)), u;
              }
            }), null), g;
          })()
        }), null), i(m, f(C, {
          get when() {
            return (e.equations || []).length === 0;
          },
          get children() {
            var o = en(), r = o.firstChild;
            return r.nextSibling, i(o, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var g = Zt();
                return K(g, "click", e.onAddEquation, !0), g;
              }
            }), null), o;
          }
        }), null), m;
      }
    }), null), N(() => W(h, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, xn = (e) => {
  const [t, n] = j(!0), l = () => (e.continuousEvents || []).length + (e.discreteEvents || []).length;
  return (() => {
    var c = hn(), h = c.firstChild, a = h.firstChild, d = a.nextSibling, _ = d.firstChild, m = _.nextSibling;
    return m.nextSibling, h.$$click = () => n(!t()), i(d, l, m), i(h, f(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var o = an(), r = o.firstChild, g = r.nextSibling;
        return r.$$click = (u) => {
          var s;
          u.stopPropagation(), (s = e.onAddContinuousEvent) == null || s.call(e);
        }, g.$$click = (u) => {
          var s;
          u.stopPropagation(), (s = e.onAddDiscreteEvent) == null || s.call(e);
        }, o;
      }
    }), null), i(c, f(C, {
      get when() {
        return t();
      },
      get children() {
        var o = un();
        return i(o, f(C, {
          get when() {
            return (e.continuousEvents || []).length > 0;
          },
          get children() {
            var r = sn();
            return r.firstChild, i(r, f(F, {
              get each() {
                return e.continuousEvents || [];
              },
              children: (g) => (() => {
                var u = gn(), s = u.firstChild;
                return i(s, () => g.name || "Unnamed Event"), i(u, f(C, {
                  get when() {
                    return g.description;
                  },
                  get children() {
                    var $ = qe();
                    return i($, () => g.description), $;
                  }
                }), null), u;
              })()
            }), null), r;
          }
        }), null), i(o, f(C, {
          get when() {
            return (e.discreteEvents || []).length > 0;
          },
          get children() {
            var r = on();
            return r.firstChild, i(r, f(F, {
              get each() {
                return e.discreteEvents || [];
              },
              children: (g) => (() => {
                var u = fn(), s = u.firstChild;
                return i(s, () => g.name || "Unnamed Event"), i(u, f(C, {
                  get when() {
                    return g.description;
                  },
                  get children() {
                    var $ = qe();
                    return i($, () => g.description), $;
                  }
                }), null), u;
              })()
            }), null), r;
          }
        }), null), i(o, f(C, {
          get when() {
            return l() === 0;
          },
          get children() {
            var r = dn(), g = r.firstChild;
            return g.nextSibling, i(r, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var u = cn(), s = u.firstChild, $ = s.nextSibling;
                return K(s, "click", e.onAddContinuousEvent, !0), K($, "click", e.onAddDiscreteEvent, !0), u;
              }
            }), null), r;
          }
        }), null), o;
      }
    }), null), N(() => W(a, `expand-icon ${t() ? "expanded" : ""}`)), c;
  })();
}, tl = (e) => {
  const [t, n] = j(/* @__PURE__ */ new Set()), l = (u) => {
    if (e.readonly || !e.onModelChange) return;
    const s = {
      ...e.model,
      ...u
    };
    e.onModelChange(s);
  }, c = () => {
    console.log("Add variable");
  }, h = (u) => {
    console.log("Edit variable:", u.name);
  }, a = (u) => {
    const s = (e.model.variables || []).filter(($) => $.name !== u);
    l({
      variables: s
    });
  }, d = () => {
    const u = {
      lhs: "_placeholder_",
      rhs: 0
    }, s = [...e.model.equations || [], u];
    l({
      equations: s
    });
  }, _ = (u, s) => {
    const $ = [...e.model.equations || []];
    $[u] = s, l({
      equations: $
    });
  }, m = (u) => {
    const s = (e.model.equations || []).filter(($, y) => y !== u);
    l({
      equations: s
    });
  }, o = () => {
    console.log("Add continuous event");
  }, r = () => {
    console.log("Add discrete event");
  }, g = () => {
    const u = ["model-editor"];
    return e.readonly && u.push("readonly"), e.class && u.push(e.class), u.join(" ");
  };
  return (() => {
    var u = vn(), s = u.firstChild, $ = s.firstChild, y = $.firstChild, P = y.firstChild, V = y.nextSibling;
    return i(P, () => e.model.name || "Untitled Model"), i(y, f(C, {
      get when() {
        return e.model.description;
      },
      get children() {
        var E = $n();
        return i(E, () => e.model.description), E;
      }
    }), null), i(V, f(bn, {
      get variables() {
        return e.model.variables;
      },
      onAddVariable: c,
      onEditVariable: h,
      onRemoveVariable: a,
      get readonly() {
        return e.readonly;
      }
    }), null), i(V, f(yn, {
      get equations() {
        return e.model.equations;
      },
      get highlightedVars() {
        return t();
      },
      onAddEquation: d,
      onEditEquation: _,
      onRemoveEquation: m,
      get readonly() {
        return e.readonly;
      }
    }), null), i(V, f(xn, {
      get continuousEvents() {
        return e.model.continuous_events;
      },
      get discreteEvents() {
        return e.model.discrete_events;
      },
      onAddContinuousEvent: o,
      onAddDiscreteEvent: r,
      get readonly() {
        return e.readonly;
      }
    }), null), i(s, f(C, {
      get when() {
        return J(() => !!e.showPalette)() && !e.readonly;
      },
      get children() {
        var E = mn();
        return i(E, f(It, {
          get currentModel() {
            return e.model;
          },
          visible: !0
        })), E;
      }
    }), null), N(() => W(u, g())), u;
  })();
};
z(["click"]);
var wn = /* @__PURE__ */ v('<span class=reaction-name title="Reaction name">'), Cn = /* @__PURE__ */ v('<button class=reaction-remove-btn title="Remove reaction">×'), Sn = /* @__PURE__ */ v('<div class=reaction-rate-editor><div class=rate-editor-header><span>Rate Expression:</span><button class=collapse-btn title="Collapse rate editor">▲</button></div><div class=rate-editor-content>'), En = /* @__PURE__ */ v("<div class=reaction-description>"), kn = /* @__PURE__ */ v("<div class=reaction-item><div class=reaction-header><div class=reaction-equation><span class=reactants></span><span class=reaction-arrow>→<span>[<!>]</span></span><span class=products></span></div><div class=reaction-controls>"), pn = /* @__PURE__ */ v("<div class=no-rate-placeholder><span>No rate expression defined</span><button class=add-rate-btn>Add rate constant"), An = /* @__PURE__ */ v('<button class=add-btn title="Add new species"aria-label="Add new species">+'), Pn = /* @__PURE__ */ v("<button class=add-first-btn>Add first species"), Rn = /* @__PURE__ */ v("<div class=empty-state><div class=empty-icon>🧪</div><div class=empty-text>No species defined"), qn = /* @__PURE__ */ v("<div class=species-content>"), Vn = /* @__PURE__ */ v("<div class=species-panel><div class=panel-header><span>▶</span><h3>Species (<!>)"), Dn = /* @__PURE__ */ v("<span class=species-name>(<!>)"), Nn = /* @__PURE__ */ v("<div class=species-description>"), Tn = /* @__PURE__ */ v('<button class=species-remove-btn title="Remove species">×'), Mn = /* @__PURE__ */ v("<div class=species-item><div class=species-info><span class=species-formula>"), In = /* @__PURE__ */ v('<button class=add-btn title="Add new parameter"aria-label="Add new parameter">+'), Ln = /* @__PURE__ */ v("<button class=add-first-btn>Add first parameter"), jn = /* @__PURE__ */ v("<div class=empty-state><div class=empty-icon>⚗️</div><div class=empty-text>No parameters defined"), On = /* @__PURE__ */ v("<div class=parameters-content>"), Fn = /* @__PURE__ */ v("<div class=parameters-panel><div class=panel-header><span>▶</span><h3>Parameters (<!>)"), Hn = /* @__PURE__ */ v("<span class=parameter-unit>[<!>]"), Un = /* @__PURE__ */ v("<span class=parameter-value>= "), Bn = /* @__PURE__ */ v("<div class=parameter-description>"), Wn = /* @__PURE__ */ v('<button class=parameter-remove-btn title="Remove parameter">×'), Yn = /* @__PURE__ */ v("<div class=parameter-item><div class=parameter-info><span class=parameter-name>"), Gn = /* @__PURE__ */ v('<button class=add-reaction-btn title="Add new reaction">+ Add Reaction'), Jn = /* @__PURE__ */ v("<button class=add-first-btn>Add first reaction"), Xn = /* @__PURE__ */ v("<div class=empty-state><div class=empty-icon>⚛️</div><div class=empty-text>No reactions defined"), zn = /* @__PURE__ */ v("<div><div class=reaction-editor-layout><div class=reactions-main><div class=reactions-header><h2>Reactions (<!>)</h2></div><div class=reactions-list></div></div><div class=reaction-sidebar>");
const be = (e) => e.replace(/(\d+)/g, (t) => {
  const n = "₀₁₂₃₄₅₆₇₈₉";
  return t.split("").map((l) => n[parseInt(l, 10)]).join("");
}), Qn = (e) => {
  const [t, n] = j(!1), [l, c] = j(null), [h, a] = j(null), d = M(() => {
    const s = /* @__PURE__ */ new Map();
    return e.species.forEach(($) => {
      s.set($.name, $);
    }), s;
  }), _ = M(() => {
    const s = e.highlightedVars || /* @__PURE__ */ new Set(), $ = h();
    return $ && !s.has($) ? /* @__PURE__ */ new Set([...s, $]) : s;
  }), m = () => e.reaction.reactants ? e.reaction.reactants.map((s, $) => {
    const y = d().get(s.species), P = (y == null ? void 0 : y.formula) || s.species, V = s.stoichiometry !== void 0 ? s.stoichiometry : 1;
    return `${V > 1 ? V : ""}${be(P)}`;
  }).join(" + ") : "", o = () => e.reaction.products ? e.reaction.products.map((s, $) => {
    const y = d().get(s.species), P = (y == null ? void 0 : y.formula) || s.species, V = s.stoichiometry !== void 0 ? s.stoichiometry : 1;
    return `${V > 1 ? V : ""}${be(P)}`;
  }).join(" + ") : "", r = () => {
    e.readonly || n(!t());
  }, g = (s) => {
    if (e.readonly || !e.onEditReaction) return;
    const $ = {
      ...e.reaction,
      rate: s
    };
    e.onEditReaction(e.index, $);
  }, u = () => {
    var s;
    e.readonly || (s = e.onRemoveReaction) == null || s.call(e, e.index);
  };
  return (() => {
    var s = kn(), $ = s.firstChild, y = $.firstChild, P = y.firstChild, V = P.nextSibling, E = V.firstChild, x = E.nextSibling, S = x.firstChild, A = S.nextSibling;
    A.nextSibling;
    var I = V.nextSibling, k = y.nextSibling;
    return i(P, m), x.$$click = r, i(x, () => e.reaction.rate ? "k" : "?", A), i(I, o), i(k, f(C, {
      get when() {
        return e.reaction.name;
      },
      get children() {
        var R = wn();
        return i(R, () => e.reaction.name), R;
      }
    }), null), i(k, f(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var R = Cn();
        return R.$$click = u, N(() => D(R, "aria-label", `Remove reaction ${e.index + 1}`)), R;
      }
    }), null), i(s, f(C, {
      get when() {
        return t();
      },
      get children() {
        var R = Sn(), w = R.firstChild, b = w.firstChild, q = b.nextSibling, T = w.nextSibling;
        return q.$$click = () => n(!1), i(T, f(C, {
          get when() {
            return e.reaction.rate;
          },
          get fallback() {
            return (() => {
              var p = pn(), L = p.firstChild, H = L.nextSibling;
              return H.$$click = () => g("k_rate"), p;
            })();
          },
          get children() {
            return f(ge, {
              get expr() {
                return e.reaction.rate;
              },
              path: ["rate"],
              highlightedVars: () => _(),
              onHoverVar: a,
              onSelect: c,
              onReplace: (p, L) => {
                p.length === 1 && p[0] === "rate" && g(L);
              },
              get selectedPath() {
                return l();
              }
            });
          }
        })), R;
      }
    }), null), i(s, f(C, {
      get when() {
        return e.reaction.description;
      },
      get children() {
        var R = En();
        return i(R, () => e.reaction.description), R;
      }
    }), null), N((R) => {
      var w = `rate-expression ${t() ? "expanded" : ""} ${e.readonly ? "" : "clickable"}`, b = e.readonly ? void 0 : "Click to edit rate expression";
      return w !== R.e && W(x, R.e = w), b !== R.t && D(x, "title", R.t = b), R;
    }, {
      e: void 0,
      t: void 0
    }), s;
  })();
}, Kn = (e) => {
  const [t, n] = j(!0);
  return (() => {
    var l = Vn(), c = l.firstChild, h = c.firstChild, a = h.nextSibling, d = a.firstChild, _ = d.nextSibling;
    return _.nextSibling, c.$$click = () => n(!t()), i(a, () => (e.species || []).length, _), i(c, f(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var m = An();
        return m.$$click = (o) => {
          var r;
          o.stopPropagation(), (r = e.onAddSpecies) == null || r.call(e);
        }, m;
      }
    }), null), i(l, f(C, {
      get when() {
        return t();
      },
      get children() {
        var m = qn();
        return i(m, f(F, {
          get each() {
            return e.species || [];
          },
          children: (o) => (() => {
            var r = Mn(), g = r.firstChild, u = g.firstChild;
            return r.$$click = () => {
              var s;
              return (s = e.onEditSpecies) == null ? void 0 : s.call(e, o);
            }, i(u, () => be(o.formula || o.name)), i(g, f(C, {
              get when() {
                return o.name !== o.formula;
              },
              get children() {
                var s = Dn(), $ = s.firstChild, y = $.nextSibling;
                return y.nextSibling, i(s, () => o.name, y), s;
              }
            }), null), i(r, f(C, {
              get when() {
                return o.description;
              },
              get children() {
                var s = Nn();
                return i(s, () => o.description), s;
              }
            }), null), i(r, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var s = Tn();
                return s.$$click = ($) => {
                  var y;
                  $.stopPropagation(), (y = e.onRemoveSpecies) == null || y.call(e, o.name);
                }, N(() => D(s, "aria-label", `Remove species ${o.name}`)), s;
              }
            }), null), r;
          })()
        }), null), i(m, f(C, {
          get when() {
            return (e.species || []).length === 0;
          },
          get children() {
            var o = Rn(), r = o.firstChild;
            return r.nextSibling, i(o, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var g = Pn();
                return K(g, "click", e.onAddSpecies, !0), g;
              }
            }), null), o;
          }
        }), null), m;
      }
    }), null), N(() => W(h, `expand-icon ${t() ? "expanded" : ""}`)), l;
  })();
}, Zn = (e) => {
  const [t, n] = j(!0), l = M(() => (e.parameters || []).filter((c) => c.name.startsWith("k_") || c.name.includes("rate") || c.name.includes("const")));
  return (() => {
    var c = Fn(), h = c.firstChild, a = h.firstChild, d = a.nextSibling, _ = d.firstChild, m = _.nextSibling;
    return m.nextSibling, h.$$click = () => n(!t()), i(d, () => l().length, m), i(h, f(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var o = In();
        return o.$$click = (r) => {
          var g;
          r.stopPropagation(), (g = e.onAddParameter) == null || g.call(e);
        }, o;
      }
    }), null), i(c, f(C, {
      get when() {
        return t();
      },
      get children() {
        var o = On();
        return i(o, f(F, {
          get each() {
            return l();
          },
          children: (r) => (() => {
            var g = Yn(), u = g.firstChild, s = u.firstChild;
            return g.$$click = () => {
              var $;
              return ($ = e.onEditParameter) == null ? void 0 : $.call(e, r);
            }, i(s, () => r.name), i(u, f(C, {
              get when() {
                return r.unit;
              },
              get children() {
                var $ = Hn(), y = $.firstChild, P = y.nextSibling;
                return P.nextSibling, i($, () => r.unit, P), $;
              }
            }), null), i(u, f(C, {
              get when() {
                return r.default_value !== void 0;
              },
              get children() {
                var $ = Un();
                return $.firstChild, i($, () => r.default_value, null), $;
              }
            }), null), i(g, f(C, {
              get when() {
                return r.description;
              },
              get children() {
                var $ = Bn();
                return i($, () => r.description), $;
              }
            }), null), i(g, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var $ = Wn();
                return $.$$click = (y) => {
                  var P;
                  y.stopPropagation(), (P = e.onRemoveParameter) == null || P.call(e, r.name);
                }, N(() => D($, "aria-label", `Remove parameter ${r.name}`)), $;
              }
            }), null), g;
          })()
        }), null), i(o, f(C, {
          get when() {
            return l().length === 0;
          },
          get children() {
            var r = jn(), g = r.firstChild;
            return g.nextSibling, i(r, f(C, {
              get when() {
                return !e.readonly;
              },
              get children() {
                var u = Ln();
                return K(u, "click", e.onAddParameter, !0), u;
              }
            }), null), r;
          }
        }), null), o;
      }
    }), null), N(() => W(a, `expand-icon ${t() ? "expanded" : ""}`)), c;
  })();
}, nl = (e) => {
  const t = (g) => {
    if (e.readonly || !e.onReactionSystemChange) return;
    const u = {
      ...e.reactionSystem,
      ...g
    };
    e.onReactionSystemChange(u);
  }, n = () => {
    const g = {
      reactants: [{
        species: "A",
        stoichiometry: 1
      }],
      products: [{
        species: "B",
        stoichiometry: 1
      }],
      rate: "k_rate"
    }, u = [...e.reactionSystem.reactions || [], g];
    t({
      reactions: u
    });
  }, l = (g, u) => {
    const s = [...e.reactionSystem.reactions || []];
    s[g] = u, t({
      reactions: s
    });
  }, c = (g) => {
    const u = (e.reactionSystem.reactions || []).filter((s, $) => $ !== g);
    t({
      reactions: u
    });
  }, h = () => {
    console.log("Add species");
  }, a = (g) => {
    console.log("Edit species:", g.name);
  }, d = (g) => {
    const u = (e.reactionSystem.species || []).filter((s) => s.name !== g);
    t({
      species: u
    });
  }, _ = () => {
    console.log("Add parameter");
  }, m = (g) => {
    console.log("Edit parameter:", g.name);
  }, o = (g) => {
    console.log("Remove parameter:", g);
  }, r = () => {
    const g = ["reaction-editor"];
    return e.readonly && g.push("readonly"), e.class && g.push(e.class), g.join(" ");
  };
  return (() => {
    var g = zn(), u = g.firstChild, s = u.firstChild, $ = s.firstChild, y = $.firstChild, P = y.firstChild, V = P.nextSibling;
    V.nextSibling;
    var E = $.nextSibling, x = s.nextSibling;
    return i(y, () => (e.reactionSystem.reactions || []).length, V), i($, f(C, {
      get when() {
        return !e.readonly;
      },
      get children() {
        var S = Gn();
        return S.$$click = n, S;
      }
    }), null), i(E, f(F, {
      get each() {
        return e.reactionSystem.reactions || [];
      },
      children: (S, A) => f(Qn, {
        reaction: S,
        get index() {
          return A();
        },
        get species() {
          return e.reactionSystem.species || [];
        },
        onEditReaction: l,
        onRemoveReaction: c,
        get highlightedVars() {
          return e.highlightedVars;
        },
        get readonly() {
          return e.readonly;
        }
      })
    }), null), i(E, f(C, {
      get when() {
        return (e.reactionSystem.reactions || []).length === 0;
      },
      get children() {
        var S = Xn(), A = S.firstChild;
        return A.nextSibling, i(S, f(C, {
          get when() {
            return !e.readonly;
          },
          get children() {
            var I = Jn();
            return I.$$click = n, I;
          }
        }), null), S;
      }
    }), null), i(x, f(Kn, {
      get species() {
        return e.reactionSystem.species;
      },
      onAddSpecies: h,
      onEditSpecies: a,
      onRemoveSpecies: d,
      get readonly() {
        return e.readonly;
      }
    }), null), i(x, f(Zn, {
      parameters: [],
      onAddParameter: _,
      onEditParameter: m,
      onRemoveParameter: o,
      get readonly() {
        return e.readonly;
      }
    }), null), N(() => W(g, r())), g;
  })();
};
z(["click"]);
var ei = /* @__PURE__ */ v("<svg><rect width=50 height=30></svg>", !1, !0, !1), ti = /* @__PURE__ */ v("<svg><ellipse rx=25 ry=15></svg>", !1, !0, !1), ni = /* @__PURE__ */ v("<svg><polygon></svg>", !1, !0, !1), ii = /* @__PURE__ */ v("<svg><circle r=20></svg>", !1, !0, !1), li = /* @__PURE__ */ v("<svg><line></svg>", !1, !0, !1), ri = /* @__PURE__ */ v('<div class="absolute top-4 right-4 border border-gray-300 bg-white bg-opacity-90"><svg width=150 height=150><rect width=100% height=100% fill=white stroke=gray></rect><rect fill=none stroke=red stroke-width=1>'), ai = /* @__PURE__ */ v("<svg><circle r=2></svg>", !1, !0, !1), Ve = /* @__PURE__ */ v('<p class="text-sm mt-2">'), si = /* @__PURE__ */ v("<div>Species: "), oi = /* @__PURE__ */ v('<div><h3 class="font-bold text-lg"></h3><p class="text-sm text-gray-600">Type: </p><div class="text-xs mt-2"><div>Variables: </div><div>Equations: '), ci = /* @__PURE__ */ v('<div><h3 class="font-bold text-lg"></h3><p class="text-sm text-gray-600">Type: </p><p class=text-sm>From: <!> → To: '), di = /* @__PURE__ */ v('<div class="absolute bottom-4 left-4 p-4 bg-white border border-gray-300 rounded shadow-lg max-w-md"><button class="mt-2 px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded">Close'), ui = /* @__PURE__ */ v('<div class="relative w-full h-full"><svg class="border border-gray-300"><defs><marker id=arrowhead markerWidth=10 markerHeight=7 refX=9 refY=3.5 orient=auto><polygon points="0 0, 10 3.5, 0 7"fill=#999></polygon></marker></defs><g class=edges></g><g class=nodes></g><g class=labels>'), hi = /* @__PURE__ */ v("<svg><text text-anchor=middle font-size=12 fill=black pointer-events=none></svg>", !1, !0, !1);
const ne = (e) => {
  let t = null, n = !1;
  const l = () => {
    if (n) return;
    const c = 400, h = 300, a = Math.min(200, Math.max(100, e.length * 15));
    e.forEach((d, _) => {
      const m = _ / e.length * 2 * Math.PI;
      d.x = c + Math.cos(m) * a, d.y = h + Math.sin(m) * a;
    }), t == null || t();
  };
  return setTimeout(l, 10), {
    force: (c, h) => ne(e),
    on: (c, h) => (c === "tick" && (t = h), ne(e)),
    nodes: (c) => ne(c),
    alpha: (c) => ne(e),
    restart: () => (setTimeout(l, 10), ne(e)),
    stop: () => {
      n = !0;
    }
  };
}, gi = (e) => ne(e), fi = () => ({
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
}), $i = () => ({
  strength: (e) => ({})
}), mi = (e, t) => ({}), vi = () => ({
  radius: (e) => ({})
}), il = (e) => {
  const t = () => e.width ?? 800, n = () => e.height ?? 600, l = M(() => [...e.graph.nodes]), c = M(() => e.graph.edges.map((w) => ({
    source: l().find((b) => b.id === w.source),
    target: l().find((b) => b.id === w.target),
    data: w.data
  }))), [h, a] = j(null), [d, _] = j(null), [m, o] = j(null), [r, g] = j({
    x: 0,
    y: 0,
    k: 1
  });
  let u, s;
  const $ = () => {
    const w = l();
    c(), s = gi(w).force("link", fi().id((b) => b.id).distance(100).strength(0.1)).force("charge", $i().strength(-300)).force("center", mi(t() / 2, n() / 2)).force("collision", vi().radius(30)).on("tick", () => {
      y([...w]);
    }), w.forEach((b) => {
      b.x === void 0 && (b.x = t() / 2 + (Math.random() - 0.5) * 100), b.y === void 0 && (b.y = n() / 2 + (Math.random() - 0.5) * 100);
    });
  }, [, y] = j(l(), {
    equals: !1
  }), P = (w) => {
    var q;
    const b = {
      stroke: "#333",
      "stroke-width": ((q = h()) == null ? void 0 : q.id) === w.id ? 3 : 1,
      cursor: "pointer",
      filter: m() === w.id ? "brightness(1.2)" : "none"
    };
    switch (w.type) {
      case "model":
        return {
          ...b,
          fill: "#4CAF50",
          rx: 5,
          ry: 5
        };
      case "data_loader":
        return {
          ...b,
          fill: "#2196F3"
        };
      case "operator":
        return {
          ...b,
          fill: "#FF9800"
        };
      case "reaction_system":
        return {
          ...b,
          fill: "#9C27B0"
        };
      default:
        return {
          ...b,
          fill: "#607D8B"
        };
    }
  }, V = (w) => {
    var q;
    const b = {
      stroke: "#999",
      "stroke-width": ((q = d()) == null ? void 0 : q.id) === w.id ? 3 : 1,
      cursor: "pointer",
      "marker-end": "url(#arrowhead)",
      filter: m() === w.id ? "brightness(1.5)" : "none"
    };
    switch (w.type) {
      case "variable":
        return {
          ...b,
          "stroke-dasharray": "none"
        };
      case "temporal":
        return {
          ...b,
          "stroke-dasharray": "5,5"
        };
      case "spatial":
        return {
          ...b,
          "stroke-dasharray": "10,2"
        };
      default:
        return b;
    }
  }, E = (w) => {
    var b;
    a((q) => (q == null ? void 0 : q.id) === w.id ? null : w), _(null), (b = e.onNodeSelect) == null || b.call(e, w);
  }, x = (w) => {
    var b;
    _((q) => (q == null ? void 0 : q.id) === w.id ? null : w), a(null), (b = e.onEdgeSelect) == null || b.call(e, w);
  }, S = (w, b) => {
    s && (w.fx = b.offsetX, w.fy = b.offsetY, s.alpha(0.3).restart());
  }, A = (w) => {
    w.preventDefault();
    const b = w.deltaY > 0 ? 0.9 : 1.1, q = r();
    g({
      ...q,
      k: Math.max(0.1, Math.min(3, q.k * b))
    });
  };
  ze(() => {
    $(), u && u.addEventListener("wheel", A, {
      passive: !1
    });
  }), Qe(() => {
    s == null || s.stop(), u && u.removeEventListener("wheel", A);
  }), M(() => {
    var w, b, q;
    s && (l() !== s.nodes() || c() !== ((w = s.force("link")) == null ? void 0 : w.links())) && (s.nodes(l()), (q = (b = s.force("link")) == null ? void 0 : b.links) == null || q.call(b, c()), s.alpha(0.3).restart());
  });
  const I = (w) => {
    const b = P(w), q = w.x ?? 0, T = w.y ?? 0;
    switch (w.type) {
      case "model":
      case "reaction_system":
        return (() => {
          var p = ei();
          return D(p, "x", q - 25), D(p, "y", T - 15), se(p, ae(b, {
            onClick: () => E(w),
            onMouseEnter: () => o(w.id),
            onMouseLeave: () => o(null),
            onMouseDown: (L) => S(w, L)
          }), !0), p;
        })();
      case "data_loader":
        return (() => {
          var p = ti();
          return D(p, "cx", q), D(p, "cy", T), se(p, ae(b, {
            onClick: () => E(w),
            onMouseEnter: () => o(w.id),
            onMouseLeave: () => o(null),
            onMouseDown: (L) => S(w, L)
          }), !0), p;
        })();
      case "operator":
        return (() => {
          var p = ni();
          return D(p, "points", `${q},${T - 20} ${q + 20},${T} ${q},${T + 20} ${q - 20},${T}`), se(p, ae(b, {
            onClick: () => E(w),
            onMouseEnter: () => o(w.id),
            onMouseLeave: () => o(null),
            onMouseDown: (L) => S(w, L)
          }), !0), p;
        })();
      default:
        return (() => {
          var p = ii();
          return D(p, "cx", q), D(p, "cy", T), se(p, ae(b, {
            onClick: () => E(w),
            onMouseEnter: () => o(w.id),
            onMouseLeave: () => o(null),
            onMouseDown: (L) => S(w, L)
          }), !0), p;
        })();
    }
  }, k = (w) => {
    if (!w.source.x || !w.source.y || !w.target.x || !w.target.y) return null;
    const b = V(w.data);
    return (() => {
      var q = li();
      return se(q, ae({
        get x1() {
          return w.source.x;
        },
        get y1() {
          return w.source.y;
        },
        get x2() {
          return w.target.x;
        },
        get y2() {
          return w.target.y;
        }
      }, b, {
        onClick: () => x(w.data),
        onMouseEnter: () => o(w.data.id),
        onMouseLeave: () => o(null)
      }), !0), q;
    })();
  }, R = () => {
    const b = Math.min(150 / t(), 150 / n());
    return (() => {
      var q = ri(), T = q.firstChild, p = T.firstChild, L = p.nextSibling;
      return i(T, f(F, {
        get each() {
          return l();
        },
        children: (H) => (() => {
          var O = ai();
          return N((U) => {
            var B = (H.x ?? 0) * b, Y = (H.y ?? 0) * b, G = P(H).fill;
            return B !== U.e && D(O, "cx", U.e = B), Y !== U.t && D(O, "cy", U.t = Y), G !== U.a && D(O, "fill", U.a = G), U;
          }, {
            e: void 0,
            t: void 0,
            a: void 0
          }), O;
        })()
      }), L), N((H) => {
        var O = -r().x * b, U = -r().y * b, B = t() * b / r().k, Y = n() * b / r().k;
        return O !== H.e && D(L, "x", H.e = O), U !== H.t && D(L, "y", H.t = U), B !== H.a && D(L, "width", H.a = B), Y !== H.o && D(L, "height", H.o = Y), H;
      }, {
        e: void 0,
        t: void 0,
        a: void 0,
        o: void 0
      }), q;
    })();
  };
  return (() => {
    var w = ui(), b = w.firstChild, q = b.firstChild, T = q.nextSibling, p = T.nextSibling, L = p.nextSibling, H = u;
    return typeof H == "function" ? je(H, b) : u = b, i(T, f(F, {
      get each() {
        return c();
      },
      children: (O) => k(O)
    })), i(p, f(F, {
      get each() {
        return l();
      },
      children: (O) => I(O)
    })), i(L, f(F, {
      get each() {
        return l();
      },
      children: (O) => (() => {
        var U = hi();
        return i(U, () => O.name), N((B) => {
          var Y = O.x ?? 0, G = (O.y ?? 0) + 40;
          return Y !== B.e && D(U, "x", B.e = Y), G !== B.t && D(U, "y", B.t = G), B;
        }, {
          e: void 0,
          t: void 0
        }), U;
      })()
    })), i(w, f(C, {
      get when() {
        return e.showMinimap !== !1;
      },
      get children() {
        return f(R, {});
      }
    }), null), i(w, f(C, {
      get when() {
        return h() || d();
      },
      get children() {
        var O = di(), U = O.firstChild;
        return i(O, f(C, {
          get when() {
            return h();
          },
          get children() {
            var B = oi(), Y = B.firstChild, G = Y.nextSibling;
            G.firstChild;
            var Z = G.nextSibling, le = Z.firstChild;
            le.firstChild;
            var re = le.nextSibling;
            return re.firstChild, i(Y, () => h().name), i(G, () => h().type, null), i(B, f(C, {
              get when() {
                return h().description;
              },
              get children() {
                var X = Ve();
                return i(X, () => h().description), X;
              }
            }), Z), i(le, () => h().metadata.var_count, null), i(re, () => h().metadata.eq_count, null), i(Z, f(C, {
              get when() {
                return h().metadata.species_count > 0;
              },
              get children() {
                var X = si();
                return X.firstChild, i(X, () => h().metadata.species_count, null), X;
              }
            }), null), B;
          }
        }), U), i(O, f(C, {
          get when() {
            return d();
          },
          get children() {
            var B = ci(), Y = B.firstChild, G = Y.nextSibling;
            G.firstChild;
            var Z = G.nextSibling, le = Z.firstChild, re = le.nextSibling;
            return re.nextSibling, i(Y, () => d().label), i(G, () => d().type, null), i(Z, () => d().from, re), i(Z, () => d().to, null), i(B, f(C, {
              get when() {
                return d().description;
              },
              get children() {
                var X = Ve();
                return i(X, () => d().description), X;
              }
            }), null), B;
          }
        }), U), U.$$click = () => {
          a(null), _(null);
        }, O;
      }
    }), null), N((O) => {
      var U = t(), B = n(), Y = `transform: translate(${r().x}px, ${r().y}px) scale(${r().k})`;
      return U !== O.e && D(b, "width", O.e = U), B !== O.t && D(b, "height", O.t = B), O.a = Le(b, Y, O.a), O;
    }, {
      e: void 0,
      t: void 0,
      a: void 0
    }), w;
  })();
};
z(["click"]);
var _i = /* @__PURE__ */ v("<span class=error-badge>"), bi = /* @__PURE__ */ v("<span class=warning-badge>"), yi = /* @__PURE__ */ v('<span class=success-badge title="No errors found">✓'), xi = /* @__PURE__ */ v("<div class=validation-success><span class=success-icon>✓</span>No validation errors found. The ESM file is valid."), wi = /* @__PURE__ */ v('<div class=error-section><h4 class="error-section-title error-title">Schema Errors (<!>)</h4><div class=error-list>'), Ci = /* @__PURE__ */ v('<div class=error-section><h4 class="error-section-title error-title">Structural Errors (<!>)</h4><div class=error-list>'), Si = /* @__PURE__ */ v('<div class=error-section><h4 class="error-section-title warning-title">Warnings (<!>)</h4><div class=error-list>'), Ei = /* @__PURE__ */ v("<div class=validation-content>"), ki = /* @__PURE__ */ v("<div><div class=validation-header><h3 class=validation-title>Validation Results</h3><button class=collapse-toggle>"), me = /* @__PURE__ */ v("<div class=error-details>"), De = /* @__PURE__ */ v('<div class="error-item error-severity clickable"role=button tabindex=0><div class=error-header><span class=error-icon>🔴</span><span class=error-code></span><span class=error-path></span></div><div class=error-message>'), ve = /* @__PURE__ */ v("<div class=error-detail><strong>:</strong> "), pi = /* @__PURE__ */ v('<div class="error-item warning-severity clickable"role=button tabindex=0><div class=error-header><span class=error-icon>🟡</span><span class=error-code></span><span class=error-path></span></div><div class=error-message>');
function Ai(e) {
  return "error";
}
const ll = (e) => {
  const t = M(() => Ke(e.esmFile)), n = M(() => {
    const o = t(), r = [];
    return o.schema_errors.forEach((g) => {
      r.push({
        ...g,
        severity: "error",
        type: "schema"
      });
    }), o.structural_errors.forEach((g) => {
      r.push({
        ...g,
        severity: Ai(),
        type: "structural"
      });
    }), r;
  }), l = M(() => {
    const o = n();
    return {
      errors: o.filter((r) => r.severity === "error"),
      warnings: o.filter((r) => r.severity === "warning")
    };
  }), c = M(() => l().errors.length), h = M(() => l().warnings.length), a = M(() => t().is_valid), d = (o) => {
    e.onErrorClick && e.onErrorClick(o.path);
  }, _ = () => {
    e.onToggleCollapsed && e.onToggleCollapsed(!e.collapsed);
  }, m = () => {
    const o = ["validation-panel"];
    return e.collapsed && o.push("collapsed"), a() ? o.push("valid") : o.push("invalid"), e.class && o.push(e.class), o.join(" ");
  };
  return (() => {
    var o = ki(), r = o.firstChild, g = r.firstChild;
    g.firstChild;
    var u = g.nextSibling;
    return r.$$click = _, i(g, f(C, {
      get when() {
        return c() > 0;
      },
      get children() {
        var s = _i();
        return i(s, c), N(() => D(s, "title", `${c()} error(s)`)), s;
      }
    }), null), i(g, f(C, {
      get when() {
        return h() > 0;
      },
      get children() {
        var s = bi();
        return i(s, h), N(() => D(s, "title", `${h()} warning(s)`)), s;
      }
    }), null), i(g, f(C, {
      get when() {
        return a();
      },
      get children() {
        return yi();
      }
    }), null), i(u, () => e.collapsed ? "▶" : "▼"), i(o, f(C, {
      get when() {
        return !e.collapsed;
      },
      get children() {
        var s = Ei();
        return i(s, f(C, {
          get when() {
            return a();
          },
          get children() {
            return xi();
          }
        }), null), i(s, f(C, {
          get when() {
            return !a();
          },
          get children() {
            return [f(C, {
              get when() {
                return l().errors.filter(($) => $.type === "schema").length > 0;
              },
              get children() {
                var $ = wi(), y = $.firstChild, P = y.firstChild, V = P.nextSibling;
                V.nextSibling;
                var E = y.nextSibling;
                return i(y, () => l().errors.filter((x) => x.type === "schema").length, V), i(E, f(F, {
                  get each() {
                    return l().errors.filter((x) => x.type === "schema");
                  },
                  children: (x) => (() => {
                    var S = De(), A = S.firstChild, I = A.firstChild, k = I.nextSibling, R = k.nextSibling, w = A.nextSibling;
                    return S.$$keydown = (b) => {
                      (b.key === "Enter" || b.key === " ") && (b.preventDefault(), d(x));
                    }, S.$$click = () => d(x), i(k, () => x.code), i(R, () => x.path || "$"), i(w, () => x.message), i(S, f(C, {
                      get when() {
                        return Object.keys(x.details).length > 0;
                      },
                      get children() {
                        var b = me();
                        return i(b, f(F, {
                          get each() {
                            return Object.entries(x.details);
                          },
                          children: ([q, T]) => (() => {
                            var p = ve(), L = p.firstChild, H = L.firstChild;
                            return L.nextSibling, i(L, q, H), i(p, () => String(T), null), p;
                          })()
                        })), b;
                      }
                    }), null), N(() => D(R, "title", `Path: ${x.path}`)), S;
                  })()
                })), $;
              }
            }), f(C, {
              get when() {
                return l().errors.filter(($) => $.type === "structural").length > 0;
              },
              get children() {
                var $ = Ci(), y = $.firstChild, P = y.firstChild, V = P.nextSibling;
                V.nextSibling;
                var E = y.nextSibling;
                return i(y, () => l().errors.filter((x) => x.type === "structural").length, V), i(E, f(F, {
                  get each() {
                    return l().errors.filter((x) => x.type === "structural");
                  },
                  children: (x) => (() => {
                    var S = De(), A = S.firstChild, I = A.firstChild, k = I.nextSibling, R = k.nextSibling, w = A.nextSibling;
                    return S.$$keydown = (b) => {
                      (b.key === "Enter" || b.key === " ") && (b.preventDefault(), d(x));
                    }, S.$$click = () => d(x), i(k, () => x.code), i(R, () => x.path || "$"), i(w, () => x.message), i(S, f(C, {
                      get when() {
                        return Object.keys(x.details).length > 0;
                      },
                      get children() {
                        var b = me();
                        return i(b, f(F, {
                          get each() {
                            return Object.entries(x.details);
                          },
                          children: ([q, T]) => (() => {
                            var p = ve(), L = p.firstChild, H = L.firstChild;
                            return L.nextSibling, i(L, q, H), i(p, () => String(T), null), p;
                          })()
                        })), b;
                      }
                    }), null), N(() => D(R, "title", `Path: ${x.path}`)), S;
                  })()
                })), $;
              }
            }), f(C, {
              get when() {
                return h() > 0;
              },
              get children() {
                var $ = Si(), y = $.firstChild, P = y.firstChild, V = P.nextSibling;
                V.nextSibling;
                var E = y.nextSibling;
                return i(y, h, V), i(E, f(F, {
                  get each() {
                    return l().warnings;
                  },
                  children: (x) => (() => {
                    var S = pi(), A = S.firstChild, I = A.firstChild, k = I.nextSibling, R = k.nextSibling, w = A.nextSibling;
                    return S.$$keydown = (b) => {
                      (b.key === "Enter" || b.key === " ") && (b.preventDefault(), d(x));
                    }, S.$$click = () => d(x), i(k, () => x.code), i(R, () => x.path || "$"), i(w, () => x.message), i(S, f(C, {
                      get when() {
                        return Object.keys(x.details).length > 0;
                      },
                      get children() {
                        var b = me();
                        return i(b, f(F, {
                          get each() {
                            return Object.entries(x.details);
                          },
                          children: ([q, T]) => (() => {
                            var p = ve(), L = p.firstChild, H = L.firstChild;
                            return L.nextSibling, i(L, q, H), i(p, () => String(T), null), p;
                          })()
                        })), b;
                      }
                    }), null), N(() => D(R, "title", `Path: ${x.path}`)), S;
                  })()
                })), $;
              }
            })];
          }
        }), null), s;
      }
    }), null), N((s) => {
      var $ = m(), y = e.collapsed ? "Expand validation panel" : "Collapse validation panel";
      return $ !== s.e && W(o, s.e = $), y !== s.t && D(u, "aria-label", s.t = y), s;
    }, {
      e: void 0,
      t: void 0
    }), o;
  })();
};
z(["click", "keydown"]);
var Pi = /* @__PURE__ */ v("<div class=info-item><strong>Title:</strong> "), Ri = /* @__PURE__ */ v("<div class=info-item><strong>Description:</strong> "), qi = /* @__PURE__ */ v("<div class=info-item><strong>Authors:</strong> "), Vi = /* @__PURE__ */ v("<div class=info-item><strong>Created:</strong> "), Di = /* @__PURE__ */ v('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Models (<!>) →</h4><div class=section-content>'), Ni = /* @__PURE__ */ v('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Reaction Systems (<!>) →</h4><div class=section-content>'), Ti = /* @__PURE__ */ v('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Data Loaders (<!>) →</h4><div class=section-content>'), Mi = /* @__PURE__ */ v('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Operators (<!>) →</h4><div class=section-content>'), Ii = /* @__PURE__ */ v('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Coupling Rules (<!>) →</h4><div class=section-content>'), Li = /* @__PURE__ */ v("<div class=info-item><strong>Time:</strong>Start: <!>, End: "), ji = /* @__PURE__ */ v("<div class=info-item><strong>Spatial:</strong> "), Oi = /* @__PURE__ */ v('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Domain Configuration →</h4><div class=section-content>'), Fi = /* @__PURE__ */ v("<div class=info-item><strong>Tolerances:"), Hi = /* @__PURE__ */ v("<div class=info-item><strong>Max Steps:</strong> "), Ui = /* @__PURE__ */ v('<div class=summary-section><h4 class="section-title clickable-section"role=button tabindex=0>Solver Configuration →</h4><div class=section-content><div class=info-item><strong>Type:</strong> '), Bi = /* @__PURE__ */ v("<div class=empty-state><p>This ESM file appears to be empty or contains no major components."), Wi = /* @__PURE__ */ v("<div class=summary-content><div class=summary-section><h4 class=section-title>Format Information</h4><div class=section-content><div class=info-item><strong>Version:</strong> "), Yi = /* @__PURE__ */ v("<div><div class=summary-header><h3 class=summary-title>File Summary</h3><button class=collapse-toggle>"), Ne = /* @__PURE__ */ v('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong></strong> →</div><div class=system-summary>'), Te = /* @__PURE__ */ v('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong></strong> →</div><div class=system-summary>Type: '), Gi = /* @__PURE__ */ v('<div class=system-item><div class="system-name clickable"role=button tabindex=0><strong>Rule </strong> →</div><div class=system-summary>');
function de(e) {
  return e ? Object.keys(e).length : 0;
}
function Ji(e) {
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
function Me(e) {
  const t = [];
  return "variables" in e && e.variables && t.push(`${Object.keys(e.variables).length} variables`), "species" in e && e.species && t.push(`${Object.keys(e.species).length} species`), "parameters" in e && e.parameters && t.push(`${Object.keys(e.parameters).length} parameters`), "equations" in e && e.equations && t.push(`${e.equations.length} equations`), "reactions" in e && e.reactions && t.push(`${e.reactions.length} reactions`), "subsystems" in e && e.subsystems && t.push(`${Object.keys(e.subsystems).length} subsystems`), t.join(", ") || "Empty system";
}
const rl = (e) => {
  const t = M(() => de(e.esmFile.models)), n = M(() => de(e.esmFile.reaction_systems)), l = M(() => de(e.esmFile.data_loaders)), c = M(() => de(e.esmFile.operators)), h = M(() => {
    var m;
    return ((m = e.esmFile.coupling) == null ? void 0 : m.length) || 0;
  }), a = (m, o) => {
    e.onSectionClick && e.onSectionClick(m, o);
  }, d = () => {
    e.onToggleCollapsed && e.onToggleCollapsed(!e.collapsed);
  }, _ = () => {
    const m = ["file-summary"];
    return e.collapsed && m.push("collapsed"), e.class && m.push(e.class), m.join(" ");
  };
  return (() => {
    var m = Yi(), o = m.firstChild, r = o.firstChild, g = r.nextSibling;
    return o.$$click = d, i(g, () => e.collapsed ? "▶" : "▼"), i(m, f(C, {
      get when() {
        return !e.collapsed;
      },
      get children() {
        var u = Wi(), s = u.firstChild, $ = s.firstChild, y = $.nextSibling, P = y.firstChild, V = P.firstChild;
        return V.nextSibling, i(P, () => e.esmFile.esm_version || "Not specified", null), i(y, f(C, {
          get when() {
            return e.esmFile.metadata;
          },
          get children() {
            return [(() => {
              var E = Pi(), x = E.firstChild;
              return x.nextSibling, i(E, () => e.esmFile.metadata.title || "Untitled", null), E;
            })(), f(C, {
              get when() {
                return e.esmFile.metadata.description;
              },
              get children() {
                var E = Ri(), x = E.firstChild;
                return x.nextSibling, i(E, () => e.esmFile.metadata.description, null), E;
              }
            }), f(C, {
              get when() {
                return J(() => !!e.esmFile.metadata.authors)() && e.esmFile.metadata.authors.length > 0;
              },
              get children() {
                var E = qi(), x = E.firstChild;
                return x.nextSibling, i(E, () => e.esmFile.metadata.authors.join(", "), null), E;
              }
            }), f(C, {
              get when() {
                return e.esmFile.metadata.created_date;
              },
              get children() {
                var E = Vi(), x = E.firstChild;
                return x.nextSibling, i(E, () => e.esmFile.metadata.created_date, null), E;
              }
            })];
          }
        }), null), i(u, f(C, {
          get when() {
            return t() > 0;
          },
          get children() {
            var E = Di(), x = E.firstChild, S = x.firstChild, A = S.nextSibling;
            A.nextSibling;
            var I = x.nextSibling;
            return x.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), a("models"));
            }, x.$$click = () => a("models"), i(x, t, A), i(I, f(F, {
              get each() {
                return Object.entries(e.esmFile.models || {});
              },
              children: ([k, R]) => (() => {
                var w = Ne(), b = w.firstChild, q = b.firstChild, T = b.nextSibling;
                return b.$$keydown = (p) => {
                  (p.key === "Enter" || p.key === " ") && (p.preventDefault(), a("models", k));
                }, b.$$click = () => a("models", k), i(q, k), i(T, () => Me(R)), w;
              })()
            })), E;
          }
        }), null), i(u, f(C, {
          get when() {
            return n() > 0;
          },
          get children() {
            var E = Ni(), x = E.firstChild, S = x.firstChild, A = S.nextSibling;
            A.nextSibling;
            var I = x.nextSibling;
            return x.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), a("reaction_systems"));
            }, x.$$click = () => a("reaction_systems"), i(x, n, A), i(I, f(F, {
              get each() {
                return Object.entries(e.esmFile.reaction_systems || {});
              },
              children: ([k, R]) => (() => {
                var w = Ne(), b = w.firstChild, q = b.firstChild, T = b.nextSibling;
                return b.$$keydown = (p) => {
                  (p.key === "Enter" || p.key === " ") && (p.preventDefault(), a("reaction_systems", k));
                }, b.$$click = () => a("reaction_systems", k), i(q, k), i(T, () => Me(R)), w;
              })()
            })), E;
          }
        }), null), i(u, f(C, {
          get when() {
            return l() > 0;
          },
          get children() {
            var E = Ti(), x = E.firstChild, S = x.firstChild, A = S.nextSibling;
            A.nextSibling;
            var I = x.nextSibling;
            return x.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), a("data_loaders"));
            }, x.$$click = () => a("data_loaders"), i(x, l, A), i(I, f(F, {
              get each() {
                return Object.entries(e.esmFile.data_loaders || {});
              },
              children: ([k, R]) => (() => {
                var w = Te(), b = w.firstChild, q = b.firstChild, T = b.nextSibling;
                return T.firstChild, b.$$keydown = (p) => {
                  (p.key === "Enter" || p.key === " ") && (p.preventDefault(), a("data_loaders", k));
                }, b.$$click = () => a("data_loaders", k), i(q, k), i(T, () => R.type || "Unknown", null), i(T, (() => {
                  var p = J(() => !!R.source);
                  return () => p() && ` | Source: ${R.source}`;
                })(), null), i(T, (() => {
                  var p = J(() => !!R.description);
                  return () => p() && ` | ${R.description}`;
                })(), null), w;
              })()
            })), E;
          }
        }), null), i(u, f(C, {
          get when() {
            return c() > 0;
          },
          get children() {
            var E = Mi(), x = E.firstChild, S = x.firstChild, A = S.nextSibling;
            A.nextSibling;
            var I = x.nextSibling;
            return x.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), a("operators"));
            }, x.$$click = () => a("operators"), i(x, c, A), i(I, f(F, {
              get each() {
                return Object.entries(e.esmFile.operators || {});
              },
              children: ([k, R]) => (() => {
                var w = Te(), b = w.firstChild, q = b.firstChild, T = b.nextSibling;
                return T.firstChild, b.$$keydown = (p) => {
                  (p.key === "Enter" || p.key === " ") && (p.preventDefault(), a("operators", k));
                }, b.$$click = () => a("operators", k), i(q, k), i(T, () => R.type || "Unknown", null), i(T, (() => {
                  var p = J(() => !!R.description);
                  return () => p() && ` | ${R.description}`;
                })(), null), w;
              })()
            })), E;
          }
        }), null), i(u, f(C, {
          get when() {
            return h() > 0;
          },
          get children() {
            var E = Ii(), x = E.firstChild, S = x.firstChild, A = S.nextSibling;
            A.nextSibling;
            var I = x.nextSibling;
            return x.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), a("coupling"));
            }, x.$$click = () => a("coupling"), i(x, h, A), i(I, f(F, {
              get each() {
                return e.esmFile.coupling || [];
              },
              children: (k, R) => (() => {
                var w = Gi(), b = w.firstChild, q = b.firstChild;
                q.firstChild;
                var T = b.nextSibling;
                return b.$$keydown = (p) => {
                  (p.key === "Enter" || p.key === " ") && (p.preventDefault(), a("coupling", R().toString()));
                }, b.$$click = () => a("coupling", R().toString()), i(q, () => R() + 1, null), i(T, () => Ji(k)), w;
              })()
            })), E;
          }
        }), null), i(u, f(C, {
          get when() {
            return e.esmFile.domain;
          },
          get children() {
            var E = Oi(), x = E.firstChild, S = x.nextSibling;
            return x.$$keydown = (A) => {
              (A.key === "Enter" || A.key === " ") && (A.preventDefault(), a("domain"));
            }, x.$$click = () => a("domain"), i(S, f(C, {
              get when() {
                return e.esmFile.domain.time;
              },
              get children() {
                var A = Li(), I = A.firstChild, k = I.nextSibling, R = k.nextSibling;
                return R.nextSibling, i(A, () => e.esmFile.domain.time.start ?? "N/A", R), i(A, () => e.esmFile.domain.time.end ?? "N/A", null), i(A, (() => {
                  var w = J(() => !!e.esmFile.domain.time.step);
                  return () => w() && `, Step: ${e.esmFile.domain.time.step}`;
                })(), null), A;
              }
            }), null), i(S, f(C, {
              get when() {
                return e.esmFile.domain.spatial;
              },
              get children() {
                var A = ji(), I = A.firstChild;
                return I.nextSibling, i(A, () => e.esmFile.domain.spatial.type || "Unknown type", null), A;
              }
            }), null), E;
          }
        }), null), i(u, f(C, {
          get when() {
            return e.esmFile.solver;
          },
          get children() {
            var E = Ui(), x = E.firstChild, S = x.nextSibling, A = S.firstChild, I = A.firstChild;
            return I.nextSibling, x.$$keydown = (k) => {
              (k.key === "Enter" || k.key === " ") && (k.preventDefault(), a("solver"));
            }, x.$$click = () => a("solver"), i(A, () => e.esmFile.solver.type || "Not specified", null), i(S, f(C, {
              get when() {
                return e.esmFile.solver.tolerances;
              },
              get children() {
                var k = Fi();
                return k.firstChild, i(k, (() => {
                  var R = J(() => !!e.esmFile.solver.tolerances.absolute);
                  return () => R() && ` Absolute: ${e.esmFile.solver.tolerances.absolute}`;
                })(), null), i(k, (() => {
                  var R = J(() => !!e.esmFile.solver.tolerances.relative);
                  return () => R() && ` Relative: ${e.esmFile.solver.tolerances.relative}`;
                })(), null), k;
              }
            }), null), i(S, f(C, {
              get when() {
                return e.esmFile.solver.max_steps;
              },
              get children() {
                var k = Hi(), R = k.firstChild;
                return R.nextSibling, i(k, () => e.esmFile.solver.max_steps, null), k;
              }
            }), null), E;
          }
        }), null), i(u, f(C, {
          get when() {
            return J(() => t() === 0 && n() === 0 && l() === 0)() && h() === 0;
          },
          get children() {
            return Bi();
          }
        }), null), u;
      }
    }), null), N((u) => {
      var s = _(), $ = e.collapsed ? "Expand file summary" : "Collapse file summary";
      return s !== u.e && W(m, u.e = s), $ !== u.t && D(g, "aria-label", u.t = $), u;
    }, {
      e: void 0,
      t: void 0
    }), m;
  })();
};
z(["click", "keydown"]);
class Xi {
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
      const l = this.find(n);
      return this.parent.set(t, l), l;
    }
    return t;
  }
  // Union two sets by rank
  union(t, n) {
    const l = this.find(t), c = this.find(n);
    if (l === c) return;
    const h = this.rank.get(l) || 0, a = this.rank.get(c) || 0;
    h < a ? this.parent.set(l, c) : h > a ? this.parent.set(c, l) : (this.parent.set(c, l), this.rank.set(l, h + 1));
  }
  // Get all variables in the same equivalence class
  getEquivalenceClass(t) {
    const n = this.find(t), l = /* @__PURE__ */ new Set();
    for (const [c, h] of this.parent.entries())
      this.find(c) === n && l.add(c);
    return l;
  }
  // Get all equivalence classes
  getAllEquivalenceClasses() {
    const t = /* @__PURE__ */ new Map();
    for (const n of this.parent.keys()) {
      const l = this.find(n);
      t.has(l) || t.set(l, this.getEquivalenceClass(n));
    }
    return t;
  }
}
function Ue(e) {
  const t = new Xi();
  if (e.couplings)
    for (const n of e.couplings)
      zi(n, t);
  return t.getAllEquivalenceClasses();
}
function zi(e, t) {
  var n;
  switch (e.type) {
    case "variable_map":
      t.union(e.from, e.to);
      break;
    case "operator_compose":
      if (e.translate)
        for (const [l, c] of Object.entries(e.translate)) {
          const h = typeof c == "string" ? c : c.var;
          t.union(l, h);
        }
      break;
    case "couple2":
      if ((n = e.connector) != null && n.equations)
        for (const l of e.connector.equations)
          t.union(l.from, l.to);
      break;
  }
}
function Be(e, t, n = "model") {
  const l = [];
  return n === "equation" ? (l.push(e), l) : (l.push(e), !e.includes(".") && t && n !== "file" && l.push(`${t}.${e}`), l);
}
const We = ye();
function al(e) {
  const [t, n] = j(null), l = M(() => Ue(e.file)), c = M(() => {
    const a = t();
    if (!a) return /* @__PURE__ */ new Set();
    const d = l(), _ = e.scopingMode || "model", m = Be(a, e.currentModelContext, _), o = /* @__PURE__ */ new Set();
    for (const r of m)
      for (const [g, u] of d.entries())
        if (u.has(r)) {
          for (const s of u)
            fe(s, a, _, e.currentModelContext) && o.add(s);
          break;
        }
    for (const r of m)
      fe(r, a, _, e.currentModelContext) && o.add(r);
    return o;
  }), h = {
    hoveredVar: t,
    setHoveredVar: n,
    highlightedVars: c,
    equivalences: l
  };
  return f(We.Provider, {
    value: h,
    get children() {
      return e.children;
    }
  });
}
function sl() {
  const e = xe(We);
  if (!e)
    throw new Error("useHighlightContext must be used within a HighlightProvider");
  return e;
}
function fe(e, t, n, l) {
  switch (n) {
    case "equation":
      return e === t;
    case "model":
      return !0;
    case "file":
      return !0;
  }
}
function ol(e, t) {
  return t.has(e);
}
function cl(e, t, n = "model") {
  const [l, c] = j(null), h = M(() => Ue(e)), a = M(() => {
    const d = l();
    if (!d) return /* @__PURE__ */ new Set();
    const _ = h(), m = Be(d, t, n), o = /* @__PURE__ */ new Set();
    for (const r of m)
      for (const [, g] of _.entries())
        if (g.has(r)) {
          for (const u of g)
            fe(u, d, n) && o.add(u);
          break;
        }
    for (const r of m)
      fe(r, d, n) && o.add(r);
    return o;
  });
  return {
    hoveredVar: l,
    setHoveredVar: c,
    highlightedVars: a,
    equivalences: h
  };
}
const Ye = ye();
function we(e, t) {
  let n = e;
  for (const l of t) {
    if (n == null) return null;
    if (l === "args" && typeof n == "object" && "args" in n)
      n = n.args;
    else if (typeof l == "number" && Array.isArray(n))
      n = n[l];
    else
      return null;
  }
  return n;
}
function Ge(e, t, n) {
  if (t.length === 0)
    return n;
  let l = JSON.parse(JSON.stringify(e)), c = l;
  for (let a = 0; a < t.length - 1; a++) {
    const d = t[a];
    if (d === "args" && typeof c == "object" && "args" in c)
      c = c.args;
    else if (typeof d == "number" && Array.isArray(c))
      c = c[d];
    else
      throw new Error(`Invalid path segment: ${d}`);
  }
  const h = t[t.length - 1];
  if (typeof h == "number" && Array.isArray(c))
    c[h] = n;
  else
    throw new Error(`Invalid final path segment: ${h}`);
  return l;
}
function Je(e, t) {
  if (t.length === 0)
    return {
      type: "root"
    };
  const n = t.slice(0, -2), l = t[t.length - 1];
  if (typeof l != "number")
    return {
      type: "root"
    };
  const c = we(e, n);
  return c && typeof c == "object" && "op" in c ? {
    type: "operator",
    operator: c.op,
    argIndex: l
  } : {
    type: "root"
  };
}
function Xe(e) {
  const t = [];
  return typeof e == "number" ? t.push("Edit Value", "Convert to Variable", "Wrap in Operator") : typeof e == "string" ? t.push("Edit Variable", "Convert to Number", "Wrap in Operator") : typeof e == "object" && e !== null && "op" in e && t.push("Change Operator", "Add Argument", "Remove Argument", "Unwrap"), t;
}
function Qi(e) {
  if (!e) return [];
  const t = /* @__PURE__ */ new Set();
  if (e.models)
    for (const n of e.models) {
      if (n.variables)
        for (const l of n.variables)
          t.add(l.name);
      if (n.parameters)
        for (const l of n.parameters)
          t.add(l.name);
      if (n.species)
        for (const l of n.species)
          t.add(l.name);
    }
  return Array.from(t).sort();
}
function dl(e) {
  const [t, n] = j(null), [l, c] = j(!1), [h, a] = j(""), d = (s) => {
    const $ = t();
    return !$ || $.length !== s.length ? !1 : $.every((y, P) => y === s[P]);
  }, _ = M(() => {
    const s = t();
    if (!s) return null;
    const $ = e.rootExpression(), y = we($, s);
    if (!y) return null;
    const P = typeof y == "number" ? "number" : typeof y == "string" ? "variable" : "operator", V = typeof y == "object" && "op" in y ? y.op : y;
    return {
      type: P,
      value: V,
      parentContext: Je($, s),
      availableActions: Xe(y),
      path: [...s],
      expression: y
    };
  }), m = (s, $) => {
    const y = e.rootExpression(), P = Ge(y, s, $);
    e.onRootReplace(P);
  }, o = () => {
    const s = _();
    s && (s.type === "number" || s.type === "variable") && (a(String(s.value)), c(!0));
  }, r = () => {
    c(!1), a("");
  }, u = {
    selectedPath: t,
    setSelectedPath: n,
    isSelected: d,
    selectedNodeDetails: _,
    onReplace: m,
    startInlineEdit: o,
    cancelInlineEdit: r,
    confirmInlineEdit: (s) => {
      const $ = t(), y = _();
      if (!$ || !y) return;
      let P;
      if (y.type === "number") {
        const V = parseFloat(s);
        if (isNaN(V)) return;
        P = V;
      } else if (y.type === "variable") {
        if (!s.trim()) return;
        P = s.trim();
      } else
        return;
      m($, P), r();
    },
    isInlineEditing: l,
    inlineEditValue: h,
    setInlineEditValue: a
  };
  return f(Ye.Provider, {
    value: u,
    get children() {
      return e.children;
    }
  });
}
function ul() {
  const e = xe(Ye);
  if (!e)
    throw new Error("useSelectionContext must be used within a SelectionProvider");
  return e;
}
function hl(e, t) {
  const [n, l] = j(null), [c, h] = j(!1), [a, d] = j(""), _ = (r) => {
    const g = n();
    return !g || g.length !== r.length ? !1 : g.every((u, s) => u === r[s]);
  }, m = M(() => {
    const r = n();
    if (!r) return null;
    const g = e(), u = we(g, r);
    if (!u) return null;
    const s = typeof u == "number" ? "number" : typeof u == "string" ? "variable" : "operator", $ = typeof u == "object" && "op" in u ? u.op : u;
    return {
      type: s,
      value: $,
      parentContext: Je(g, r),
      availableActions: Xe(u),
      path: [...r],
      expression: u
    };
  }), o = (r, g) => {
    const u = e(), s = Ge(u, r, g);
    t(s);
  };
  return {
    selectedPath: n,
    setSelectedPath: l,
    isSelected: _,
    selectedNodeDetails: m,
    onReplace: o,
    startInlineEdit: () => {
      const r = m();
      r && (r.type === "number" || r.type === "variable") && (d(String(r.value)), h(!0));
    },
    cancelInlineEdit: () => {
      h(!1), d("");
    },
    confirmInlineEdit: (r) => {
      const g = n(), u = m();
      if (!g || !u) return;
      let s;
      if (u.type === "number") {
        const $ = parseFloat(r);
        if (isNaN($)) return;
        s = $;
      } else if (u.type === "variable") {
        if (!r.trim()) return;
        s = r.trim();
      } else
        return;
      o(g, s), h(!1), d("");
    },
    isInlineEditing: c,
    inlineEditValue: a,
    setInlineEditValue: d
  };
}
function gl(e, t = "") {
  const n = Qi(e);
  if (!t) return n;
  const l = t.toLowerCase();
  return n.filter((c) => c.toLowerCase().includes(l));
}
function fl(e, t) {
  return e.length !== t.length ? !1 : e.every((n, l) => n === t[l]);
}
function $l(e) {
  return e.join(".");
}
function ml(e) {
  return e ? e.split(".").map((t) => {
    const n = parseInt(t, 10);
    return isNaN(n) ? t : n;
  }) : [];
}
export {
  Oe as COMMUTATIVE_OPERATORS,
  il as CouplingGraph,
  He as DraggableExpression,
  Ot as EquationEditor,
  ge as ExpressionNode,
  It as ExpressionPalette,
  rl as FileSummary,
  al as HighlightProvider,
  tl as ModelEditor,
  nl as ReactionEditor,
  dl as SelectionProvider,
  mt as StructuralEditingMenu,
  el as StructuralEditingProvider,
  ll as ValidationPanel,
  $t as WRAP_OPERATORS,
  Ue as buildVarEquivalences,
  cl as createHighlightContext,
  hl as createSelectionContext,
  gl as getVariableSuggestions,
  ol as isHighlighted,
  Be as normalizeScopedReference,
  $l as pathToString,
  fl as pathsEqual,
  ml as stringToPath,
  sl as useHighlightContext,
  ul as useSelectionContext,
  $e as useStructuralEditingContext
};
