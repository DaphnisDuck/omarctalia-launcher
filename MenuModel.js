// Bundled Omarchy menu model, with Omarctalia reliability fixes.
// See UPSTREAM.md and LICENSE-OMARCHY for provenance.
function stripJsonc(raw) {
  var text = String(raw || "");
  var out = "", quoted = false, escaped = false;
  for (var i = 0; i < text.length; i++) {
    var c = text[i], next = text[i + 1];
    if (quoted) {
      out += c;
      if (escaped) escaped = false;
      else if (c === "\\") escaped = true;
      else if (c === '"') quoted = false;
    } else if (c === '"') { quoted = true; out += c; }
    else if (c === "/" && next === "/") {
      out += "  "; i++;
      while (i + 1 < text.length && text[i + 1] !== "\n") { out += " "; i++; }
    } else if (c === "/" && next === "*") {
      out += "  "; i++;
      var closed = false;
      while (++i < text.length) {
        if (text[i] === "*" && text[i + 1] === "/") { out += "  "; i++; closed = true; break; }
        out += text[i] === "\n" ? "\n" : " ";
      }
      if (!closed) throw new Error("Unterminated JSONC comment");
    } else out += c;
  }
  // Remove trailing commas only outside strings (URLs and command text survive).
  var clean = ""; quoted = false; escaped = false;
  for (var j = 0; j < out.length; j++) {
    var ch = out[j];
    if (quoted) {
      clean += ch;
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === '"') quoted = false;
    } else if (ch === '"') { quoted = true; clean += ch; }
    else if (ch === ",") {
      var k = j + 1;
      while (k < out.length && /\s/.test(out[k])) k++;
      clean += out[k] === "}" || out[k] === "]" ? " " : ch;
    } else clean += ch;
  }
  return clean;
}

function normalizeAliases(value) {
  if (Array.isArray(value)) return value.filter(function(v) { return v })
  if (typeof value === "string" && value) return [value]
  return []
}

function normalizeItem(id, raw) {
  var value = raw || {}
  var aliases = normalizeAliases(value.aliases)
  var parent = value.parent
  if (parent === undefined)
    parent = id.indexOf(".") >= 0 ? id.split(".").slice(0, -1).join(".") : "root"
  if (id === "root") parent = ""

  var kind = value.action ? "action" : (value.target ? "link" : "menu")

  return {
    id: id,
    parent: parent,
    kind: kind,
    icon: value.icon || "",
    iconFont: value.iconFont || "",
    label: value.label || id,
    title: value.title || "",
    target: value.target || "",
    description: value.description || "",
    action: value.action || "",
    provider: value.provider || "",
    aliases: aliases,
    when: value.when || "",
    checked: value.checked || ""
  }
}

function parseMenuJsonc(raw) {
  var stripped = stripJsonc(raw);
  if (!stripped.trim()) return [];
  var parsed = JSON.parse(stripped);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
    throw new Error("Menu must be an object keyed by item ID");
  var source = Object.prototype.hasOwnProperty.call(parsed, "items") ? parsed.items : parsed;
  if (!source || typeof source !== "object" || Array.isArray(source))
    throw new Error("Menu items must be an object");
  var strings = ["parent", "icon", "iconFont", "label", "title", "target", "description", "action", "provider", "when", "checked"];
  return Object.keys(source).map(function(id) {
    if (!id || /[\x00-\x1f]/.test(id) || ["__proto__", "constructor", "prototype"].indexOf(id) >= 0)
      throw new Error("Invalid menu item ID");
    var value = source[id];
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid item: " + id);
    var patch = {id: id};
    strings.forEach(function(key) {
      if (Object.prototype.hasOwnProperty.call(value, key)) {
        if (typeof value[key] !== "string") throw new Error(id + "." + key + " must be text");
        patch[key] = value[key];
      }
    });
    if (Object.prototype.hasOwnProperty.call(value, "aliases")) {
      if (typeof value.aliases !== "string" && !(Array.isArray(value.aliases) && value.aliases.every(function(v) { return typeof v === "string"; })))
        throw new Error(id + ".aliases must be text or a list of text");
      patch.aliases = value.aliases;
    }
    return patch;
  });
}

