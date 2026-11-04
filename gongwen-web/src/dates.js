var GW = GW || {};
(function (GW) {
  "use strict";
  // 与 gongwen/core/dates.py 规则一致
  var DIGITS = { "〇": 0, "○": 0, "Ｏ": 0, "０": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
                 "五": 5, "六": 6, "七": 7, "八": 8, "九": 9 };
  var CN_DATE = /^([〇○Ｏ０零一二三四五六七八九]{4})年([一二三四五六七八九十]{1,3})月([一二三四五六七八九十]{1,3})日$/;

  function small(s) {
    if (s.indexOf("十") < 0) return s.length === 1 && s in DIGITS ? DIGITS[s] : null;
    var parts = s.split("十"), tens = parts[0], ones = parts[1];
    if (tens.length > 1 || ones.length > 1 || (tens && !(tens in DIGITS)) || (ones && !(ones in DIGITS))) return null;
    return (tens ? DIGITS[tens] : 1) * 10 + (ones ? DIGITS[ones] : 0);
  }

  GW.normalizeDate = function (s) {
    var m = CN_DATE.exec(s.trim());
    if (!m) return s;
    var year = m[1].split("").map(function (c) { return String(DIGITS[c]); }).join("");
    var month = small(m[2]), day = small(m[3]);
    if (month === null || day === null || month < 1 || month > 12 || day < 1 || day > 31) return s;
    return year + "年" + month + "月" + day + "日";
  };
})(GW);
