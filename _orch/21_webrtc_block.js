if (POISON) {
  try {
    var _OrigRTC = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
    if (_OrigRTC) {
      var _isLeaky = function(ev) {
        if (!ev || !ev.candidate || !ev.candidate.candidate) return false;
        var c = ev.candidate.candidate;
        return (c.indexOf(' typ host') !== -1) || (c.indexOf(' typ srflx') !== -1);
      };
      var _Wrapped = function(config, constraints) {
        var pc = new _OrigRTC(config, constraints);
        var _origAdd = pc.addEventListener.bind(pc);
        pc.addEventListener = function(type, listener, opts) {
          if (type === 'icecandidate' && typeof listener === 'function') {
            return _origAdd(type, function(ev) { if (_isLeaky(ev)) return; listener(ev); }, opts);
          }
          return _origAdd(type, listener, opts);
        };
        var _userCb = null;
        try {
          Object.defineProperty(pc, 'onicecandidate', {
            configurable: true,
            get: function() { return _userCb; },
            set: function(fn) {
              _userCb = fn;
              _origAdd('icecandidate', function(ev) {
                if (_isLeaky(ev)) return;
                if (typeof _userCb === 'function') _userCb(ev);
              });
            }
          });
        } catch (e) {}
        return pc;
      };
      _Wrapped.prototype = _OrigRTC.prototype;
      window.RTCPeerConnection = _Wrapped;
      if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = _Wrapped;
      if (window.mozRTCPeerConnection) window.mozRTCPeerConnection = _Wrapped;
    }
  } catch (e) {}
}