function mergeMenuSources(defaultItems, userItems) {
  var patches = Object.create(null), order = [];
  [defaultItems || [], userItems || []].forEach(function(source) {
    source.forEach(function(patch) {
      if (!patch || !patch.id) return;
      if (!patches[patch.id]) { patches[patch.id] = {}; order.push(patch.id); }
      Object.keys(patch).forEach(function(key) { patches[patch.id][key] = patch[key]; });
    });
  });
  var items = Object.create(null);
  order.forEach(function(id) { items[id] = normalizeItem(id, patches[id]); });
  if (!items.root) { items.root = normalizeItem("root", {label: "Home"}); order.unshift("root"); }
  if (items.root.kind !== "menu") throw new Error("Root must be a menu");
  order.forEach(function(id, index) {
    var entry = items[id]; entry.order = index;
    if (id !== "root" && !items[entry.parent]) throw new Error("Missing parent for " + id + ": " + entry.parent);
    if (entry.kind === "link" && !items[entry.target]) throw new Error("Missing target for " + id);
    if (entry.kind === "link") {
      var linked = entry, links = Object.create(null);
      while (linked && linked.kind === "link") {
        if (links[linked.id]) throw new Error("Menu link cycle at " + id);
        links[linked.id] = true; linked = items[linked.target];
      }
      if (!linked || linked.kind !== "menu") throw new Error("Link must target a menu: " + id);
    }
    var current = entry, seen = Object.create(null);
    while (current && current.id !== "root") {
      if (seen[current.id]) throw new Error("Menu parent cycle at " + id);
      seen[current.id] = true; current = items[current.parent];
    }
  });
  return {items: items, itemOrder: order};
}

// Both merges below return fresh items/itemOrder objects for the caller to
// assign in one go. They must never write into the maps they are handed: those
// live in QML `var` properties, and an in-place write into such an object is
// occasionally dropped by the engine — the key lands with an undefined value.
// A lost write used to leave an id in itemOrder with no item behind it, and
// the next merge then kept that orphan and appended a second row for the same
// app, so the launcher listed it twice (and again on every later rescan).

// Swaps every app row for the current set. Rows keep the order they arrive in;
// ids already claimed (including duplicate desktop ids) are listed once.
function mergeAppRows(items, itemOrder, appRows) {
  var source = items || ({})
  var order = Array.isArray(itemOrder) ? itemOrder : []
  var rows = Array.isArray(appRows) ? appRows : []
  var nextItems = ({})
  var nextOrder = []

  for (var i = 0; i < order.length; i++) {
    var id = order[i]
    var existing = source[id]
    // Orphans (an id with no item) are dropped rather than carried forward,
    // so a single lost write cannot compound into a duplicate row.
    if (!existing || existing.kind === "app") continue
    nextItems[id] = existing
    nextOrder.push(id)
  }

  for (var j = 0; j < rows.length; j++) {
    var row = rows[j]
    if (!row || !row.id || nextItems[row.id]) continue
    row.order = nextOrder.length
    nextItems[row.id] = row
    nextOrder.push(row.id)
  }

  return { items: nextItems, itemOrder: nextOrder }
}

// Swaps the rows one provider contributed, leaving every other item untouched.
// Rows carry the id of the submenu that produced them, so a provider that runs
// again drops its previous batch — a plugin that was just enabled disappears
// from the Enable list — without disturbing static children declared in JSONC.
function swapProviderRows(items, itemOrder, menuId, rows) {
  var source = items || ({})
  var order = Array.isArray(itemOrder) ? itemOrder : []
  var incoming = Array.isArray(rows) ? rows : []
  var nextItems = ({})
  var nextOrder = []

  for (var i = 0; i < order.length; i++) {
    var id = order[i]
    var existing = source[id]
    if (!existing || existing.providerMenu === menuId) continue
    nextItems[id] = existing
    nextOrder.push(id)
  }

  for (var j = 0; j < incoming.length; j++) {
    var row = incoming[j]
    if (!row || !row.id || nextItems[row.id]) continue
    row.providerMenu = menuId
    row.order = nextOrder.length
    nextItems[row.id] = row
    nextOrder.push(row.id)
  }

  return { items: nextItems, itemOrder: nextOrder }
}

function item(items, id) {
  return items && items[id] ? items[id] : null
}

