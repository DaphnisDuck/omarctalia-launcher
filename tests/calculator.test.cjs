const assert = require('node:assert/strict');
const {calculate:c} = require('../Calculator.js');
for (const [expression,result] of [
 ['2+3*4','14'], ['(12+8)/5','4'],['-2^2','-4'],['2^3^2','512'],['2**-3','0.125'],
 ['20% * 150','30'],['100 + 20%','100.2'],['0.1+0.2','0.3'],['1e3 / 4','250'],
 ['sqrt(144)','12'],['abs(-pi)','3.14159265359'],['= pi','3.14159265359'],
 ['2 × 3 − 1','5'],['8 ÷ 2','4'],['-.5 * 4','-2'],['1 / 8','0.125']
]) assert.equal(c(expression).value,result,expression);
for (const expression of ['1/0','sqrt(-1)','1e999','2+','(2+3','2(3)','2^99999','='.repeat(10), '('.repeat(40)+'1'+')'.repeat(40)])
 assert.ok(c(expression).error,expression);
for (const query of ['', 'chromium','1password','node.js','setup','$(touch /tmp/pwn)','Math.random()','process.exit()']) assert.equal(c(query),null,query);
assert.ok(c('= process.exit()').error);
assert.ok(c('1+'.repeat(200)).error);
console.log('PASS: calculator precedence, percentages, decimals, bounds, errors, and code rejection');
