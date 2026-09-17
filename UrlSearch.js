// Recognize web URLs only; do not reinterpret app names or local file paths.
function normalize(input) {
    var value = String(input || "").trim()
    if (/^www\./i.test(value)) value = "https://" + value
    if (value.length > 4096 || /[\s\u0000-\u001f\u007f\\]/.test(value)) return ""
    var match = /^(https?):\/\/([^/?#]+)([/?#].*)?$/i.exec(value)
    if (!match || match[2].indexOf("@") >= 0) return ""
    var host = /^(\[[0-9a-f:]+\]|[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)(?::([0-9]{1,5}))?$/i.exec(match[2])
    if (!host || (host[2] && (Number(host[2]) < 1 || Number(host[2]) > 65535))) return ""
    if (host[1].indexOf("..") >= 0) return ""
    return match[1].toLowerCase() + "://" + match[2] + (match[3] || "")
}
if (typeof module !== "undefined") module.exports = {normalize: normalize}
