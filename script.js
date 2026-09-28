const MEDICINES = {
  MED001: {
    name: "DemoCure 500",
    ingredient: "Sample active ingredient",
    manufacturer: "MediScan Demo Pharma",
    mfg: "2025-01-15",
    expiry: "2027-01-14",
    batch: "MS-A1025",
    form: "Tablet",
    use: "Sample record: this field demonstrates how a medicine's general labeled use can be presented in simple language.",
    warning: "Follow the product label and prescription. Do not use this demo record as medical advice."
  },
  MED002: {
    name: "DemoRelief 10",
    ingredient: "Sample active ingredient",
    manufacturer: "MediScan Demo Pharma",
    mfg: "2026-02-01",
    expiry: "2028-01-31",
    batch: "MS-B2206",
    form: "Tablet",
    use: "Sample record: this field demonstrates a plain-language explanation of the medicine's general purpose.",
    warning: "Check the official label for contraindications, interactions, dosage, and other warnings."
  },
  MED003: {
    name: "ExpiredDemo 250",
    ingredient: "Sample active ingredient",
    manufacturer: "MediScan Demo Pharma",
    mfg: "2023-03-01",
    expiry: "2025-02-28",
    batch: "MS-X2303",
    form: "Capsule",
    use: "Sample record used to demonstrate expiry detection.",
    warning: "This demo product is expired. In a real system, the application should clearly flag it and advise the user not to use it without appropriate professional guidance."
  }
};

let selectedMedicine = null;

function formatDate(d) {
  const date = new Date(d + "T00:00:00");
  return date.toLocaleDateString(undefined, {day:"2-digit", month:"short", year:"numeric"});
}

function showDemo(id) {
  if (MEDICINES[id]) displayMedicine(MEDICINES[id]);
}

function displayMedicine(m) {
  selectedMedicine = m;
  document.getElementById("result").classList.remove("hidden");
  document.getElementById("medicine-name").textContent = m.name;
  document.getElementById("ingredient").textContent = m.ingredient;
  document.getElementById("manufacturer").textContent = m.manufacturer;
  document.getElementById("mfg").textContent = formatDate(m.mfg);
  document.getElementById("expiry").textContent = formatDate(m.expiry);
  document.getElementById("batch").textContent = m.batch;
  document.getElementById("form").textContent = m.form;
  document.getElementById("use").textContent = m.use;
  document.getElementById("warning").textContent = m.warning;

  const badge = document.getElementById("status-badge");
  const expired = new Date(m.expiry + "T23:59:59") < new Date();
  badge.textContent = expired ? "EXPIRED" : "VALID";
  badge.className = "badge" + (expired ? " expired" : "");

  document.getElementById("result").scrollIntoView({behavior:"smooth", block:"start"});
}

function addToCabinet() {
  if (!selectedMedicine) return;
  const current = JSON.parse(localStorage.getItem("mediscanCabinet") || "[]");
  if (!current.some(x => x.batch === selectedMedicine.batch)) {
    current.push(selectedMedicine);
    localStorage.setItem("mediscanCabinet", JSON.stringify(current));
  }
  renderCabinet();
  document.getElementById("cabinet").scrollIntoView({behavior:"smooth"});
}

function renderCabinet() {
  const list = document.getElementById("cabinet-list");
  const items = JSON.parse(localStorage.getItem("mediscanCabinet") || "[]");
  if (!items.length) {
    list.innerHTML = '<p class="muted">No medicines saved yet. Scan a medicine and add it here.</p>';
    return;
  }
  list.innerHTML = items.map(m => {
    const expired = new Date(m.expiry + "T23:59:59") < new Date();
    return `<div class="cabinet-item">
      <div><strong>${m.name}</strong><br><small>Batch ${m.batch} • Expires ${formatDate(m.expiry)}</small></div>
      <span class="badge ${expired ? "expired" : ""}">${expired ? "EXPIRED" : "VALID"}</span>
    </div>`;
  }).join("");
}

window.addEventListener("DOMContentLoaded", () => {
  renderCabinet();

  const message = document.getElementById("scan-message");
  if (window.Html5Qrcode) {
    const scanner = new Html5Qrcode("reader");
    scanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        if (MEDICINES[decodedText.trim()]) {
          displayMedicine(MEDICINES[decodedText.trim()]);
          message.textContent = "QR scanned successfully.";
        } else {
          message.textContent = "QR scanned, but this demo does not recognize that product ID. Try MED001, MED002, or MED003.";
        }
      },
      () => {}
    ).catch(() => {
      message.textContent = "Camera access may require HTTPS or localhost. Use the demo buttons below for the presentation.";
    });
  }
});
