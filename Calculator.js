// Bounded arithmetic grammar; never evaluate JavaScript or invoke a shell.
function calculate(input) {
    var source = String(input || "").trim().replace(/×/g, "*").replace(/÷/g, "/").replace(/−/g, "-")
    var explicit = source.charAt(0) === "="
    if (explicit) source = source.substring(1).trim()
    if (!source) return null
    var names = source.match(/[a-zA-Z_]+/g) || []
    if (!explicit && names.some(function(n) { return ["e", "pi", "sqrt", "abs"].indexOf(n.toLowerCase()) < 0 })) return null
    if (!explicit && /[^0-9a-zA-Z\s.+\-*/^()%]/.test(source)) return null
    if (!explicit && !/[0-9]/.test(source) && !/^(pi|e|sqrt\s*\(|abs\s*\()/i.test(source)) return null
    if (source.length > 256) return {error: "Expression is too long"}
    var tokens = [], at = 0, depth = 0
    try {
        var pattern = /\s*(?:(\d+(?:\.\d*)?|\.\d+)([eE][+\-]?\d+)?|([a-zA-Z_]+)|(\*\*|[+\-*/^()%]))/g
        var offset = 0
        while (offset < source.length) {
            pattern.lastIndex = offset
            var match = pattern.exec(source)
            if (!match || match.index !== offset) throw new Error("Check the expression")
            tokens.push(match[1] ? Number(match[1] + (match[2] || "")) : (match[3] || match[4]).toLowerCase())
            if (tokens.length > 128) throw new Error("Expression is too long")
            offset = pattern.lastIndex
        }
        function finite(value) {
            if (!isFinite(value)) throw new Error("Result is outside the supported range")
            return value
        }
        function atom() {
            if (++depth > 32) throw new Error("Too many nested operations")
            var token = tokens[at++], value
            if (typeof token === "number") value = finite(token)
            else if (token === "pi") value = Math.PI
            else if (token === "e") value = Math.E
            else if (token === "(" || token === "sqrt" || token === "abs") {
                if (token !== "(" && tokens[at++] !== "(") throw new Error("Use parentheses after " + token)
                value = sum()
                if (tokens[at++] !== ")") throw new Error("Complete the expression")
                if (token === "sqrt") {
                    if (value < 0) throw new Error("Square root needs a nonnegative number")
                    value = Math.sqrt(value)
                } else if (token === "abs") value = Math.abs(value)
            } else throw new Error(token === undefined ? "Complete the expression" : "Check the expression")
            while (tokens[at] === "%") { at++; value /= 100 }
            depth--
            return value
        }
        function power() {
            var value = atom()
            if (tokens[at] === "^" || tokens[at] === "**") {
                at++
                value = finite(Math.pow(value, unary()))
            }
            return value
        }
        function unary() {
            if (++depth > 32) throw new Error("Too many nested operations")
            var token = tokens[at], value
            if (token === "+" || token === "-") { at++; value = unary(); if (token === "-") value = -value }
            else value = power()
            depth--
            return value
        }
        function product() {
            var value = unary()
            while (tokens[at] === "*" || tokens[at] === "/") {
                var op = tokens[at++], right = unary()
                if (op === "/" && right === 0) throw new Error("Cannot divide by zero")
                value = finite(op === "*" ? value * right : value / right)
            }
            return value
        }
        function sum() {
            var value = product()
            while (tokens[at] === "+" || tokens[at] === "-") {
                var op = tokens[at++], right = product()
                value = finite(op === "+" ? value + right : value - right)
            }
            return value
        }
        var result = sum()
        if (at !== tokens.length) throw new Error("Check the expression")
        // Display useful precision without common binary floating-point tails.
        return {value: String(Number(result.toPrecision(12)))}
    } catch (error) { return {error: error.message} }
}
if (typeof module !== "undefined") module.exports = {calculate: calculate}
