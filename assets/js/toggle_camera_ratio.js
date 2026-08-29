document.addEventListener("click", async (event) => {
  const option = event.target.closest(".ratio-option");
  if (!option) return;

  const ratio = option.getAttribute("data-ratio");
  const videoBox = document.querySelector(".fd-video");

  const allRatioOptions = document.querySelectorAll("#o-1 .ratio-option");
  allRatioOptions.forEach((opt) => {
    const tick = opt.querySelector(".tick-icon");
    if (tick) tick.classList.remove("active");
  });

  const currentTick = option.querySelector(".tick-icon");
  if (currentTick) {
    currentTick.classList.add("active");
  }

  if (videoBox) {
    if (ratio === "9:16") {
      videoBox.classList.remove("ratio-16-9");
      videoBox.classList.add("ratio-9-16");
      console.log("Switch Resolution to 9:16");
    } else {
      videoBox.classList.remove("ratio-9-16");
      videoBox.classList.add("ratio-16-9");
      console.log("Switch Resolution to 16:9");
    }
  }

  const videoStream = document.querySelector("#video_feed");
  if (videoStream) {
    videoStream.src = `/video_feed?mode=${ratio}&t=${new Date().getTime()}`;
  }
});
