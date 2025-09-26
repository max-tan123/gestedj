# GesteDJ Web UI - Phase 1 Testing Instructions

## 🎯 Phase 1 Goal
Test basic connectivity between Tauri frontend and Python WebSocket backend.

## 📁 Project Structure
```
gestdj-web-ui/
├── gestdj-ui/                    # Tauri + React app
│   ├── src-tauri/               # Rust backend
│   ├── src/                     # React frontend
│   └── package.json
├── test_websocket_server.py     # Python WebSocket test server
├── test_requirements.txt        # Python dependencies
└── TESTING_INSTRUCTIONS.md     # This file
```

## 🔧 Prerequisites

1. **Node.js and npm** (already installed ✅)
2. **Rust** (already installed ✅)
3. **Python 3.x** with websockets library

## 🚀 Step-by-Step Testing

### Step 1: Install Python Dependencies
```bash
cd /Users/maxtan/Documents/MIT/Hack_MIT_2025/HackMIT2025/gestdj-web-ui

# Install WebSocket library
pip install -r test_requirements.txt
# or
pip install websockets
```

### Step 2: Start Python WebSocket Server
```bash
# From the gestdj-web-ui directory
python test_websocket_server.py
```

**Expected Output:**
```
🚀 Starting GesteDJ WebSocket Test Server
This server simulates the Python backend for testing the Tauri frontend
Press Ctrl+C to stop
--------------------------------------------------
INFO:__main__:Starting GesteDJ test server on localhost:8765
INFO:__main__:✅ WebSocket server started successfully
INFO:__main__:Waiting for Tauri frontend connections...
```

### Step 3: Start Tauri Development Server

**Open a new terminal** and navigate to the React app:
```bash
cd /Users/maxtan/Documents/MIT/Hack_MIT_2025/HackMIT2025/gestdj-web-ui/gestdj-ui

# Start Tauri in development mode
npm run tauri-dev
```

**What should happen:**
1. React development server starts on http://localhost:3000
2. Tauri compiles the Rust backend
3. Desktop app window opens showing the React UI

**Expected initial compilation (first time only):**
- May take 2-3 minutes to download and compile Rust dependencies
- Should end with: "App listening at http://localhost:3000"
- Desktop window opens

### Step 4: Test Tauri Connection

In the opened desktop app:

1. **Click "Test Tauri Connection"**
   - ✅ **Expected**: Message "Hello, GesteDJ User! You've been greeted from Rust!"
   - ❌ **If fails**: Shows "Error: Could not connect to Tauri backend"

### Step 5: Test Python Backend Connection

1. **Make sure Python server is still running** (from Step 2)
2. **Click "Test Python Backend"**
   - ✅ **Expected**: Message "✅ Python backend connected"
   - ❌ **If fails**: Shows "❌ Python backend not running"

### Step 6: Test WebSocket Latency ⏱️

1. **After Python backend connects** (green checkmark from Step 5)
2. **Click "Test WebSocket Latency"**
   - Will run 20 round-trip tests
   - ✅ **Expected**: Results with color-coded performance
   - 🟢 **Excellent**: <20ms average
   - 🟡 **Good**: 20-30ms average
   - 🔴 **Consider PyQt6**: >30ms average

### Step 7: Monitor Server Logs

While testing, watch the Python server terminal:

**Expected server logs:**
```
INFO:__main__:Client connected from ('127.0.0.1', 54321)
INFO:__main__:Received message: (initial connection data)
```

## 🧪 Test Results Checklist

Mark each test result:

- [ ] Python WebSocket server starts without errors
- [ ] Tauri app compiles and opens desktop window
- [ ] "Test Tauri Connection" button works ✅
- [ ] "Test Python Backend" button shows ✅ connected
- [ ] Python server logs show client connection
- [ ] **WebSocket Latency Test**: ___ms average (**record the result!**)
- [ ] No JavaScript console errors (F12 → Console)

### 📊 Latency Results Analysis:

**Record your latency test results:**
- Average: ___ms
- Min: ___ms
- Max: ___ms
- Performance rating: 🟢 🟡 🔴

## 🐛 Troubleshooting

### Issue: Tauri won't start
**Solution:**
```bash
# Clean and rebuild
cd gestdj-ui
rm -rf src-tauri/target
npm run tauri-dev
```

### Issue: Python backend connection fails
**Checklist:**
- [ ] Python server is running on port 8765
- [ ] No firewall blocking localhost:8765
- [ ] Check server terminal for error messages

### Issue: Desktop app shows blank screen
**Solution:**
- Wait for React dev server to fully start
- Check browser console (F12) for errors
- Restart with `npm run tauri-dev`

### Issue: "websockets module not found"
**Solution:**
```bash
pip install websockets>=11.0.0
```

## 🎉 Success Criteria

**Phase 1 is successful if:**
1. ✅ Tauri desktop app opens and displays React UI
2. ✅ Tauri backend communication works (Rust ↔ JavaScript)
3. ✅ WebSocket connection established (JavaScript ↔ Python)
4. ✅ Python server receives connection logs
5. ✅ **WebSocket latency measured and documented**

### 🎯 Next Phase Decision Tree:

**If latency results:**
- 🟢 **<20ms average**: Continue with Tauri → Phase 2 (video streaming)
- 🟡 **20-30ms average**: Consider MediaPipe JS option or continue with Tauri
- 🔴 **>30ms average**: Recommend PyQt6 for better performance

## 🔄 Clean Restart (if needed)

If anything goes wrong, clean restart:

```bash
# Kill all processes
killall -9 node python

# Clean Tauri build
cd gestdj-ui
rm -rf src-tauri/target

# Restart from Step 2
```

## 📝 Next Steps (Phase 2)

Once Phase 1 passes all tests:
- Add video streaming from Python to frontend
- Implement Canvas rendering for video + overlays
- Add MediaPipe hand landmark visualization

---

**Report any issues found during testing! 🐛**