if (POISON) { 
    var RTC = window.RTCPeerConnection; 
    if (RTC && RTC.prototype && RTC.prototype.setLocalDescription) { 
        var _origSLD = RTC.prototype.setLocalDescription; 
        RTC.prototype.setLocalDescription = function(description) { 
            if (description && description.sdp) { 
                description.sdp = description.sdp.split('\n').filter(line => { 
                    if (line.startsWith('a=candidate')) { 
                        const tIndex = line.indexOf(' typ '); 
                        if (tIndex !== -1 && (line.substring(tIndex).includes(' host') || line.substring(tIndex).includes(' srflx'))) { 
                            return false; 
                        } 
                    } 
                    return true; 
                }).join('\n'); 
            } 
            return _origSLD.apply(this, arguments); 
        }; 
    } 
}
