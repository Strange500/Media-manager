function downloadFile(element) {
    // Get the filename from the element's value
    const filename = element.value;

    // Create a new anchor element
    const link = document.createElement('a');

    // Set the href attribute to the filename
    link.href = filename;

    // Set the download attribute to the filename
    link.download = filename;

    // Add the anchor element to the page
    document.body.appendChild(link);

    // Click the anchor element to start the download
    link.click();

    // Remove the anchor element from the page
    document.body.removeChild(link);
  }

function dl_link (link){
  document.getElementById("download-link").addEventListener("click", function(event) {
    event.preventDefault();
    const downloadUrl = "/server/upload/Lobster Jumpscare.mp4";
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = downloadUrl.split("/")[3];
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });}


function uploadFile() {
    var fileInput = document.getElementById("fileInput");
    var file = fileInput.files[0];
    var formData = new FormData();
    formData.append("file", file);

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);

    xhr.upload.addEventListener("progress", function(e) {
      var percentComplete = (e.loaded / e.total) * 100;
      document.getElementById("progress").style.width = percentComplete + "%";
    });

    xhr.addEventListener("load", function(e) {
      console.log("Upload complete");
    });

    xhr.send(formData);
  }

async function addDownloadLinks(apiUrl, containerId) {
    // Fetch the list of files from the API
    const response = await fetch(apiUrl);
    const files = await response.json();
  
    // Get the container element where the download links will be added
    const container = document.getElementById(containerId);
    // Loop through each file and create a download link for it
    for (let file in files) {
      if (files[file] === "100") {
        // Create a new input element with type "hidden"
        const input = document.createElement('input');
        input.type = 'hidden';
        input.value = file;
        
        // Create a new anchor element
        const link = document.createElement('a');
        link.href = "/encoding/" + file;
        console.log(link.href)
        link.download = file;
        link.textContent = file;
    
        // Add the input and anchor elements to the container
        container.appendChild(input);
        container.appendChild(link);}
    };
  }

async function addVideoProgressBars(apiUrl, containerId) {
    // Fetch the list of videos and percents from the API
    const response = await fetch(apiUrl);
    const videos = await response.json();
  
    // Get the container element where the progress bars will be added
    const container = document.getElementById(containerId);
  
    // Loop through each video and create a progress bar for it
    for (let video in videos) {
        if (videos[video] !== "100") {
      // Create a new div element for the progress bar
      const progressDiv = document.createElement('div');
  
      // Create a new p element for the video name
      const nameP = document.createElement('p');
      nameP.textContent = video;
      progressDiv.appendChild(nameP);
  
      // Create a new span element for the percent text
      const percentSpan = document.createElement('span');
      percentSpan.textContent = `${videos[video]}%`;
      progressDiv.appendChild(percentSpan);
  
      // Create a new progress element for the bar
      const progressBar = document.createElement('progress');
      progressBar.max = 100;
      progressBar.value = videos[video];
      progressDiv.appendChild(progressBar);
  
      // Add the progress bar to the container
      container.appendChild(progressDiv);}
    }}

addDownloadLinks('http://127.0.0.1:8081/ready', 'dl_div');

setInterval(() => {
    let h = document.getElementById("progressBars")
    h.innerHTML = '';
    addVideoProgressBars("http://127.0.0.1:8081/ready","progressBars")
}, 1000);


setInterval(() => {
    let h = document.getElementById("dl_div")
    h.innerHTML = '';
    addDownloadLinks("http://127.0.0.1:8081/ready","dl_div")
}, 1000);