// Routes may name a real id (`system`, `setup.power`) or an alias declared in
// JSONC (`power-menu`, `settings`). An exact id beats any alias, and app rows
// are never routable: their aliases carry .desktop Keywords and GenericName
// for search, so an installed application could otherwise shadow a menu route
// (htop ships `Keywords=system;...`). Unknown strings fall through as the
// literal input so misspellings still attempt to open that id.
function resolveRoute(items, itemOrder, input) {
  var raw = String(input || "").toLowerCase().replace(/_/g, "-")
  if (!raw || raw === "go" || raw === "menu") return "root"
  if (item(items, raw)) return raw
  var order = Array.isArray(itemOrder) ? itemOrder : []
  for (var i = 0; i < order.length; i++) {
    var entry = item(items, order[i])
    if (!entry || entry.kind === "app" || !entry.aliases) continue
    for (var j = 0; j < entry.aliases.length; j++) {
      var alias = String(entry.aliases[j] || "").toLowerCase().replace(/_/g, "-")
      if (alias === raw) return entry.id
    }
  }
  return raw
}

function slugify(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "item"
}

function depthFor(items, id) {
  var depth = 0
  var current = item(items, id)
  var guard = 0

  while (current && current.parent && current.parent !== "root" && guard < 32) {
    depth += 1
    current = item(items, current.parent)
    guard += 1
  }

  return depth
}

function pathFor(items, id) {
  var labels = []
  var current = item(items, id)
  var guard = 0

  while (current && current.id !== "root" && guard < 32) {
    labels.unshift(current.label)
    current = item(items, current.parent)
    guard += 1
  }

  return labels.join(" › ")
}

function parentPathFor(items, id) {
  var entry = item(items, id)
  if (!entry || !entry.parent || entry.parent === "root") return ""
  return pathFor(items, entry.parent)
}

function isDescendantOf(items, id, ancestorId) {
  if (ancestorId === "root") return id !== "root"

  var current = item(items, id)
  var guard = 0
  while (current && current.parent && guard < 32) {
    if (current.parent === ancestorId) return true
    current = item(items, current.parent)
    guard += 1
  }

  return false
}

function childCount(items, itemOrder, id) {
  var count = 0
  var order = Array.isArray(itemOrder) ? itemOrder : []
  for (var i = 0; i < order.length; i++) {
    var entry = item(items, order[i])
    if (entry && entry.parent === id) count += 1
  }
  return count
}

function isVisible(items, itemOrder, whenResults, entry, depth) {
  if (entry && entry.policyBlocked) return false;
  if (!entry) return false
  if (entry.when && (!whenResults || whenResults[entry.id] !== true)) return false
  if (entry.kind !== "menu" && entry.kind !== "link") return true
  if (entry.provider) return true

  var guard = depth || 0
  if (guard >= 32) return false

  var targetEntry = entry
  var hops = 0
  while (targetEntry && targetEntry.kind === "link" && hops++ < 32) {
    targetEntry = item(items, targetEntry.target)
    if (targetEntry && targetEntry.when && (!whenResults || whenResults[targetEntry.id] !== true)) return false
  }
  if (!targetEntry || targetEntry.kind !== "menu") return false
  if (targetEntry.provider) return true
  var target = targetEntry.id
  var order = Array.isArray(itemOrder) ? itemOrder : []
  for (var i = 0; i < order.length; i++) {
    var child = item(items, order[i])
    if (child && child.parent === target && isVisible(items, itemOrder, whenResults, child, guard + 1)) return true
  }

  return false
}

function labelFor(entry, checkedResults) {
  if (!entry) return ""
  if (entry.checked && checkedResults && checkedResults[entry.id]) return entry.label + " ✓"
  return entry.label
}

function searchableToken(value) {
  return String(value || "").replace(/[._-]+/g, " ")
}

function leafIdFor(id) {
  var parts = String(id || "").split(".")
  return parts.length > 0 ? parts[parts.length - 1] : id
}

function nameSearchText(entry) {
  if (!entry) return ""
  var aliases = []
  var values = Array.isArray(entry.aliases) ? entry.aliases : []
  for (var i = 0; i < values.length; i++) aliases.push(searchableToken(values[i]))
  return [entry.label, searchableToken(leafIdFor(entry.id)), aliases.join(" ")].join(" ").toLowerCase()
}

