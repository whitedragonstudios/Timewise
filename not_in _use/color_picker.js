const picker = document.getElementById('colorPicker');
const hexValue = document.getElementById('hexValue');
const rgbValue = document.getElementById('rgbValue');
const previewBox = document.getElementById('previewBox');
const copyButton = document.getElementById('copyButton');

// Convert hex to RGB
function hexToRgb(hex) {
    const bigint = parseInt(hex.slice(1), 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgb(${r}, ${g}, ${b})`;
}

// Update color preview
picker.addEventListener('input', () => {
    const color = picker.value;
    hexValue.textContent = color;
    rgbValue.textContent = hexToRgb(color);
    previewBox.style.backgroundColor = color;
});

// Copy hex value to clipboard
copyButton.addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(hexValue.textContent);
        copyButton.textContent = "Copied!";
        setTimeout(() => copyButton.textContent = "Copy Hex", 1000);
    } catch {
        alert("Failed to copy color.");
    }
});
