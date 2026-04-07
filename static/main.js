// Select DOM elements
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileInfo = document.getElementById("fileInfo");
const transcribeBtn = document.getElementById("transcribeBtn");

// ===== NEW: Progress Bar Elements =====
const progressBarContainer = document.getElementById("progressBarContainer");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");

// Handle file drop/selection events
dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));

// Drag and drop support
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drop-zone--over");
});

["dragleave", "dragend"].forEach((type) => {
  dropZone.addEventListener(type, () => {
    dropZone.classList.remove("drop-zone--over");
  });
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drop-zone--over");
  if (e.dataTransfer.files.length) {
    handleFile(e.dataTransfer.files[0]);
  }
});

// Validate video file
function handleFile(file) {
  if (file && file.type.startsWith("video/")) {
    fileInfo.textContent = "✅ " + file.name + " uploaded";
    fileInfo.classList.remove("hidden");
    transcribeBtn.disabled = false;
    
    // ===== NEW: Reset progress bar when new file is selected =====
    progressBarContainer.classList.add("hidden"); // Hide progress bar
    progressBar.style.width = "0%";              // Reset width
    progressText.textContent = "0%";             // Reset text
  } else {
    fileInfo.textContent = "❌ Invalid file type. Please upload a video.";
    fileInfo.classList.remove("hidden");
    transcribeBtn.disabled = true;
  }
}

// ===== NEW: Function to update progress bar =====
function updateProgressBar(percentage) {
  progressBar.style.width = percentage + "%";  // Update width
  progressText.textContent = percentage + "%"; // Update text
}

// Upload & transcribe
transcribeBtn.addEventListener("click", () => {
  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  // Update button state
  transcribeBtn.textContent = "Transcribing...";
  transcribeBtn.disabled = true;

  // ===== NEW: Show and initialize progress bar =====
  progressBarContainer.classList.remove("hidden");
  updateProgressBar(0);

  // ===== NEW: Simulate progress (for demo purposes) =====
  // In a real app, these updates would come from the backend
  let simulatedProgress = 0;
  const progressInterval = setInterval(() => {
    // Increment progress randomly between 5-15%
    simulatedProgress += Math.floor(Math.random() * 10) + 5;
    
    // Don't go beyond 95% until we get real backend confirmation
    if (simulatedProgress >= 95) {
      simulatedProgress = 95;
      clearInterval(progressInterval);
    }
    updateProgressBar(simulatedProgress);
  }, 800); // Update every 800ms

  // Send to backend
  fetch("http://127.0.0.1:5000/upload", {
    method: "POST",
    body: formData
  })
    .then(async res => {
      // ===== NEW: Stop simulated progress when backend responds =====
      clearInterval(progressInterval);

      const rawText = await res.text();
      console.log("📦 Raw response text from Flask:", rawText);

      try {
        const data = JSON.parse(rawText);
        console.log("✅ Parsed data:", data);

        
        document.getElementById("transcriptPlaceholder")?.remove();
        document.getElementById("sentimentPlaceholder")?.remove();
        document.getElementById("videoPlaceholder")?.remove();

        // ===== NEW: Complete progress bar (100%) on success =====
        updateProgressBar(100);
        
        // Hide progress bar after 1 second
        setTimeout(() => {
          progressBarContainer.classList.add("hidden");
        }, 1000);

        // Continue with existing success handling...
        const videoId = data.vtt_url.split("/").pop().replace(".vtt", "");
        const videoContainer = document.getElementById("videoContainer");
        const previewTitle = document.getElementById("previewTitle");

        if (previewTitle) {
          previewTitle.classList.remove("centered");
          previewTitle.classList.add("left");
        }

        videoContainer.innerHTML = `
          <video controls width="100%" class="mt-4">
            <source src="/video/${videoId}.mp4" type="video/mp4">
            <track src="${data.vtt_url}" kind="subtitles" srclang="en" label="English" default>
            Your browser does not support the video tag.
          </video>
        `;

        const transcriptBox = document.getElementById("transcriptBox");
        const segments = data.segments || [];
        transcriptBox.innerHTML = segments.map(seg => {
          const start = new Date(seg.start * 1000).toISOString().substr(11, 8);
          const end = new Date(seg.end * 1000).toISOString().substr(11, 8);
          return `<div><strong>[${start} - ${end}]</strong> ${seg.text}</div>`;
        }).join("");

        document.getElementById("downloadSrt").href = data.srt_url;

        const transcriptText = segments.map(seg => {
          const start = new Date(seg.start * 1000).toISOString().substr(11, 8);
          const end = new Date(seg.end * 1000).toISOString().substr(11, 8);
          return `[${start} - ${end}] ${seg.text}`;
        }).join("\n");

        const txtBlob = new Blob([transcriptText], { type: "text/plain" });
        const docBlob = new Blob([transcriptText], { type: "application/msword" });

        document.getElementById("downloadTxt").href = URL.createObjectURL(txtBlob);
        document.getElementById("downloadDoc").href = URL.createObjectURL(docBlob);

        document.getElementById("toggleDownloadDropdown").style.display = "inline-block";

        const sentimentBody = document.getElementById("sentimentBody");
        sentimentBody.innerHTML = "";

        if (data.sentiment_table && data.sentiment_table.length > 0) {
          data.sentiment_table.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
              <td>${row.minute}</td>
              <td>${row.dialogues}</td>
              <td>${row.sentiment}</td>
              <td>${row.score}</td>
            `;
            sentimentBody.appendChild(tr);
          });
        }

        populateActionSentimentTable(data.action_sentiment_table || []);
        populateChunkAnalysisTable(data.chunk_analysis_table || []);


      } catch (err) {
        console.error("❌ Failed to parse JSON from response:", rawText);
        transcribeBtn.textContent = "Try Again";
        
        // ===== NEW: Reset progress bar on error =====
        updateProgressBar(0);
        progressBarContainer.classList.add("hidden");
      }

      transcribeBtn.disabled = false;
      transcribeBtn.textContent = "Generate Subtitles";
    })
    .catch(err => {
      console.error("❌ Network/Server error during fetch:", err);
      transcribeBtn.textContent = "Try Again";
      transcribeBtn.disabled = false;
      
      // ===== NEW: Reset progress bar on error =====
      updateProgressBar(0);
      progressBarContainer.classList.add("hidden");
    });
});

// ... existing populateActionSentimentTable etc. functions ...
// 🎬 Function to fill action-based sentiment table
function populateActionSentimentTable(actionData) {
  document.getElementById("expressionPlaceholder")?.remove();
  const body = document.getElementById("actionSentimentBody");
  body.innerHTML = "";

  if (!Array.isArray(actionData)) {
    console.warn("⚠️ action_sentiment_table is not an array:", actionData);
    return;
  }

  actionData.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.start}</td>
      <td>${row.end}</td>
      <td>${row.expression}</td>
      <td>${row.sentiment}</td>
    `;
    body.appendChild(tr);
  });
}
// 🔍 Populate 10-sec Chunk Table
function populateChunkAnalysisTable(data) {
  document.getElementById("chunkPlaceholder")?.remove();
  const body = document.getElementById("chunkAnalysisBody");
  body.innerHTML = "";

  data.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.start}</td>
      <td>${row.end}</td>
      <td>${row.expression}</td>
      <td>${row.expression_sentiment}</td>
      <td>${row.dialogue_sentiment}</td>
      <td>${row.people}</td>
      <td>${row.places}</td>
      <td>${row.characters}</td>
      <td>${row.things}</td>
      <td>${row.animals}</td>
      <td>${row.others}</td>
    `;
    body.appendChild(tr);
  });
}

