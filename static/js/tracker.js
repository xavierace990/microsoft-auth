function getSessionId() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'ms_session_id') return value;
    }
    return null;
}

function sendClickEvent(eventType, data = {}) {
    const sessionId = getSessionId();
    if (!sessionId) return;
    fetch('/api/collect-click/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            session_id: sessionId,
            event_type: eventType || 'click',
            x: data.x || 0,
            y: data.y || 0,
            target: data.target || 'unknown'
        })
    }).catch(() => {});
}

document.addEventListener('click', function(e) {
    sendClickEvent('click', {x: e.clientX, y: e.clientY, target: e.target.tagName});
});

console.log('🔍 Tracker initialized');