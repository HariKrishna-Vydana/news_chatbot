https://webrtchacks.com/an-intro-to-webrtcs-natfirewall-problem/
https://forums.virtualbox.org/viewtopic.php?t=101583
https://medium.com/@fippo/goodbye-macos-webrtc-audio-bug-25a780222a5c
https://discussions.apple.com/thread/255262028?sortBy=rank
https://github.com/blakeblackshear/frigate/issues/7671
https://forum.nomachine.com/topic/webrtc-issues-nat-infinite-looping
https://github.com/pipecat-ai/pipecat/issues/1573
https://www.reddit.com/r/WebRTC/comments/1p60n87/building_a_benchmarking_tool_to_compare_webrtc/
https://docs.livekit.io/reference/telephony/troubleshooting/
https://github.com/pipecat-ai/pipecat/issues/1570

---

# WebRTC "Hanging on Connecting" - Solutions Plan

## Problem Summary
WebRTC connections hang/stall during the "Connecting" phase, never reaching a connected state. This is typically caused by ICE candidate gathering issues, NAT traversal failures, or browser-specific WebRTC restrictions.

## Root Causes Identified

### 1. ICE Candidate Gathering Not Completing (MOST LIKELY FOR PIPECAT)
**From pipecat issue #1570:** The SmallWebRTCTransport doesn't wait for all ICE candidates to be gathered before creating the offer. This causes the connection to get stuck in ICE "checking" state.

### 2. Missing/Misconfigured STUN/TURN Servers
- 80% of WebRTC connectivity problems originate from network configuration or firewall issues
- Public STUN servers (like Google's) can be unreliable due to overload
- Without TURN servers, symmetric NAT users cannot connect at all

### 3. Symmetric NAT
- Test at: https://tomchen.github.io/symmetric-nat-test/
- WebRTC cannot work behind symmetric NAT without TURN relay servers

### 4. Browser Restrictions
- **Ungoogled-Chromium:** WebRTC is intentionally hobbled; fix via `chrome://flags/#webrtc-ip-handling-policy`
- **Firefox:** Doesn't allow loopback addresses by default (change `media.peerconnection.ice.loopback` in about:config)

---

## Implementation Plan

### Step 1: Update Pipecat Packages (CRITICAL)
The ICE gathering fix was merged in pipecat PR #1587 and published to npm.

```bash
# Update web client packages
cd web_client
npm update @pipecat-ai/client-js @pipecat-ai/daily-transport @pipecat-ai/websocket-transport
```

### Step 2: Configure ICE Servers in Backend
Add STUN/TURN server configuration to the backend when creating the WebRTC transport:

**Option A: Use Google's Public STUN (free, but can be unreliable)**
```python
ice_servers = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
    {"urls": "stun:stun2.l.google.com:19302"},
]
```

**Option B: Use Metered TURN Service (recommended for production)**
- Sign up at https://www.metered.ca/stun-turn
- Get TURN credentials and add:
```python
ice_servers = [
    {"urls": "stun:stun.metered.ca:80"},
    {
        "urls": "turn:global.relay.metered.ca:80",
        "username": "<YOUR_USERNAME>",
        "credential": "<YOUR_CREDENTIAL>"
    },
    {
        "urls": "turn:global.relay.metered.ca:443",
        "username": "<YOUR_USERNAME>",
        "credential": "<YOUR_CREDENTIAL>"
    },
]
```

**Option C: Self-host CoTURN (full control)**
```bash
# Install coturn
brew install coturn  # macOS
# or
apt install coturn   # Ubuntu

# Basic config in /etc/turnserver.conf
listening-port=3478
realm=yourdomain.com
server-name=yourdomain.com
lt-cred-mech
user=username:password
```

### Step 3: Pass ICE Servers to SmallWebRTCTransport (if using SmallWebRTC)
For SmallWebRTC transport, configure ICE servers:

```python
# In voice_backend/app.py - if you add SmallWebRTC endpoint
from pipecat.transports.webrtc.small import SmallWebRTCTransport

transport = SmallWebRTCTransport(
    # ... other params,
    ice_servers=ice_servers
)
```

### Step 4: Configure Client-Side ICE Servers
Update the web client to pass ICE servers when connecting:

```typescript
// In web_client/src/App.tsx
const iceServers = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
];

// For SmallWebRTCTransport connection:
await client.connect({
    endpoint: `${VOICE_BACKEND_URL}/webrtc/connect`,
    config: {
        iceServers: iceServers
    }
});
```

### Step 5: Add Debugging
Add WebRTC debugging to identify issues:

```typescript
// In browser console
// Navigate to chrome://webrtc-internals/ while testing

// Or programmatically:
client.on(RTVIEvent.Error, (error) => {
    console.error('WebRTC Error:', error);
});
```

### Step 6: Firewall/Network Checks
Ensure these ports are open:
- **UDP 3478** - STUN
- **TCP/UDP 5349** - TURN over TLS
- **UDP 49152-65535** - Media ports (or your configured range)

---

## Files to Modify

1. **`/voice_backend/app.py`** - Add SmallWebRTCTransport endpoint with ICE server config
2. **`/web_client/src/App.tsx`** - Add SmallWebRTC transport option and ICE config
3. **`/web_client/package.json`** - Add `@pipecat-ai/small-webrtc-transport` dependency

---

## Quick Diagnosis Checklist

- [ ] Test with Google Chrome (not ungoogled-chromium)
- [ ] Check if behind symmetric NAT: https://tomchen.github.io/symmetric-nat-test/
- [ ] Open `chrome://webrtc-internals/` during connection attempt
- [ ] Verify STUN server responds: `curl stun.l.google.com:19302` (should timeout gracefully, not error)
- [ ] Update pipecat packages to latest version

---

## References

- [Pipecat ICE Fix PR #1587](https://github.com/pipecat-ai/pipecat/pull/1587)
- [WebRTC Troubleshooting Guide](https://webrtc.ventures/2025/01/troubleshooting-webrtc-applications/)
- [ICE Candidates Troubleshooting](https://moldstud.com/articles/p-troubleshooting-webrtc-ice-candidates-common-issues-and-solutions-explained)
- [CoTURN Project](https://github.com/coturn/coturn)
- [Metered TURN Service](https://www.metered.ca/stun-turn)



https://github.com/pipecat-ai/pipecat/issues/1808
https://github.com/pipecat-ai/pipecat/issues/1573
https://github.com/pipecat-ai/pipecat/issues/1485
https://github.com/pipecat-ai/pipecat-client-web-transports/pull/70