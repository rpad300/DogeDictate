// DOM Elements
const hotkeyInputs = document.querySelectorAll('.hotkey-input');
const resetButton = document.getElementById('reset-hotkeys');
const saveButton = document.getElementById('save-hotkeys');

// Default hotkeys
const defaultHotkeys = {
  'push-to-talk': 'Alt+Space',
  'toggle-hands-free': 'Alt+H',
  'toggle-bar': 'Alt+B',
  'switch-en': 'Alt+1',
  'switch-pt': 'Alt+2',
  'switch-es': 'Alt+3'
};

// Current recording state
let isRecording = false;
let currentInput = null;

// Load saved hotkeys
async function loadHotkeys() {
  try {
    const settings = await window.api.getSettings();
    const hotkeys = settings?.hotkeys || defaultHotkeys;
    
    // Update input values
    Object.entries(hotkeys).forEach(([id, value]) => {
      const input = document.getElementById(id);
      if (input) input.value = value;
    });
  } catch (error) {
    console.error('Error loading hotkeys:', error);
  }
}

// Save hotkeys
async function saveHotkeys() {
  try {
    const hotkeys = {};
    hotkeyInputs.forEach(input => {
      hotkeys[input.id] = input.value || defaultHotkeys[input.id];
    });
    
    const settings = await window.api.getSettings() || {};
    settings.hotkeys = hotkeys;
    await window.api.saveSettings(settings);
    
    // Close the window
    window.api.closeHotkeyDialog();
  } catch (error) {
    console.error('Error saving hotkeys:', error);
  }
}

// Reset hotkeys to default
function resetHotkeys() {
  hotkeyInputs.forEach(input => {
    input.value = defaultHotkeys[input.id];
  });
}

// Start recording hotkey
function startRecording(input) {
  if (isRecording) {
    stopRecording();
  }
  
  isRecording = true;
  currentInput = input;
  input.value = 'Recording...';
  input.classList.add('recording');
}

// Stop recording hotkey
function stopRecording() {
  if (currentInput) {
    if (currentInput.value === 'Recording...') {
      currentInput.value = defaultHotkeys[currentInput.id];
    }
    currentInput.classList.remove('recording');
  }
  isRecording = false;
  currentInput = null;
}

// Event Listeners
hotkeyInputs.forEach(input => {
  input.addEventListener('click', () => {
    startRecording(input);
  });
  
  input.addEventListener('blur', () => {
    stopRecording();
  });
});

// Handle keyboard events
document.addEventListener('keydown', (e) => {
  if (!isRecording) return;
  
  e.preventDefault();
  
  // Build hotkey string
  const keys = [];
  if (e.ctrlKey) keys.push('Ctrl');
  if (e.altKey) keys.push('Alt');
  if (e.shiftKey) keys.push('Shift');
  
  // Add the main key if it's not a modifier
  if (!['Control', 'Alt', 'Shift'].includes(e.key)) {
    keys.push(e.key.length === 1 ? e.key.toUpperCase() : e.key);
  }
  
  if (keys.length > 0) {
    currentInput.value = keys.join('+');
    stopRecording();
  }
});

// Save button
saveButton.addEventListener('click', saveHotkeys);

// Reset button
resetButton.addEventListener('click', () => {
  if (confirm('Are you sure you want to reset all hotkeys to default?')) {
    resetHotkeys();
  }
});

// Initialize
document.addEventListener('DOMContentLoaded', loadHotkeys); 