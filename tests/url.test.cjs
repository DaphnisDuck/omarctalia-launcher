const assert = require('node:assert/strict');
const {normalize:n} = require('../UrlSearch.js');
assert.equal(n(' https://example.com/a?q=one&b=two#three '),'https://example.com/a?q=one&b=two#three');
assert.equal(n('www.example.com/path'),'https://www.example.com/path');
assert.equal(n('http://localhost:3000'),'http://localhost:3000');
assert.equal(n('http://[::1]:8000'),'http://[::1]:8000');
for(const value of ['chromium','node.js','file:///etc/passwd','javascript:alert(1)','ftp://example.com','https://user:pass@example.com','https://example.com:99999','https://example.com\\evil','https://exa mple.com','https://','https://'+ 'x'.repeat(4096)]) assert.equal(n(value),'',value);
console.log('PASS: web URL recognition, query preservation, scheme/credential rejection, and limits');
