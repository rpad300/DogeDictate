const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const Store = require('electron-store');

// Initialize electron store
const store = new Store();

function createWindow() {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 600,
    minWidth: 800,
    minHeight: 500,
    backgroundColor: '#F5E8C7',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, '../preload/preload.js')
    },
    frame: false, // Custom titlebar
    icon: path.join(__dirname, '../assets/icon.png')
  });

  // Load the index.html file
  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  // Open DevTools in development
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }
}

// This method will be called when Electron has finished initialization
app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Quit when all windows are closed.
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// IPC handlers
ipcMain.handle('get-settings', () => {
  return store.get('settings');
});

ipcMain.handle('save-settings', (event, settings) => {
  store.set('settings', settings);
  return true;
});

ipcMain.handle('get-microphones', () => {
  // TODO: Implement microphone detection
  return [];
});

ipcMain.handle('test-microphone', (event, deviceId) => {
  // TODO: Implement microphone testing
  return { success: true, level: 0.5 };
});

ipcMain.handle('test-service', (event, service, credentials) => {
  // TODO: Implement service testing
  return { success: true, message: 'Service connection successful' };
});

ipcMain.handle('start-dictation', () => {
  // TODO: Implement dictation start
  return true;
});

ipcMain.handle('stop-dictation', () => {
  // TODO: Implement dictation stop
  return true;
});

// Window controls
ipcMain.on('minimize-window', () => {
  const win = BrowserWindow.getFocusedWindow();
  if (win) win.minimize();
});

ipcMain.on('maximize-window', () => {
  const win = BrowserWindow.getFocusedWindow();
  if (win) {
    if (win.isMaximized()) {
      win.unmaximize();
    } else {
      win.maximize();
    }
  }
});

ipcMain.on('close-window', () => {
  const win = BrowserWindow.getFocusedWindow();
  if (win) win.close();
}); 