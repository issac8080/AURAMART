# Frontend troubleshooting

## EBUSY: resource busy or locked (.next folder)

**Error:** `EBUSY: resource busy or locked, open '...\frontend\.next\server\webpack-runtime.js'`

This often happens on **Windows** when the project is in **OneDrive** or another process is locking files in `.next`.

### Fix

1. **Stop the dev server**  
   In the terminal where `npm run dev` is running, press **Ctrl+C**.

2. **Delete the `.next` folder** (clean build cache):
   ```bash
   cd frontend
   npm run clean
   ```
   Or manually delete the `frontend\.next` folder in File Explorer (if it says "in use", close VS Code/Cursor and any other app using the project, then delete).

3. **Optional: keep OneDrive from syncing `.next`**  
   Right‑click `frontend\.next` (after it exists again) → "Free up space" / "Always keep on this device" can reduce locking. Better: move the project **outside** OneDrive (e.g. `C:\Dev\AuraShop`) so build files aren’t synced.

4. **Start the dev server again:**
   ```bash
   npm run dev
   ```

If EBUSY continues, close Cursor/VS Code, delete `frontend\.next`, then reopen the project and run `npm run dev`.
