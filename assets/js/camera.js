const cameraFeed = document.getElementById("video_feed");

if (cameraFeed && !cameraFeed.getAttribute("src")) {
  cameraFeed.setAttribute("src", "/video_feed");
}
