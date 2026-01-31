# 🔧 Return Module Setup Instructions

## Current Status

The Return & Exchange module is **partially integrated** but needs additional dependencies to be installed in your virtual environment.

---

## ✅ What's Already Fixed

1. **Backend API endpoint** - Order status update fixed
2. **Frontend UI components** - CardDescription component added
3. **Return module code** - All files integrated and import paths fixed
4. **Database setup** - Configured to use separate `returns.db`

---

## 🚨 Missing Dependencies

The following packages need to be installed in your backend virtual environment (`.venv`):

- `langgraph` - Workflow orchestration
- `langgraph-checkpoint` - State management
- `langchain-core` - Core LangChain functionality
- `sentence-transformers` - Text embeddings
- `torch` - PyTorch (required by sentence-transformers)

---

## 📦 Installation Steps

### Option 1: Quick Install (Recommended)

1. **Open a new terminal** in the `backend` folder
2. **Activate the virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install all dependencies:**
   ```powershell
   pip install langgraph langgraph-checkpoint langchain-core sentence-transformers torch
   ```

4. **Wait for installation** (may take 2-5 minutes due to large packages)

5. **Restart the backend server:**
   - Press `Ctrl+C` to stop the current server
   - Run: `uvicorn app.main:app --reload`

### Option 2: Install from requirements.txt

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## ✅ Verification

After installation, you should see this message when the backend starts:

```
[OK] Return & Exchange module loaded successfully
INFO:     Application startup complete.
```

If you see this instead, the dependencies are still missing:

```
[WARN] Return & Exchange module not available: No module named 'langgraph'
```

---

## 🧪 Testing the Return Flow

Once dependencies are installed:

### 1. Mark Order as Delivered
- Go to order details page
- Click green **"Mark as Delivered (Demo)"** button
- Verify AuraPoints are credited

### 2. Initiate Return
- Click blue **"Return / Exchange"** button
- Fill out the return form:
  - Select damage type
  - Describe the issue (min 10 characters)
  - Upload images/videos (optional)
- Submit

### 3. View AI Processing
- See AI agents analyze the return:
  - **VisionAgent** - Analyzes uploaded media
  - **PolicyAgent** - Checks return eligibility
  - **ResolutionAgent** - Determines resolution
  - **CommunicationAgent** - Generates customer message

---

## 🎯 Expected Behavior

| Damage Type | Product Category | Flow |
|-------------|-----------------|------|
| FUNCTIONAL | Electronics | Manual Review (Admin) |
| PHYSICAL | Any | AI Pipeline (Automated) |
| COSMETIC | Any | AI Pipeline (Automated) |
| OTHER | Any | AI Pipeline (Automated) |

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'langgraph'"
**Solution:** Run the installation steps above

### "Failed to load resource: 500"
**Solution:** Check backend terminal for errors, ensure all dependencies are installed

### Backend won't start after installation
**Solution:** 
1. Kill all Python processes: `Stop-Process -Name python -Force`
2. Restart backend: `.\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload`

### Pydantic version errors
**Solution:**
```powershell
.\.venv\Scripts\Activate.ps1
pip install --upgrade pydantic pydantic-core --force-reinstall
```

---

## 📊 System Requirements

- **Python**: 3.10+
- **RAM**: 4GB minimum (8GB recommended for ML models)
- **Disk Space**: ~2GB for dependencies
- **Internet**: Required for initial model downloads

---

## 🔄 Alternative: Disable Return Module

If you don't need the return functionality right now, you can disable it:

1. Open `backend/app/main.py`
2. Comment out lines 511-518 (the return module loading section)
3. Restart the backend

---

## 📝 Next Steps

1. **Install dependencies** using Option 1 above
2. **Restart backend** and verify the "[OK]" message
3. **Refresh browser** (Ctrl + Shift + R)
4. **Test the flow** using the steps above
5. **Report any issues** you encounter

---

**Last Updated:** Jan 31, 2026 - 10:30 AM  
**Status:** Dependencies need manual installation
