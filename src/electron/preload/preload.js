const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'api', {
    // Settings
    getSettings: () => ipcRenderer.invoke('get-settings'),
    saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
    
    // Microphone
    getMicrophones: () => ipcRenderer.invoke('get-microphones'),
    testMicrophone: (deviceId) => ipcRenderer.invoke('test-microphone', deviceId),
    
    // Speech Recognition Services
    testService: (service, credentials) => ipcRenderer.invoke('test-service', service, credentials),
    
    // Dictation
    startDictation: () => ipcRenderer.invoke('start-dictation'),
    stopDictation: () => ipcRenderer.invoke('stop-dictation'),
    
    // Window controls
    minimizeWindow: () => ipcRenderer.send('minimize-window'),
    maximizeWindow: () => ipcRenderer.send('maximize-window'),
    closeWindow: () => ipcRenderer.send('close-window'),
    
    // Event listeners
    on: (channel, callback) => {
      // Whitelist channels
      const validChannels = ['dictation-status', 'mic-level'];
      if (validChannels.includes(channel)) {
        ipcRenderer.on(channel, (event, ...args) => callback(...args));
      }
    },
    off: (channel, callback) => {
      // Whitelist channels
      const validChannels = ['dictation-status', 'mic-level'];
      if (validChannels.includes(channel)) {
        ipcRenderer.removeListener(channel, callback);
      }
    }
  }
); 