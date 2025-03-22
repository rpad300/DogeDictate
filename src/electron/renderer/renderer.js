// DOM Elements
const navItems = document.querySelectorAll('.nav-item');
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');
const micInput = document.getElementById('mic-input');
const micStatus = document.querySelector('.mic-status');
const recognitionService = document.getElementById('recognition-service');
const serviceSettings = document.querySelectorAll('.service-settings');

// Settings elements
const interactionSounds = document.getElementById('interaction-sounds');
const muteAudio = document.getElementById('mute-audio');
const autoLearn = document.getElementById('auto-learn');
const outputLanguage = document.getElementById('output-language');

// Service specific elements
const whisperKey = document.getElementById('whisper-key');
const azureKey = document.getElementById('azure-key');
const azureRegion = document.getElementById('azure-region');
const googleCredentials = document.getElementById('google-credentials');

// Buttons
const changeHotkeys = document.getElementById('change-hotkeys');
const testWhisper = document.getElementById('test-whisper');
const testAzure = document.getElementById('test-azure');
const testGoogle = document.getElementById('test-google');
const browseCredentials = document.getElementById('browse-credentials');

// Navigation
navItems.forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    navItems.forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    // TODO: Implement page navigation
  });
});

// Tabs
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const tabName = tab.getAttribute('data-tab');
    
    // Update tab states
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    
    // Update content visibility
    tabContents.forEach(content => {
      content.style.display = content.id === `${tabName}-tab` ? 'block' : 'none';
    });
  });
});

// Recognition Service
recognitionService.addEventListener('change', () => {
  const service = recognitionService.value;
  
  // Show/hide service specific settings
  serviceSettings.forEach(settings => {
    settings.style.display = settings.id === `${service}-settings` ? 'block' : 'none';
  });
});

// Load settings
async function loadSettings() {
  try {
    const settings = await window.api.getSettings();
    if (settings) {
      interactionSounds.checked = settings.interactionSounds || false;
      muteAudio.checked = settings.muteAudio || false;
      autoLearn.checked = settings.autoLearn !== false; // Default to true
      outputLanguage.value = settings.outputLanguage || 'en-US';
      recognitionService.value = settings.recognitionService || 'whisper';
      
      // Load service specific settings
      if (settings.whisperKey) whisperKey.value = settings.whisperKey;
      if (settings.azureKey) azureKey.value = settings.azureKey;
      if (settings.azureRegion) azureRegion.value = settings.azureRegion;
      if (settings.googleCredentials) googleCredentials.value = settings.googleCredentials;
      
      // Trigger service change to show correct settings
      recognitionService.dispatchEvent(new Event('change'));
    }
  } catch (error) {
    console.error('Error loading settings:', error);
  }
}

// Save settings
async function saveSettings() {
  try {
    const settings = {
      interactionSounds: interactionSounds.checked,
      muteAudio: muteAudio.checked,
      autoLearn: autoLearn.checked,
      outputLanguage: outputLanguage.value,
      recognitionService: recognitionService.value,
      whisperKey: whisperKey.value,
      azureKey: azureKey.value,
      azureRegion: azureRegion.value,
      googleCredentials: googleCredentials.value
    };
    
    await window.api.saveSettings(settings);
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}

// Load microphones
async function loadMicrophones() {
  try {
    const mics = await window.api.getMicrophones();
    micInput.innerHTML = '<option value="">Select a microphone...</option>';
    mics.forEach(mic => {
      const option = document.createElement('option');
      option.value = mic.id;
      option.textContent = mic.name;
      micInput.appendChild(option);
    });
  } catch (error) {
    console.error('Error loading microphones:', error);
  }
}

// Event Listeners
micInput.addEventListener('change', async () => {
  const deviceId = micInput.value;
  if (deviceId) {
    micStatus.textContent = `Mic in use: ${micInput.options[micInput.selectedIndex].text}`;
    await saveSettings();
  }
});

changeHotkeys.addEventListener('click', () => {
  // TODO: Implement hotkey configuration dialog
});

testWhisper.addEventListener('click', async () => {
  const result = await window.api.testService('whisper', { apiKey: whisperKey.value });
  alert(result.message);
});

testAzure.addEventListener('click', async () => {
  const result = await window.api.testService('azure', {
    apiKey: azureKey.value,
    region: azureRegion.value
  });
  alert(result.message);
});

testGoogle.addEventListener('click', async () => {
  const result = await window.api.testService('google', {
    credentialsPath: googleCredentials.value
  });
  alert(result.message);
});

browseCredentials.addEventListener('click', () => {
  // TODO: Implement file selection dialog
});

// Save settings when they change
[interactionSounds, muteAudio, autoLearn, outputLanguage].forEach(element => {
  element.addEventListener('change', saveSettings);
});

[whisperKey, azureKey, azureRegion].forEach(element => {
  element.addEventListener('blur', saveSettings);
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  loadMicrophones();
});

// Microphone level monitoring
window.api.on('mic-level', (level) => {
  // TODO: Implement microphone level visualization
});

// Dictation status
window.api.on('dictation-status', (status) => {
  // TODO: Implement dictation status updates
}); 