function termInSearchWords(term, text) {
  var words = String(text || "").toLowerCase().split(/\s+/)
  for (var i = 0; i < words.length; i++) {
    if (words[i] === term) return true
  }
  return false
}

function descriptionTextMatches(query, text) {
  var terms = String(query || "").toLowerCase().trim().split(/\s+/)
  for (var i = 0; i < terms.length; i++) {
    if (terms[i] && !termInSearchWords(terms[i], text)) return false
  }
  return true
}

function matchesQuery(entry, query, visible) {
  if (!entry || entry.id === "root") return false
  if (!visible) return false

  var nameText = nameSearchText(entry)
  var descriptionText = String(entry.description || "").toLowerCase()
  var terms = String(query || "").toLowerCase().trim().split(/\s+/)

  for (var i = 0; i < terms.length; i++) {
    if (!terms[i]) continue
    if (nameText.indexOf(terms[i]) >= 0) continue
    if (termInSearchWords(terms[i], descriptionText)) continue
    return false
  }

  return true
}

function searchScore(items, entry, query) {
  var needle = String(query || "").toLowerCase().trim()
  var label = entry.label.toLowerCase()
  var nameText = nameSearchText(entry)
  var descriptionText = String(entry.description || "").toLowerCase()
  var score = 80

  if (label === needle) score = entry.parent === "root" ? 2 : 0
  // An installed app whose name contains the query as a whole word ("zen"
  // for Zen Browser) beats exact-labeled menu entries like Install > Zen.
  else if (entry.kind === "app" && label.split(/\s+/).indexOf(needle) >= 0) score = 0
  else if (label.indexOf(needle) === 0) score = 10
  else if (label.indexOf(needle) >= 0) score = 30
  else if (nameText.indexOf(needle) >= 0) score = 40
  else if (descriptionTextMatches(needle, descriptionText)) score = 60

  if (entry.kind === "menu" || entry.kind === "link") score -= 2
  // App rows sort after all menu items, so they lose the tiebreak below to an
  // equal match. Outrank those, but stay inside the tier so better ones win.
  if (entry.kind === "app") score -= 5

  return score * 1000 + depthFor(items, entry.id) * 25 + entry.order
}

function displayRow(items, itemOrder, checkedResults, entry, detail, score, section) {
  var target = entry.kind === "link" ? entry.target : entry.id
  return {
    itemId: entry.id,
    kind: entry.kind,
    icon: entry.icon,
    iconFont: entry.iconFont || "",
    appIcon: entry.appIcon || "",
    appId: entry.appId || "",
    label: labelFor(entry, checkedResults),
    target: target,
    detail: detail || "",
    path: pathFor(items, entry.id),
    childCount: (entry.kind === "menu" || entry.kind === "link") ? childCount(items, itemOrder, target) : 0,
    action: entry.action || "",
    provider: entry.provider || "",
    score: score || 0,
    section: section || ""
  }
}

// Commands a `checked:` expression reads a value out of. Every sibling row
// asks the same one -- Defaults > Browser has seven rows all comparing
// against `omarchy-default-browser` -- so the batch runs it once and the rows
// read the captured answer.
//
// The capture has to be eager. These are read inside `$(...)`, and a value
// cached while one expression runs lives in that subshell only, so a lazy
// memo never survives to the expression after it.
if (typeof module !== "undefined") {
  module.exports = {
    stripJsonc: stripJsonc,
    normalizeAliases: normalizeAliases,
    normalizeItem: normalizeItem,
    parseMenuJsonc: parseMenuJsonc,
    mergeMenuSources: mergeMenuSources,
    mergeAppRows: mergeAppRows,
    swapProviderRows: swapProviderRows,
    item: item,
    resolveRoute: resolveRoute,
    slugify: slugify,
    depthFor: depthFor,
    pathFor: pathFor,
    parentPathFor: parentPathFor,
    isDescendantOf: isDescendantOf,
    childCount: childCount,
    isVisible: isVisible,
    labelFor: labelFor,
    searchableToken: searchableToken,
    leafIdFor: leafIdFor,
    nameSearchText: nameSearchText,
    termInSearchWords: termInSearchWords,
    descriptionTextMatches: descriptionTextMatches,
    matchesQuery: matchesQuery,
    searchScore: searchScore,
    displayRow: displayRow
  }
}
